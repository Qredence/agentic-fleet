from fastapi import Depends, HTTPException, status ,APIRouter
from pydantic import BaseModel
from auth import get_current_user ,db_dependency
from typing import Annotated

router = APIRouter(
    prefix="/message",
    tags=["message"]
)

user_dependency = Annotated[dict, Depends(get_current_user)]

class MessageRequest(BaseModel):
    user_id: str
    message: str

@router.post("/chat/send")
async def send_message(request: MessageRequest , db: db_dependency , user: user_dependency):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    await db.messages.create(user_id=request.user_id, message=request.message)
    return {"message": "Message sent"}


