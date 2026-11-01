"""Chat API schemas."""

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: str
    content: str = Field(max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[HistoryMessage] = Field(default_factory=list)


class SourceResponse(BaseModel):
    id: str
    chunk_id: str
    title: str
    filename: str
    category: str
    heading_path: str = ""
    snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    refused: bool
