#!/bin/bash
# Render PostgreSQL → 새 서버로 데이터 이관
# 사용법: ./scripts/migrate-render-data.sh

set -e

echo "=== Render DB 데이터 이관 ==="

RENDER_URL="postgresql://stockvision_user:JUvDY2IQm3vaBJcsEoCjbhKXdVL1jpjP@dpg-d6pfa4vkijhs73a9k4ag-a.oregon-postgres.render.com/stockvision_psbw"

# .env에서 DB 비밀번호 읽기
if [ -f .env ]; then
    source .env
fi
LOCAL_URL="postgresql://stockvision:${DB_PASSWORD:-stockvision_pass}@localhost:5432/stockvision"

echo "1. Render DB 덤프중..."
pg_dump "$RENDER_URL" --no-owner --no-acl -F custom -f render_backup.dump

echo "2. 새 DB에 복원중..."
pg_restore -d "$LOCAL_URL" --no-owner --no-acl --clean --if-exists render_backup.dump || true

echo "3. 테이블별 행 수 확인..."
psql "$LOCAL_URL" -c "
SELECT schemaname, tablename,
       (SELECT count(*) FROM information_schema.tables) as tables
FROM pg_tables WHERE schemaname = 'public'
ORDER BY tablename;
"

echo ""
echo "=== 이관 완료 ==="
echo "덤프 파일: render_backup.dump (필요 없으면 삭제)"
