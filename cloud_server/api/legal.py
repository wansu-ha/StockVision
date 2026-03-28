"""법적 문서 조회 및 동의 기록 API

GET  /api/v1/legal/documents/{doc_type}           최신 약관 조회 (공개)
GET  /api/v1/legal/consent/status                 동의 현황 (인증 필요)
POST /api/v1/legal/consent                        동의 기록 (인증 필요)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from cloud_server.core.database import get_db
from cloud_server.models.legal import LegalConsent, LegalDocument
from cloud_server.api.dependencies import current_user

router = APIRouter(prefix="/api/v1/legal", tags=["legal"])

# 현재 유효한 약관 버전
CURRENT_VERSIONS: dict[str, str] = {
    "terms": "1.1",
    "privacy": "1.1",
    "disclaimer": "1.1",
}


@router.get("/documents/{doc_type}")
def get_document(doc_type: str, db: Session = Depends(get_db)):
    """최신 버전 법적 문서 조회 (공개)"""
    if doc_type not in CURRENT_VERSIONS:
        raise HTTPException(404, "문서 유형을 찾을 수 없습니다.")

    doc = (
        db.query(LegalDocument)
        .filter(LegalDocument.doc_type == doc_type)
        .order_by(desc(LegalDocument.created_at))
        .first()
    )

    if not doc:
        # DB에 없으면 빈 응답 (시드 전)
        return {
            "success": True,
            "data": {
                "doc_type": doc_type,
                "version": CURRENT_VERSIONS[doc_type],
                "title": {"terms": "이용약관", "privacy": "개인정보처리방침", "disclaimer": "투자 위험 고지"}.get(doc_type, doc_type),
                "content_md": "",
                "effective_date": None,
            },
        }

    return {
        "success": True,
        "data": {
            "doc_type": doc.doc_type,
            "version": doc.version,
            "title": doc.title,
            "content_md": doc.content_md,
            "effective_date": str(doc.effective_date) if doc.effective_date else None,
        },
    }


@router.get("/consent/status")
def consent_status(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """현재 사용자의 동의 현황"""
    consents = (
        db.query(LegalConsent)
        .filter(LegalConsent.user_id == user["sub"])
        .all()
    )

    # 각 doc_type별 최신 동의 버전
    latest_by_type: dict[str, LegalConsent] = {}
    for c in consents:
        existing = latest_by_type.get(c.doc_type)
        if not existing or c.agreed_at > existing.agreed_at:
            latest_by_type[c.doc_type] = c

    result = {}
    for doc_type, current_ver in CURRENT_VERSIONS.items():
        consent = latest_by_type.get(doc_type)
        result[doc_type] = {
            "agreed_version": consent.doc_version if consent else None,
            "agreed_at": consent.agreed_at.isoformat() if consent else None,
            "latest_version": current_ver,
            "up_to_date": consent.doc_version == current_ver if consent else False,
        }

    return {"success": True, "data": result}


class ConsentBody(BaseModel):
    doc_type: str
    doc_version: str


@router.post("/consent")
def record_consent(
    body: ConsentBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """동의 기록 저장"""
    if body.doc_type not in CURRENT_VERSIONS:
        raise HTTPException(400, "잘못된 문서 유형입니다.")

    consent = LegalConsent(
        user_id=user["sub"],
        doc_type=body.doc_type,
        doc_version=body.doc_version,
    )
    db.add(consent)
    db.commit()

    return {"success": True, "data": {"doc_type": body.doc_type, "doc_version": body.doc_version}}
