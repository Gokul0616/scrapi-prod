from fastapi import FastAPI

from app.api.routes import router
from app.db.session import Base, engine

app = FastAPI(title='Scrapi API')


@app.get('/v1/health')
def health():
    return {'status': 'ok'}


@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)


app.include_router(router, prefix='/v1')
