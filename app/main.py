import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.services.chat import listen_pubsub


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    task = asyncio.create_task(listen_pubsub())
    yield
    task.cancel()
    await engine.dispose()


app = FastAPI(title="Ghost IRC Chat", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Ghost IRC Chat"}
