from fastapi import FastAPI
import auth,message,user_chat
from database import Base, engine
from models import User,message,prompt

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth.router)
app.include_router(message.router)
app.include_router(user_chat.router)
@app.get("/")
async def root():
    return {"message": "AgenticFleet API is running!"}
