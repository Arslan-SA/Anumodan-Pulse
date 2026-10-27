"""
AICTE FlowOps — Document Service

Manages secure document uploads, MIME/magic-byte validations, storage interactions,
authorization boundaries, and document expiry tracking.
"""

from datetime import datetime, timedelta, timezone
import math
import os
import re
from typing import BinaryIO, List, Optional, Tuple
import uuid

from fastapi import HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.application import Application
from app.models.compliance import ComplianceRecord
from app.models.document import Document
from app.models.enums import ComplianceStatus, UserRole
from app.models.institution import Institution
from app.models.user import User
from app.schemas.document import DocumentExpiringResponse
from app.services.storage import get_storage_backend


ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _detect_mime_type_from_bytes(header: bytes) -> Optional[str]:
    """Detect authentic MIME type using file signature magic bytes."""
    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\xd0\xcf\x11\xe0"):
        return "application/msword"
    if header.startswith(b"PK\x03\x04"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return None


class DocumentService:

    @staticmethod
    async def upload_document(
        db: Session,
        user: User,
        file: UploadFile,
        document_name: str,
        document_type: str,
        application_id: Optional[uuid.UUID] = None,
        compliance_record_id: Optional[uuid.UUID] = None,
        expires_at: Optional[datetime] = None,
    ) -> Document:
        """
        Securely upload and register a document.
        - Validates authenticated user affiliations
        - Enforces file size, extension, and magic-byte checks
        - Isolates files in backend storage with opaque keys
        - Stores metadata without exposing private storage paths
        """
        # Determine institution affiliation
        if user.role == UserRole.INSTITUTION_USER:
            if not user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is not affiliated with an approved institution.",
                )
            institution_id = user.institution_id
        elif user.role in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            # For officials, require either target application or compliance record to infer institution
            if compliance_record_id:
                cr = db.scalar(select(ComplianceRecord).where(ComplianceRecord.id == compliance_record_id))
                if not cr:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance record not found.")
                institution_id = cr.institution_id
            elif application_id:
                app = db.scalar(select(Application).where(Application.id == application_id))
                if not app:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
                institution_id = app.institution_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Must associate document with an application or compliance record.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reviewers are not permitted to upload documents.",
            )

        # Validate target application ownership if provided
        target_app: Optional[Application] = None
        if application_id:
            target_app = db.scalar(select(Application).where(Application.id == application_id))
            if not target_app or target_app.institution_id != institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Application '{application_id}' not found or belongs to another institution.",
                )

        # Validate target compliance record ownership if provided
        target_compliance: Optional[ComplianceRecord] = None
        if compliance_record_id:
            target_compliance = db.scalar(select(ComplianceRecord).where(ComplianceRecord.id == compliance_record_id))
            if not target_compliance or target_compliance.institution_id != institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Compliance record '{compliance_record_id}' not found or belongs to another institution.",
                )
            # Cannot attach documents to an already verified compliance record
            if target_compliance.status == ComplianceStatus.VERIFIED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot attach new documents to a VERIFIED compliance record.",
                )
            # Sync application_id if not explicitly provided
            if not application_id and target_compliance.application_id:
                application_id = target_compliance.application_id

        # ── File Validations ───────────────────────────────────────────
        raw_filename = file.filename or "uploaded_file"
        _, ext = os.path.splitext(raw_filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS.keys())}.",
            )

        # Read header for magic bytes and size check
        max_bytes = settings.storage_max_file_size_mb * 1024 * 1024
        header = await file.read(2048)
        if not header:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        rest = await file.read()
        file_size = len(header) + len(rest)

        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {settings.storage_max_file_size_mb}MB.",
            )

        # Validate authentic MIME type via magic bytes
        detected_mime = _detect_mime_type_from_bytes(header)
        expected_mime = ALLOWED_EXTENSIONS.get(ext)
        if not detected_mime or (detected_mime != expected_mime):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match expected format for extension '{ext}'.",
            )

        # Reset pointer for backend storage
        await file.seek(0)

        # ── Safe Storage Key ───────────────────────────────────────────
        safe_base = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw_filename)
        unique_token = uuid.uuid4().hex[:12]
        storage_key = f"institutions/{institution_id}/{unique_token}_{safe_base}"

        # Write to storage abstraction
        storage = get_storage_backend()
        storage.save(storage_key, file.file, content_type=detected_mime)

        # Register metadata in database
        doc = Document(
            institution_id=institution_id,
            application_id=application_id,
            compliance_record_id=compliance_record_id,
            document_name=document_name.strip(),
            document_type=document_type.strip(),
            storage_key=storage_key,
            mime_type=detected_mime,
            file_size=file_size,
            uploaded_by_user_id=user.id,
            expires_at=expires_at,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_document_metadata(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> Document:
        """
        Retrieve document metadata while enforcing institution-level access control.
        Internal storage keys and filesystem paths are never returned to client.
        """
        doc = db.scalar(
            select(Document)
            .options(
                joinedload(Document.institution),
                joinedload(Document.application),
                joinedload(Document.compliance_record),
            )
            .where(Document.id == document_id)
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )

        # Authorization check
        if user.role == UserRole.INSTITUTION_USER:
            if doc.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{document_id}' not found.",
                )
        elif user.role == UserRole.REVIEWER:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reviewers cannot access unassigned documents.",
            )

        return doc

    @staticmethod
    def download_document(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ):
        """
        Serve document securely based on configured storage backend.
        Enforces strict authorization prior to delivery.
        """
        doc = DocumentService.get_document_metadata(db, document_id, user)
        storage = get_storage_backend()

        if not storage.exists(doc.storage_key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The requested document file could not be found on storage.",
            )

        if settings.storage_backend == "local":
            local_path = storage.get_local_path(doc.storage_key)
            if not local_path or not os.path.exists(local_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Local file not found.",
                )
            # Sanitize filename for download header
            clean_filename = re.sub(r'[^\w\s.-]', '_', doc.document_name)
            return FileResponse(
                path=local_path,
                media_type=doc.mime_type or "application/octet-stream",
                filename=f"{clean_filename}{os.path.splitext(doc.storage_key)[1]}",
            )
        else:
            download_url = storage.get_download_url(doc.storage_key)
            if not download_url:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate secure download URL.",
                )
            return RedirectResponse(url=download_url)

    @staticmethod
    def delete_document(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> None:
        """
        Delete a document.
        - Only institution user who owns the institution may delete (or Admin).
        - Document cannot be deleted if attached to a VERIFIED compliance record.
        - Applications or compliance records are not cascaded.
        """
        doc = db.scalar(
            select(Document)
            .options(joinedload(Document.compliance_record))
            .where(Document.id == document_id)
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )

        if user.role == UserRole.INSTITUTION_USER:
            if doc.institution_id != user.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document '{document_id}' not found.",
                )
        elif user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owning institution or an administrator can delete documents.",
            )

        # Protect verified compliance submissions
        if doc.compliance_record and doc.compliance_record.status == ComplianceStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a document that is part of a VERIFIED statutory compliance record.",
            )

        storage = get_storage_backend()
        try:
            storage.delete(doc.storage_key)
        except Exception:
            # Storage delete error should not prevent DB consistency
            pass

        db.delete(doc)
        db.commit()

    @staticmethod
    def list_expiring_documents(
        db: Session,
        user: User,
        days_window: int = 30,
    ) -> List[DocumentExpiringResponse]:
        """
        Query documents expiring within a given window (default: next 30 days).
        Excludes documents without an expiry date.
        Enforces institution-level data isolation.
        """
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(days=days_window)

        query = (
            select(Document)
            .options(
                joinedload(Document.institution),
                joinedload(Document.application),
                joinedload(Document.compliance_record),
            )
            .where(
                Document.expires_at.is_not(None),
                Document.expires_at >= now,
                Document.expires_at <= window_end,
            )
            .order_by(Document.expires_at.asc())
        )

        if user.role == UserRole.INSTITUTION_USER:
            if not user.institution_id:
                return []
            query = query.where(Document.institution_id == user.institution_id)
        elif user.role in [UserRole.ADMIN, UserRole.AICTE_OFFICIAL]:
            # Officials have cross-institution access
            pass
        elif user.role == UserRole.REVIEWER:
            return []

        docs = db.scalars(query).all()

        results: List[DocumentExpiringResponse] = []
        for d in docs:
            days_left = max(0, (d.expires_at - now).days)
            results.append(
                DocumentExpiringResponse(
                    id=d.id,
                    document_name=d.document_name,
                    document_type=d.document_type,
                    institution_id=d.institution_id,
                    institution_name=d.institution.institution_name if d.institution else None,
                    expires_at=d.expires_at,

                    days_until_expiry=days_left,
                    application_id=d.application_id,
                    application_number=d.application.application_number if d.application else None,
                    compliance_record_id=d.compliance_record_id,
                    compliance_title=d.compliance_record.title if d.compliance_record else None,
                )
            )

        return results
