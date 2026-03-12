from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ActorCreate(BaseModel):
    name: str
    runtime: str = 'python'
    entrypoint: str = 'main.py'


class ActorOut(BaseModel):
    id: int
    name: str
    runtime: str
    entrypoint: str
    created_at: datetime

    model_config = {'from_attributes': True}


class RunCreate(BaseModel):
    actor_id: int
    input_payload: dict = Field(default_factory=dict)


class RunOut(BaseModel):
    id: int
    actor_id: int
    status: str
    input_payload: dict
    celery_task_id: str | None
    log: str
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}


class QueueRequestCreate(BaseModel):
    run_id: int
    unique_key: str
    url: str


class QueueRequestOut(BaseModel):
    id: int
    run_id: int
    unique_key: str
    url: str
    status: str
    attempt: int
    lease_expires_at: datetime | None
    next_retry_at: datetime | None
    last_error: str | None

    model_config = {'from_attributes': True}


class DatasetItemOut(BaseModel):
    id: int
    run_id: int
    data: dict
    created_at: datetime

    model_config = {'from_attributes': True}


class ScheduleCreate(BaseModel):
    actor_id: int
    cron: str
    payload: dict = Field(default_factory=dict)


class ScheduleOut(BaseModel):
    id: int
    actor_id: int
    cron: str
    enabled: bool
    payload: dict
    created_at: datetime

    model_config = {'from_attributes': True}


class WebhookCreate(BaseModel):
    event_type: str = 'run.finished'
    target_url: HttpUrl


class WebhookOut(BaseModel):
    id: int
    event_type: str
    target_url: str
    enabled: bool
    created_at: datetime

    model_config = {'from_attributes': True}


class UsageSummaryOut(BaseModel):
    total_runs: int
    succeeded_runs: int
    processed_requests: int


class RunCancelOut(BaseModel):
    id: int
    status: str


class RunResumeOut(BaseModel):
    id: int
    status: str
    celery_task_id: str | None


class QueueStatsOut(BaseModel):
    pending: int
    leased: int
    done: int
    failed: int



class KeyValueSet(BaseModel):
    actor_id: int
    key: str
    value: dict = Field(default_factory=dict)


class KeyValueOut(BaseModel):
    id: int
    actor_id: int
    key: str
    value: dict
    updated_at: datetime

    model_config = {'from_attributes': True}
