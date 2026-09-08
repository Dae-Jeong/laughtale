from fastapi import APIRouter

from chat_service.http.errors import PROBLEM_RESPONSES
from chat_service.schemas.responses import MessageData, Success

router = APIRouter()


@router.get("/", responses=PROBLEM_RESPONSES)
def index() -> Success[MessageData]:
    return Success(data=MessageData(message="Chat service"))
