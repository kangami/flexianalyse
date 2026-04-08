import logging
import os
import json
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency
    psycopg = None

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - optional dependency
    boto3 = None
    BotoCoreError = Exception
    ClientError = Exception

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AWSPersistenceService:
    def __init__(self) -> None:
        self.enabled = os.getenv("AWS_STORAGE_ENABLED", "false").lower() == "true"
        self.disabled_reason = ""
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.database_url = os.getenv("DATABASE_URL", "")
        self.documents_bucket = os.getenv("AWS_S3_BUCKET_DOCUMENTS")

        self._session = None
        self._s3 = None

        if not self.enabled:
            self.disabled_reason = "AWS_STORAGE_ENABLED=false"
            logger.info("AWS persistence disabled (AWS_STORAGE_ENABLED=false)")
            return

        if boto3 is None:
            self.disabled_reason = "boto3 unavailable"
            logger.warning("AWS persistence enabled but boto3 is unavailable")
            self.enabled = False
            return

        if not self.documents_bucket:
            self.disabled_reason = "AWS_S3_BUCKET_DOCUMENTS missing"
            logger.warning("AWS persistence enabled but AWS_S3_BUCKET_DOCUMENTS is missing")
            self.enabled = False
            return

        if not self.database_url or psycopg is None:
            self.disabled_reason = "DATABASE_URL / psycopg missing"
            logger.warning("AWS persistence enabled but PostgreSQL is not configured (DATABASE_URL / psycopg missing)")
            self.enabled = False
            return

        try:
            self._session = boto3.session.Session(region_name=self.region)
            self._s3 = self._session.client("s3")
            logger.info(
                "AWS persistence initialized (region=%s, bucket=%s)",
                self.region,
                self.documents_bucket,
            )
        except Exception as exc:
            self.disabled_reason = f"init_error: {str(exc)}"
            logger.error("Failed to initialize AWS persistence: %s", exc)
            self.enabled = False

    def _get_pg_connection(self):
        database_url = os.getenv("DATABASE_URL", self.database_url)
        if psycopg is None:
            raise RuntimeError("psycopg is not available")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing")
        return psycopg.connect(database_url)

    def _resolve_user_context(self, conn, email: Optional[str]):
        if not email:
            return None, None

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id::text, uo.organization_id::text
                FROM users u
                LEFT JOIN user_organizations uo ON uo.user_id = u.id
                WHERE u.email = %s
                ORDER BY uo.joined_at ASC NULLS LAST
                LIMIT 1
                """,
                (email,)
            )
            row = cursor.fetchone()

        if not row:
            return None, None
        return row[0], row[1]

    def persist_user_profile(self, user_data: Dict[str, Any], firebase_payload: Optional[Dict[str, Any]] = None) -> bool:
        if not self.enabled:
            return False

        email = user_data.get("email")
        if not email:
            logger.warning("Cannot persist user profile without email")
            return False

        now_iso = _utc_now_iso()
        item = {
            "email": email,
            "firebase_uid": user_data.get("firebase_uid") or (firebase_payload or {}).get("uid") or "",
            "name": user_data.get("name") or email.split("@")[0],
            "provider": user_data.get("provider") or "email",
            "plan": user_data.get("plan") or "free",
            "phone": user_data.get("phone") or "",
            "updated_at": now_iso,
            "last_login": now_iso,
        }

        if firebase_payload:
            item["email_verified"] = bool(firebase_payload.get("email_verified", False))

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE users
                        SET firebase_uid = COALESCE(NULLIF(%s, ''), firebase_uid),
                            name = COALESCE(NULLIF(%s, ''), name),
                            provider = COALESCE(NULLIF(%s, ''), provider),
                            phone = COALESCE(NULLIF(%s, ''), phone),
                            updated_at = now(),
                            last_login_at = now()
                        WHERE email = %s
                        """,
                        (
                            item.get("firebase_uid", ""),
                            item.get("name", ""),
                            item.get("provider", ""),
                            item.get("phone", ""),
                            email,
                        )
                    )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("Failed to persist user profile to PostgreSQL: %s", exc)
            return False

    def persist_document(
        self,
        *,
        file_name: str,
        content: str,
        raw_bytes: Optional[bytes] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_email: Optional[str] = None,
        session_id: Optional[str] = None,
        source: str = "index-directory",
    ) -> Dict[str, Any]:
        if not self.enabled or not self._s3:
            return {
                "stored": False,
                "reason": "aws_disabled",
                "details": self.disabled_reason or "AWS persistence service not initialized",
            }

        safe_session_id = session_id or "anonymous"
        owner = user_email or "anonymous"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        s3_key = f"documents/{owner}/{safe_session_id}/{timestamp}_{file_name}"
        upload_bytes = raw_bytes if raw_bytes is not None else (content or "").encode("utf-8")
        upload_content_type = mime_type or ("application/octet-stream" if raw_bytes is not None else "text/plain; charset=utf-8")

        try:
            put_result = self._s3.put_object(
                Bucket=self.documents_bucket,
                Key=s3_key,
                Body=upload_bytes,
                ContentType=upload_content_type,
                Metadata={
                    "owner": owner[:256],
                    "session_id": safe_session_id[:256],
                    "source": source[:256],
                    "file_name": file_name[:256],
                },
            )
        except (BotoCoreError, ClientError, Exception) as exc:
            logger.error("Failed to upload document to S3: %s", exc)
            return {"stored": False, "reason": "s3_error", "error": str(exc)}

        try:
            document_id = str(uuid4())
            with self._get_pg_connection() as conn:
                user_id, organization_id = self._resolve_user_context(conn, user_email)
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO documents (
                            id,
                            organization_id,
                            uploaded_by_user_id,
                            file_name,
                            mime_type,
                            size_bytes,
                            s3_bucket,
                            s3_key,
                            etag,
                            status,
                            metadata,
                            created_at
                        )
                        VALUES (
                            %s::uuid,
                            %s::uuid,
                            %s::uuid,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            'uploaded',
                            %s::jsonb,
                            now()
                        )
                        """,
                        (
                            document_id,
                            organization_id,
                            user_id,
                            file_name,
                            upload_content_type,
                            len(upload_bytes),
                            self.documents_bucket,
                            s3_key,
                            put_result.get("ETag", "").strip('"'),
                            json.dumps(metadata or {}),
                        )
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Document uploaded to S3 but PostgreSQL metadata write failed: %s", exc)
            return {
                "stored": True,
                "metadata_stored": False,
                "document_id": None,
                "organization_id": None,
                "s3_key": s3_key,
                "error": str(exc),
            }

        return {
            "stored": True,
            "metadata_stored": True,
            "document_id": document_id,
            "organization_id": organization_id,
            "s3_key": s3_key,
        }

    def persist_document_chunks(
        self,
        *,
        document_id: str,
        organization_id: str,
        chunks: List[str],
        embeddings: List[List[float]],
        metadata: Optional[Dict[str, Any]] = None,
        per_chunk_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not document_id or not organization_id:
            return {"stored": False, "reason": "missing_document_or_organization"}

        if not chunks or not embeddings:
            return {"stored": False, "reason": "no_chunks"}

        if len(chunks) != len(embeddings):
            return {"stored": False, "reason": "chunks_embeddings_mismatch"}

        if per_chunk_metadata and len(per_chunk_metadata) != len(chunks):
            return {"stored": False, "reason": "per_chunk_metadata_length_mismatch"}

        shared_meta = metadata or {}

        try:
            with self._get_pg_connection() as conn:
                with conn.cursor() as cursor:
                    for idx, (content, vector_values) in enumerate(zip(chunks, embeddings)):
                        vector_literal = "[" + ",".join(str(x) for x in vector_values) + "]"
                        chunk_meta = {**shared_meta, **(per_chunk_metadata[idx] if per_chunk_metadata else {})}
                        cursor.execute(
                            """
                            INSERT INTO document_chunks (
                                id,
                                document_id,
                                organization_id,
                                chunk_index,
                                content,
                                embedding,
                                metadata,
                                created_at
                            )
                            VALUES (
                                %s::uuid,
                                %s::uuid,
                                %s::uuid,
                                %s,
                                %s,
                                %s::vector,
                                %s::jsonb,
                                now()
                            )
                            """,
                            (
                                str(uuid4()),
                                document_id,
                                organization_id,
                                idx,
                                content,
                                vector_literal,
                                json.dumps(chunk_meta),
                            ),
                        )
                conn.commit()
            return {"stored": True, "chunks_count": len(chunks)}
        except Exception as exc:
            logger.error("Failed to persist document chunks to pgvector: %s", exc)
            return {"stored": False, "reason": "pgvector_error", "error": str(exc)}


aws_persistence_service = AWSPersistenceService()
