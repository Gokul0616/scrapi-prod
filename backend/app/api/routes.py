from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.api.schemas import (
    ActorCreate,
    ActorOut,
    RunCreate,
    RunOut,
    QueueRequestCreate,
    QueueRequestOut,
    DatasetItemOut,
    ScheduleCreate,
    ScheduleOut,
    WebhookCreate,
    WebhookOut,
    UsageSummaryOut,
    RunCancelOut,
    QueueStatsOut,
    RunResumeOut,
    KeyValueSet,
    KeyValueOut,
)
from app.core.security import require_api_key
from app.db.models import Actor, Run, RequestQueueItem, DatasetItem, Schedule, WebhookSubscription, UsageEvent, KeyValueRecord
from app.db.session import get_db
from app.workers.tasks import execute_run

router = APIRouter(dependencies=[Depends(require_api_key)])



@router.post('/actors', response_model=ActorOut)
def create_actor(payload: ActorCreate, db: Session = Depends(get_db)):
    actor = Actor(**payload.model_dump())
    db.add(actor)
    db.commit()
    db.refresh(actor)
    return actor


@router.get('/actors', response_model=list[ActorOut])
def list_actors(db: Session = Depends(get_db)):
    return db.scalars(select(Actor).order_by(Actor.id.desc())).all()




@router.get('/runs', response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return db.scalars(select(Run).order_by(Run.id.desc())).all()


@router.post('/runs', response_model=RunOut)
def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    actor = db.get(Actor, payload.actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail='actor_not_found')
    run = Run(actor_id=payload.actor_id, input_payload=payload.input_payload)
    db.add(run)
    db.commit()
    db.refresh(run)

    task = execute_run.delay(run.id)
    run.celery_task_id = task.id
    db.commit()
    db.refresh(run)
    return run


@router.get('/runs/{run_id}', response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='run_not_found')
    return run


@router.post('/runs/{run_id}/resume', response_model=RunResumeOut)
def resume_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='run_not_found')
    if run.status in {'SUCCEEDED', 'FAILED'}:
        raise HTTPException(status_code=409, detail='run_is_terminal')
    if run.status == 'CANCELLED':
        raise HTTPException(status_code=409, detail='run_cancelled')

    task = execute_run.delay(run.id)
    run.celery_task_id = task.id
    db.commit()
    return RunResumeOut(id=run.id, status=run.status, celery_task_id=run.celery_task_id)


@router.post('/runs/{run_id}/cancel', response_model=RunCancelOut)
def cancel_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='run_not_found')
    if run.status in {'SUCCEEDED', 'FAILED', 'CANCELLED'}:
        return RunCancelOut(id=run.id, status=run.status)

    run.status = 'CANCELLED'
    run.finished_at = datetime.utcnow()
    run.log = (run.log or '') + 'Run cancelled by user\n'
    db.commit()
    return RunCancelOut(id=run.id, status=run.status)


@router.post('/request-queue', response_model=QueueRequestOut)
def enqueue_request(payload: QueueRequestCreate, db: Session = Depends(get_db)):
    run = db.get(Run, payload.run_id)
    if not run:
        raise HTTPException(status_code=404, detail='run_not_found')

    existing = db.scalar(
        select(RequestQueueItem).where(
            RequestQueueItem.run_id == payload.run_id,
            RequestQueueItem.unique_key == payload.unique_key,
        )
    )
    if existing:
        return existing

    item = RequestQueueItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get('/request-queue/{run_id}', response_model=list[QueueRequestOut])
def list_queue(run_id: int, db: Session = Depends(get_db)):
    return db.scalars(
        select(RequestQueueItem).where(RequestQueueItem.run_id == run_id).order_by(RequestQueueItem.id)
    ).all()


@router.get('/request-queue/{run_id}/stats', response_model=QueueStatsOut)
def queue_stats(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail='run_not_found')

    pending = db.scalar(select(func.count(RequestQueueItem.id)).where(RequestQueueItem.run_id == run_id, RequestQueueItem.status == 'PENDING')) or 0
    leased = db.scalar(select(func.count(RequestQueueItem.id)).where(RequestQueueItem.run_id == run_id, RequestQueueItem.status == 'LEASED')) or 0
    done = db.scalar(select(func.count(RequestQueueItem.id)).where(RequestQueueItem.run_id == run_id, RequestQueueItem.status == 'DONE')) or 0
    failed = db.scalar(select(func.count(RequestQueueItem.id)).where(RequestQueueItem.run_id == run_id, RequestQueueItem.status == 'FAILED')) or 0
    return QueueStatsOut(pending=pending, leased=leased, done=done, failed=failed)


@router.get('/datasets/{run_id}', response_model=list[DatasetItemOut])
def list_dataset(run_id: int, db: Session = Depends(get_db)):
    return db.scalars(select(DatasetItem).where(DatasetItem.run_id == run_id).order_by(DatasetItem.id)).all()


@router.post('/schedules', response_model=ScheduleOut)
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)):
    actor = db.get(Actor, payload.actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail='actor_not_found')
    schedule = Schedule(**payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get('/schedules', response_model=list[ScheduleOut])
def list_schedules(db: Session = Depends(get_db)):
    return db.scalars(select(Schedule).order_by(Schedule.id.desc())).all()


@router.post('/webhooks', response_model=WebhookOut)
def create_webhook(payload: WebhookCreate, db: Session = Depends(get_db)):
    hook = WebhookSubscription(**payload.model_dump())
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return hook


@router.get('/webhooks', response_model=list[WebhookOut])
def list_webhooks(db: Session = Depends(get_db)):
    return db.scalars(select(WebhookSubscription).order_by(WebhookSubscription.id.desc())).all()




@router.put('/key-value', response_model=KeyValueOut)
def upsert_key_value(payload: KeyValueSet, db: Session = Depends(get_db)):
    actor = db.get(Actor, payload.actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail='actor_not_found')

    record = db.scalar(
        select(KeyValueRecord).where(
            KeyValueRecord.actor_id == payload.actor_id,
            KeyValueRecord.key == payload.key,
        )
    )
    if record:
        record.value = payload.value
    else:
        record = KeyValueRecord(actor_id=payload.actor_id, key=payload.key, value=payload.value)
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.get('/key-value/{actor_id}/{key}', response_model=KeyValueOut)
def get_key_value(actor_id: int, key: str, db: Session = Depends(get_db)):
    record = db.scalar(
        select(KeyValueRecord).where(
            KeyValueRecord.actor_id == actor_id,
            KeyValueRecord.key == key,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail='key_not_found')
    return record


@router.get('/key-value/{actor_id}', response_model=list[KeyValueOut])
def list_key_values(actor_id: int, db: Session = Depends(get_db)):
    actor = db.get(Actor, actor_id)
    if not actor:
        raise HTTPException(status_code=404, detail='actor_not_found')
    return db.scalars(
        select(KeyValueRecord).where(KeyValueRecord.actor_id == actor_id).order_by(KeyValueRecord.key)
    ).all()


@router.get('/usage/summary', response_model=UsageSummaryOut)
def usage_summary(db: Session = Depends(get_db)):
    total_runs = db.scalar(select(func.count(Run.id))) or 0
    succeeded_runs = db.scalar(select(func.count(Run.id)).where(Run.status == 'SUCCEEDED')) or 0
    processed_requests = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.value), 0)).where(UsageEvent.metric == 'processed_requests')
    ) or 0
    return UsageSummaryOut(
        total_runs=total_runs,
        succeeded_runs=succeeded_runs,
        processed_requests=processed_requests,
    )
