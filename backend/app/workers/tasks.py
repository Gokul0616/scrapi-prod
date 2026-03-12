from datetime import datetime, timezone, timedelta
from sqlalchemy import select
import requests
from croniter import croniter

from app.core.config import settings
from app.db.models import Run, RequestQueueItem, DatasetItem, WebhookSubscription, UsageEvent, Schedule
from app.db.session import SessionLocal
from app.workers.celery_app import celery


def _is_due(cron_expr: str, now: datetime) -> bool:
    prev_time = croniter(cron_expr, now).get_prev(datetime)
    return (now - prev_time).total_seconds() < 60


@celery.task(name='schedules.dispatch')
def dispatch_schedules():
    db = SessionLocal()
    created = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        schedules = db.scalars(select(Schedule).where(Schedule.enabled.is_(True))).all()
        for sched in schedules:
            try:
                if _is_due(sched.cron, now):
                    run = Run(actor_id=sched.actor_id, input_payload=sched.payload)
                    db.add(run)
                    db.commit()
                    db.refresh(run)
                    task = execute_run.delay(run.id)
                    run.celery_task_id = task.id
                    db.commit()
                    created += 1
            except Exception:
                continue
        return {'created_runs': created}
    finally:
        db.close()


@celery.task(name='webhooks.deliver')
def deliver_webhook(subscription_id: int, payload: dict):
    db = SessionLocal()
    try:
        sub = db.get(WebhookSubscription, subscription_id)
        if not sub or not sub.enabled:
            return {'status': 'skipped'}
        response = requests.post(sub.target_url, json=payload, timeout=settings.webhook_timeout_sec)
        response.raise_for_status()
        return {'status': response.status_code}
    finally:
        db.close()


@celery.task(name='runs.execute')
def execute_run(run_id: int):
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return {'error': 'run_not_found'}

        if run.status == 'CANCELLED':
            return {'status': run.status, 'run_id': run_id}

        run.status = 'RUNNING'
        run.log = (run.log or '') + 'Run started\n'
        db.commit()

        processed = 0
        now = datetime.utcnow()
        queue_items = db.scalars(
            select(RequestQueueItem).where(
                RequestQueueItem.run_id == run_id,
                RequestQueueItem.status.in_(['PENDING', 'LEASED']),
            )
        ).all()

        for item in queue_items:
            # Release stale leases
            if item.status == 'LEASED' and item.lease_expires_at and item.lease_expires_at <= now:
                item.status = 'PENDING'
                item.lease_expires_at = None

            if item.status != 'PENDING':
                continue
            now = datetime.utcnow()
            if item.next_retry_at and item.next_retry_at > now:
                continue
            db.refresh(run)
            if run.status == 'CANCELLED':
                break

            item.status = 'LEASED'
            item.attempt += 1
            item.lease_expires_at = now + timedelta(seconds=settings.queue_lease_seconds)
            db.commit()

            try:
                dataset_item = DatasetItem(
                    run_id=run_id,
                    data={
                        'url': item.url,
                        'unique_key': item.unique_key,
                        'title': f'Scraped content for {item.url}',
                    },
                )
                db.add(dataset_item)
                item.status = 'DONE'
                item.lease_expires_at = None
                item.next_retry_at = None
                item.last_error = None
                processed += 1
                run.log = (run.log or '') + f'Processed: {item.url}\n'
                db.commit()
            except Exception as exc:
                item.last_error = str(exc)
                item.lease_expires_at = None
                if item.attempt >= settings.queue_max_attempts:
                    item.status = 'FAILED'
                else:
                    item.status = 'PENDING'
                    item.next_retry_at = now + timedelta(seconds=settings.queue_retry_backoff_seconds * item.attempt)
                run.log = (run.log or '') + f'Retry scheduled for {item.url}: {exc}\n'
                db.commit()

        unfinished = db.scalar(
            select(RequestQueueItem.id).where(
                RequestQueueItem.run_id == run_id,
                RequestQueueItem.status.in_(['PENDING', 'LEASED'])
            ).limit(1)
        )

        if run.status == 'CANCELLED':
            run.log = (run.log or '') + 'Run was cancelled before completion\n'
        elif unfinished:
            run.status = 'RUNNING'
            run.log = (run.log or '') + 'Run has pending retries\n'
            retry_task = execute_run.apply_async((run_id,), countdown=5)
            run.celery_task_id = retry_task.id
        else:
            has_failed = db.scalar(
                select(RequestQueueItem.id).where(
                    RequestQueueItem.run_id == run_id,
                    RequestQueueItem.status == 'FAILED'
                ).limit(1)
            )
            run.status = 'FAILED' if has_failed else 'SUCCEEDED'
            run.finished_at = datetime.utcnow()
            run.log = (run.log or '') + 'Run finished\n'

        db.add(UsageEvent(run_id=run_id, metric='processed_requests', value=processed))
        db.commit()

        if run.status in {'SUCCEEDED', 'FAILED', 'CANCELLED'}:
            hooks = db.scalars(
                select(WebhookSubscription).where(
                    WebhookSubscription.enabled.is_(True),
                    WebhookSubscription.event_type == 'run.finished',
                )
            ).all()
            for hook in hooks:
                deliver_webhook.delay(hook.id, {'run_id': run_id, 'status': run.status})

        return {'status': run.status, 'run_id': run_id}
    except Exception as exc:
        run = db.get(Run, run_id)
        if run:
            run.status = 'FAILED'
            run.log = (run.log or '') + f'Failed: {exc}\n'
            db.commit()
        raise
    finally:
        db.close()
