from fastapi import FastAPI
from app.auth import router as auth_router
from app.chat import router as chat_router
from app.database import engine, Base

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="IRC Chat MVP")

app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to IRC Chat MVP API"}
