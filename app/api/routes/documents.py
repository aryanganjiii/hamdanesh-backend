"""Knowledge library endpoints."""

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents(request: Request) -> dict:
    service = request.app.state.document_service
    return {"documents": service.list_documents(), "stats": service.stats()}


@router.post("/documents", status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form("عمومی"),
) -> dict:
    service = request.app.state.document_service
    settings = request.app.state.settings
    raw = await file.read(settings.max_file_bytes + 1)
    await file.close()
    result = await service.add_document(
        filename=file.filename or "document.txt",
        media_type=file.content_type or "application/octet-stream",
        raw=raw,
        category=category,
    )
    return {"document": result, "stats": service.stats()}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, request: Request) -> JSONResponse:
    service = request.app.state.document_service
    if not service.delete_document(document_id):
        return JSONResponse(status_code=404, content={"error": "سند پیدا نشد."})
    return JSONResponse(status_code=200, content={"ok": True, "stats": service.stats()})


@router.post("/samples/import", status_code=201)
async def import_sample_documents(request: Request) -> dict:
    service = request.app.state.document_service
    documents = await service.import_samples()
    return {"documents": documents, "stats": service.stats()}
