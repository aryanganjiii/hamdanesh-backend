"""FastAPI application factory and dependency wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import Settings
from app.core.errors import ApplicationError
from app.domain.text_chunker import TextChunker
from app.domain.text_normalizer import PersianTextNormalizer
from app.infrastructure.parsers.document_parser import DocumentParser
from app.infrastructure.persistence.sqlite_database import SQLiteDatabase
from app.infrastructure.persistence.sqlite_document_repository import SQLiteDocumentRepository
from app.infrastructure.providers.avalai_client import AvalAIClient
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.retrieval_service import HybridRetriever


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or Settings.from_environment()
    database = SQLiteDatabase(application_settings.database_path)
    repository = SQLiteDocumentRepository(database)
    normalizer = PersianTextNormalizer()
    ai_provider = AvalAIClient(application_settings)
    chunker = TextChunker(application_settings.chunk_size, application_settings.chunk_overlap)
    parser = DocumentParser()
    document_service = DocumentService(
        settings=application_settings,
        repository=repository,
        parser=parser,
        normalizer=normalizer,
        chunker=chunker,
        ai_provider=ai_provider,
    )
    retriever = HybridRetriever(repository, ai_provider, normalizer)
    chat_service = ChatService(application_settings, retriever, ai_provider)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        try:
            yield
        finally:
            await ai_provider.close()

    app = FastAPI(
        title="هم‌دانش | سامانه‌ی مدیریت دانش سازمانی",
        description="دستیار فارسی مبتنی بر RAG برای جست‌وجو در اسناد سازمانی",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.state.settings = application_settings
    app.state.document_service = document_service
    app.state.chat_service = chat_service
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(chat_router)

    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"error": error.message})

    return app


app = create_app()
