#!/bin/bash
# StockVision 서버 설치 스크립트
# Oracle Cloud VM, GCP, 또는 로컬 PC에서 실행

set -e

echo "=== StockVision 서버 설치 ==="
echo ""

# 1. Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "Docker 설치중..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker 설치 완료. 로그아웃 후 다시 로그인하고 이 스크립트를 재실행하세요."
    exit 0
fi

if ! command -v docker compose &> /dev/null; then
    echo "Docker Compose 플러그인 설치중..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

echo "Docker: $(docker --version)"
echo ""

# 2. .env 파일 생성
if [ ! -f .env ]; then
    echo ".env 파일 생성중..."

    # 랜덤 시크릿 생성
    SECRET_KEY=$(openssl rand -hex 32)
    CONFIG_ENCRYPTION_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    DATA_API_SECRET=$(openssl rand -hex 16)
    BACKTEST_API_SECRET=$(openssl rand -hex 16)

    cat > .env << EOF
# === StockVision 환경변수 ===
# 자동 생성됨 — 필요시 수정

# DB
DB_PASSWORD=${DB_PASSWORD}

# 보안 키
SECRET_KEY=${SECRET_KEY}
CONFIG_ENCRYPTION_KEY=${CONFIG_ENCRYPTION_KEY}

# 내부 API 인증
DATA_API_SECRET=${DATA_API_SECRET}
BACKTEST_API_SECRET=${BACKTEST_API_SECRET}

# AI (Claude)
ANTHROPIC_API_KEY=

# DART (금융감독원)
DART_API_KEY=

# 키움 (분봉 수집용, 선택)
KIWOOM_APP_KEY=
KIWOOM_SECRET_KEY=

# 프론트엔드 URL
CORS_ORIGINS=https://stock-vision-two.vercel.app
FRONTEND_URL=https://stock-vision-two.vercel.app

# 이 서버의 공개 URL (VM 공인 IP로 변경)
CLOUD_URL=http://localhost:4010
EOF

    echo ".env 파일 생성 완료"
    echo ""
    echo "⚠️  아래 항목을 수동으로 입력하세요:"
    echo "  - ANTHROPIC_API_KEY (Claude API 키)"
    echo "  - CLOUD_URL (VM 공인 IP, 예: http://123.45.67.89:4010)"
    echo ""
    echo ".env 수정 후 이 스크립트를 다시 실행하세요."
    echo "  nano .env  또는  vi .env"
    exit 0
fi

echo ".env 파일 확인됨"
echo ""

# 3. Docker Compose 실행
echo "서비스 빌드 + 시작중..."
docker compose -f docker-compose.oracle.yml up -d --build

echo ""
echo "서비스 시작 대기중..."
sleep 10

# 4. 헬스체크
echo ""
echo "=== 헬스체크 ==="

check_health() {
    local name=$1
    local url=$2
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$status" = "200" ]; then
        echo "  ✓ $name — 정상"
    else
        echo "  ✗ $name — 실패 (HTTP $status)"
    fi
}

check_health "클라우드 서버" "http://localhost:4010/health"
check_health "데이터 서버"   "http://localhost:4030/health"
check_health "백테스트 서버" "http://localhost:4040/health"

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "서비스 URL:"
echo "  클라우드 서버:  http://localhost:4010"
echo "  데이터 서버:    http://localhost:4030"
echo "  백테스트 서버:  http://localhost:4040"
echo ""
echo "로그 확인: docker compose -f docker-compose.oracle.yml logs -f"
echo "중지:     docker compose -f docker-compose.oracle.yml down"
echo "재시작:   docker compose -f docker-compose.oracle.yml restart"
