"""법적 문서 시드 데이터 — legal_documents 테이블 초기화.

사용법:
    python -m cloud_server.scripts.seed_legal_documents

docs/legal/ 의 마크다운 원문을 읽어 DB에 삽입한다.
이미 같은 (doc_type, version) 조합이 있으면 건너뛴다.
"""
from datetime import date
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from cloud_server.core.database import SessionLocal
from cloud_server.models.legal import LegalDocument

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "legal"

SEED_DATA = [
    {
        "doc_type": "terms",
        "version": "1.0",
        "title": "StockVision 이용약관",
        "file": "terms-of-service.md",
        "effective_date": date(2026, 3, 9),
    },
    {
        "doc_type": "privacy",
        "version": "1.0",
        "title": "StockVision 개인정보처리방침",
        "file": "privacy-policy.md",
        "effective_date": date(2026, 3, 9),
    },
    {
        "doc_type": "disclaimer",
        "version": "1.0",
        "title": "StockVision 투자 위험 고지",
        "file": "disclaimer.md",
        "effective_date": date(2026, 3, 9),
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        for item in SEED_DATA:
            content_md = (DOCS_DIR / item["file"]).read_text(encoding="utf-8")
            doc = LegalDocument(
                doc_type=item["doc_type"],
                version=item["version"],
                title=item["title"],
                content_md=content_md,
                effective_date=item["effective_date"],
            )
            db.add(doc)
            try:
                db.commit()
                print(f"  ✅ {item['doc_type']} v{item['version']} 삽입 완료")
            except IntegrityError:
                db.rollback()
                print(f"  ⏭️  {item['doc_type']} v{item['version']} 이미 존재 — 건너뜀")
    finally:
        db.close()


if __name__ == "__main__":
    print("법적 문서 시드 데이터 삽입 시작...")
    seed()
    print("완료.")
