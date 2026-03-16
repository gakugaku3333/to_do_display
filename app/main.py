from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import dashboard, tasks
from app.scheduler import refresh_data, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    await refresh_data()
    yield
    stop_scheduler()


app = FastAPI(title="Family Dashboard", lifespan=lifespan)

app.include_router(dashboard.router)
app.include_router(tasks.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
