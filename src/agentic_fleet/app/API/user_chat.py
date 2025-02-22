from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from auth import get_current_user ,db_dependency
from typing import Annotated

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

user_dependency = Annotated[dict, Depends(get_current_user)]

class prompt(BaseModel):
    prompt: str
    user_id: int

@router.post("/prompt")
async def send_prompt(request: prompt , db: db_dependency , user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    await db.prompts.create(user_id=request.user_id, prompt=request.prompt)
    return {"message": "Prompt sent"}

@router.put("/prompt")
async def update_prompt(request: prompt , db: db_dependency , user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    await db.prompts.update(user_id=request.user_id, prompt=request.prompt)
    return {"message": "Prompt updated"}

@router.get("/prompt")
async def get_prompt(db: db_dependency , user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await db.query(prompt).filter(prompt.user_id == user['id']).all()