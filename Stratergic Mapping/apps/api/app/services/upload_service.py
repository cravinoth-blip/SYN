import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk, ParsedDocument, ProjectFile
from app.services.audit import record_audit
from app.services.document_parser import chunk_text, parse_document
from app.services.project_service import get_project
from app.services.storage import storage
from app.services.vector_store import delete_file_vectors, index_document_chunks


ALLOWED_EXTENSIONS = {".pdf": "pdf", ".pptx": "pptx"}


def _file_type(filename: str) -> str:
    lower = filename.lower()
    for extension, file_type in ALLOWED_EXTENSIONS.items():
        if lower.endswith(extension):
            return file_type
    raise HTTPException(status_code=422, detail="Only PDF and PPTX uploads are supported")


async def upload_project_file(db: Session, project_id: uuid.UUID, upload: UploadFile) -> ProjectFile:
    project = get_project(db, project_id)
    file_type = _file_type(upload.filename or "")
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    key = f"projects/{project_id}/uploads/{uuid.uuid4()}-{upload.filename}"
    storage_uri = storage.put_bytes(key, data, content_type=upload.content_type)
    record = ProjectFile(
        project_id=project.project_id,
        filename=upload.filename or "upload",
        file_type=file_type,
        storage_uri=storage_uri,
        parse_status="pending",
    )
    db.add(record)
    db.flush()

    try:
        parsed = parse_document(record.filename, data)
        parsed_document = ParsedDocument(
            file_id=record.file_id,
            extracted_text=parsed.text,
            metadata_json=parsed.metadata,
        )
        db.add(parsed_document)
        db.flush()
        chunks: list[DocumentChunk] = []
        for index, chunk in enumerate(chunk_text(parsed.text)):
            document_chunk = DocumentChunk(
                parsed_document_id=parsed_document.parsed_document_id,
                chunk_index=index,
                chunk_text=chunk,
                metadata_json={"filename": record.filename, "file_id": str(record.file_id)},
            )
            chunks.append(document_chunk)
            db.add(document_chunk)
        db.flush()
        try:
            vector_status = index_document_chunks(
                file=record,
                parsed_document=parsed_document,
                chunks=chunks,
            )
        except Exception as exc:
            vector_status = {"status": "failed", "error": str(exc)}
        record_audit(
            db,
            "file.vector_indexed",
            project_id=project.project_id,
            payload={"file_id": str(record.file_id), **vector_status},
        )
        record.parse_status = "parsed"
    except Exception as exc:
        record.parse_status = "failed"
        record_audit(
            db,
            "file.parse.failed",
            project_id=project.project_id,
            payload={"file_id": str(record.file_id), "error": str(exc)},
        )

    record_audit(
        db,
        "file.uploaded",
        project_id=project.project_id,
        payload={"file_id": str(record.file_id), "filename": record.filename},
    )
    db.commit()
    db.refresh(record)
    return record


def list_project_files(db: Session, project_id: uuid.UUID) -> list[ProjectFile]:
    get_project(db, project_id)
    return list(db.scalars(select(ProjectFile).where(ProjectFile.project_id == project_id)))


def delete_project_file(db: Session, project_id: uuid.UUID, file_id: uuid.UUID) -> None:
    file = db.get(ProjectFile, file_id)
    if not file or file.project_id != project_id:
        raise HTTPException(status_code=404, detail="File not found")
    delete_file_vectors(file.file_id)
    db.delete(file)
    record_audit(
        db,
        "file.deleted",
        project_id=project_id,
        payload={"file_id": str(file_id), "filename": file.filename},
    )
    db.commit()
