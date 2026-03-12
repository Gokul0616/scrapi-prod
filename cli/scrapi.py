#!/usr/bin/env python3
import argparse
import json
import os
import pathlib

import requests

API = os.getenv('SCRAPI_API', 'http://localhost:8000/v1')
API_KEY = os.getenv('SCRAPI_API_KEY', 'dev-secret-key')


def _headers():
    return {'x-api-key': API_KEY}


def request(method: str, path: str, payload: dict | None = None):
    resp = requests.request(
        method,
        f'{API}{path}',
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def cmd_init(args):
    pathlib.Path('scrapi.yaml').write_text(
        'name: my-actor\nruntime: python\nentrypoint: main.py\n', encoding='utf-8'
    )
    pathlib.Path('main.py').write_text("print('Hello from Scrapi actor')\n", encoding='utf-8')
    print('Initialized Scrapi actor project.')


def cmd_push(args):
    cfg = pathlib.Path('scrapi.yaml')
    if not cfg.exists():
        raise SystemExit('scrapi.yaml not found. Run scrapi init first.')
    name = 'local-actor'
    for line in cfg.read_text(encoding='utf-8').splitlines():
        if line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
    print(json.dumps(request('POST', '/actors', {'name': name, 'runtime': 'python', 'entrypoint': 'main.py'}), indent=2))


def cmd_run(args):
    print(json.dumps(request('POST', '/runs', {'actor_id': args.actor_id, 'input_payload': {}}), indent=2))


def cmd_runs(args):
    print(json.dumps(request('GET', '/runs'), indent=2))


def cmd_schedule(args):
    print(json.dumps(request('POST', '/schedules', {'actor_id': args.actor_id, 'cron': args.cron, 'payload': {}}), indent=2))


def cmd_webhook(args):
    print(json.dumps(request('POST', '/webhooks', {'event_type': 'run.finished', 'target_url': args.url}), indent=2))


def cmd_resume(args):
    print(json.dumps(request('POST', f'/runs/{args.run_id}/resume'), indent=2))


def cmd_cancel(args):
    print(json.dumps(request('POST', f'/runs/{args.run_id}/cancel'), indent=2))


def cmd_queue_stats(args):
    print(json.dumps(request('GET', f'/request-queue/{args.run_id}/stats'), indent=2))


def cmd_kv_set(args):
    value = json.loads(args.value)
    print(json.dumps(request('PUT', '/key-value', {'actor_id': args.actor_id, 'key': args.key, 'value': value}), indent=2))


def cmd_kv_get(args):
    print(json.dumps(request('GET', f'/key-value/{args.actor_id}/{args.key}'), indent=2))


def cmd_kv_list(args):
    print(json.dumps(request('GET', f'/key-value/{args.actor_id}'), indent=2))


def main():
    parser = argparse.ArgumentParser('scrapi')
    sub = parser.add_subparsers(required=True)

    p_init = sub.add_parser('init')
    p_init.set_defaults(func=cmd_init)

    p_push = sub.add_parser('push')
    p_push.set_defaults(func=cmd_push)

    p_run = sub.add_parser('run')
    p_run.add_argument('--actor-id', type=int, required=True)
    p_run.set_defaults(func=cmd_run)

    p_runs = sub.add_parser('runs')
    p_runs.set_defaults(func=cmd_runs)

    p_sched = sub.add_parser('schedule')
    p_sched.add_argument('--actor-id', type=int, required=True)
    p_sched.add_argument('--cron', type=str, required=True)
    p_sched.set_defaults(func=cmd_schedule)

    p_hook = sub.add_parser('webhook')
    p_hook.add_argument('--url', type=str, required=True)
    p_hook.set_defaults(func=cmd_webhook)

    p_resume = sub.add_parser('resume')
    p_resume.add_argument('--run-id', type=int, required=True)
    p_resume.set_defaults(func=cmd_resume)

    p_cancel = sub.add_parser('cancel')
    p_cancel.add_argument('--run-id', type=int, required=True)
    p_cancel.set_defaults(func=cmd_cancel)

    p_stats = sub.add_parser('queue-stats')
    p_stats.add_argument('--run-id', type=int, required=True)
    p_stats.set_defaults(func=cmd_queue_stats)

    p_kv_set = sub.add_parser('kv-set')
    p_kv_set.add_argument('--actor-id', type=int, required=True)
    p_kv_set.add_argument('--key', type=str, required=True)
    p_kv_set.add_argument('--value', type=str, required=True, help='JSON object string')
    p_kv_set.set_defaults(func=cmd_kv_set)

    p_kv_get = sub.add_parser('kv-get')
    p_kv_get.add_argument('--actor-id', type=int, required=True)
    p_kv_get.add_argument('--key', type=str, required=True)
    p_kv_get.set_defaults(func=cmd_kv_get)

    p_kv_list = sub.add_parser('kv-list')
    p_kv_list.add_argument('--actor-id', type=int, required=True)
    p_kv_list.set_defaults(func=cmd_kv_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
