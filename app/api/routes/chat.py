"""Conversation endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Request

from app.api.schemas.chat import ChatRequest, ChatResponse, SourceResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def create_chat_answer(payload: ChatRequest, request: Request) -> ChatResponse:
    service = request.app.state.chat_service
    answer = await service.answer(
        payload.message,
        [message.model_dump() for message in payload.history],
    )
    sources = [SourceResponse(**asdict(source)) for source in answer.sources]
    return ChatResponse(answer=answer.answer, sources=sources, refused=answer.refused)
