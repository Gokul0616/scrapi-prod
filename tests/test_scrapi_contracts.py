from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def test_api_routes_include_run_controls_and_queue_stats():
    routes = _read('backend/app/api/routes.py')
    assert "@router.get('/runs'" in routes
    assert "@router.post('/runs/{run_id}/resume'" in routes
    assert "@router.post('/runs/{run_id}/cancel'" in routes
    assert "@router.get('/request-queue/{run_id}/stats'" in routes
    assert "@router.put('/key-value'" in routes
    assert "@router.get('/key-value/{actor_id}/{key}'" in routes


def test_worker_logic_has_cancellation_and_retry_reschedule():
    tasks = _read('backend/app/workers/tasks.py')
    assert "if run.status == 'CANCELLED'" in tasks
    assert "run.celery_task_id = retry_task.id" in tasks
    assert "RequestQueueItem.status.in_(['PENDING', 'LEASED'])" in tasks


def test_cli_exposes_phase3_commands():
    cli = _read('cli/scrapi.py')
    assert "sub.add_parser('runs')" in cli
    assert "sub.add_parser('resume')" in cli
    assert "sub.add_parser('cancel')" in cli
    assert "sub.add_parser('queue-stats')" in cli
    assert "sub.add_parser('kv-set')" in cli
    assert "sub.add_parser('kv-get')" in cli
    assert "sub.add_parser('kv-list')" in cli


def test_readme_documents_new_endpoints_and_commands():
    readme = _read('Readme.md')
    assert '/v1/runs/1/resume' in readme
    assert '/v1/request-queue/1/stats' in readme
    assert 'python cli/scrapi.py runs' in readme
    assert 'python cli/scrapi.py resume --run-id 1' in readme
    assert '/v1/key-value/1/state' in readme
    assert 'python cli/scrapi.py kv-set --actor-id 1 --key state' in readme
