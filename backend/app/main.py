from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from app.api import stocks
from app.api.ai_analysis import router as ai_analysis_router
from app.services.cache_scheduler import CacheScheduler
from app.core.api_logging import api_logger_instance
import uuid
import datetime
import sqlite3
import os
from dotenv import load_dotenv

# 환경 변수 로딩
load_dotenv()

# 전역 서비스 인스턴스 (순환 참조 방지)
stock_list_service = None
stock_data_service = None
cache_scheduler = None

def get_stock_list_service():
    """주식 목록 서비스 인스턴스 반환 (싱글톤)"""
    global stock_list_service
    if stock_list_service is None:
        from app.services.stock_list_service import StockListService
        stock_list_service = StockListService()
    return stock_list_service

def get_stock_data_service():
    """주식 데이터 서비스 인스턴스 반환 (싱글톤)"""
    global stock_data_service
    if stock_data_service is None:
        from app.services.stock_data_service import StockDataService
        stock_data_service = StockDataService()
    return stock_data_service

app = FastAPI(
    title="StockVision API",
    description="""
    🚀 **AI 기반 주식 동향 예측 및 가상 거래 시스템**
    
    ## 주요 기능
    - 📊 **주식 데이터 수집**: yfinance를 통한 실시간 데이터
    - 🤖 **AI 예측 모델**: Random Forest, LSTM 기반 주가 예측
    - 💼 **가상 거래 시스템**: 리스크 없는 투자 전략 검증
    - 📈 **기술적 지표**: RSI, MACD, EMA, 볼린저 밴드 등
    
    ## 기술 스택
    - **Backend**: FastAPI + Python 3.13.7
    - **Database**: SQLite (개발) → PostgreSQL (운영)
    - **ML**: scikit-learn, TensorFlow, Keras
    - **Data**: yfinance, pandas, numpy
    
    ## 빠른 시작
    1. `/docs` - Swagger UI (상세한 API 문서)
    2. `/redoc` - ReDoc (읽기 쉬운 문서)
    3. `/rapidoc` - RapiDoc (현대적인 UI)
    4. `/health` - 서버 상태 확인
    """,
    version="1.0.0",
    contact={
        "name": "StockVision Team",
        "email": "contact@stockvision.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url=None,  # 기본 Swagger UI 비활성화
    redoc_url=None,  # 기본 ReDoc 비활성화
)

# API 로깅 미들웨어 (먼저 정의)
@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    """API 요청/응답 로깅"""
    import time
    import logging
    
    # 로거 설정
    logger = logging.getLogger(__name__)
    
    # 로깅이 필요 없는 API 경로들
    exclude_paths = [
        # 로그 관련 API (자체 로깅 제외)
        "/api/v1/logs/stats",      # 로그 통계 API
        "/api/v1/logs/entries",    # 로그 엔트리 API
        "/api/v1/logs/stream",     # 로그 스트리밍 API
        "/api/v1/logs/",           # 로그 대시보드 페이지
        
        # 메인 페이지 및 문서 (로깅 불필요)
        "/",                       # 메인 페이지
        "/docs",                   # Swagger UI
        "/redoc",                  # ReDoc
        "/rapidoc",                # RapiDoc
        "/test",                   # 테스트 엔드포인트
        "/health",                 # 헬스체크
        "/api-info",               # API 정보
        
        # 정적 파일 (로깅 불필요)
        "/favicon.ico",            # 파비콘
        "/.well-known/",           # 웰노운 파일들
    ]
    
    # 로깅 제외 여부 확인
    should_log = True
    for exclude_path in exclude_paths:
        if request.url.path.startswith(exclude_path):
            should_log = False
            break
    
    # 로깅이 필요한 경우에만 처리
    if should_log:
        # 고유 추적 ID 생성
        trace_id = str(uuid.uuid4())
        
        # 요청 로깅
        request_data = api_logger_instance.log_request(request, trace_id)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 응답 로깅
            api_logger_instance.log_response(request_data, response, process_time, response.status_code)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # 오류 로깅
            api_logger_instance.log_error(request_data, e, process_time)
            raise
    else:
        # 로깅하지 않고 바로 처리
        logger.debug(f"로깅 제외 API: {request.method} {request.url.path}")
        return await call_next(request)

# 성능 모니터링 미들웨어
@app.middleware("http")
async def performance_monitoring(request: Request, call_next):
    """성능 모니터링 및 캐시 스케줄러 작업 체크"""
    import time
    import logging
    
    # 로거 설정
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    
    # 캐시 스케줄러 작업 체크 (APScheduler 없을 때 기본 스케줄링)
    if cache_scheduler:
        cache_scheduler.check_and_run_tasks()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 시간이 1초 이상이면 로그 기록
        if process_time > 1.0:
            logger.warning(f"느린 API 응답: {request.method} {request.url.path} - {process_time:.3f}초")
        
        # 응답 헤더에 처리 시간 추가
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"API 오류: {request.method} {request.url.path} - {process_time:.3f}초 - {e}")
        raise

# CORS 설정 (모든 미들웨어 이후에 추가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite 개발 서버
        "http://localhost:3000",  # React 개발 서버 (백업)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 통계 함수
def get_database_stats():
    try:
        db_path = "stockvision.db"
        if not os.path.exists(db_path):
            return {
                "total_stocks": 0,
                "total_prices": 0,
                "total_indicators": 0,
                "last_updated": "N/A"
            }
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 주식 수
        cursor.execute("SELECT COUNT(*) FROM stocks")
        total_stocks = cursor.fetchone()[0]
        
        # 가격 데이터 수
        cursor.execute("SELECT COUNT(*) FROM stock_prices")
        total_prices = cursor.fetchone()[0]
        
        # 기술적 지표 수
        cursor.execute("SELECT COUNT(*) FROM technical_indicators")
        total_indicators = cursor.fetchone()[0]
        
        # 마지막 업데이트
        cursor.execute("SELECT MAX(date) FROM stock_prices")
        last_date = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_stocks": total_stocks,
            "total_prices": total_prices,
            "total_indicators": total_indicators,
            "last_updated": last_date or "N/A"
        }
    except Exception as e:
        return {
            "total_stocks": 0,
            "total_prices": 0,
            "total_indicators": 0,
            "last_updated": "Error"
        }

# 커스텀 OpenAPI 스키마
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 태그 정보 추가
    openapi_schema["tags"] = [
        {
            "name": "stocks",
            "description": "주식 정보 및 데이터 관련 API",
            "externalDocs": {
                "description": "주식 데이터 가이드",
                "url": "https://stockvision.com/docs/stocks",
            },
        },
        {
            "name": "predictions",
            "description": "AI 기반 주가 예측 API",
            "externalDocs": {
                "description": "예측 모델 가이드",
                "url": "https://stockvision.com/docs/predictions",
            },
        },
        {
            "name": "trading",
            "description": "가상 거래 및 백테스팅 API",
            "externalDocs": {
                "description": "거래 시스템 가이드",
                "url": "https://stockvision.com/docs/trading",
            },
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# API 라우터 등록
app.include_router(stocks.router, prefix="/api/v1", tags=["stocks"])
app.include_router(ai_analysis_router, prefix="/api/v1/ai-analysis", tags=["ai-analysis"])

# 로그 API 라우터 등록
from app.api import logs
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])

# 캐시 스케줄러 초기화 및 시작
@app.on_event("startup")
async def startup_event():
    global cache_scheduler
    try:
        # 캐시 스케줄러 초기화
        cache_scheduler = CacheScheduler()
        
        # 서비스 인스턴스 설정
        stock_list_service = get_stock_list_service()
        stock_data_service = get_stock_data_service()
        
        cache_scheduler.set_services(stock_list_service, stock_data_service)
        cache_scheduler.setup_jobs()
        cache_scheduler.start()
        
        print("✅ 캐시 스케줄러 시작됨")
        
    except Exception as e:
        print(f"❌ 캐시 스케줄러 시작 실패: {e}")

# 기본 스케줄링을 위한 주기적 체크 (APScheduler가 없을 때)
# 성능 모니터링 미들웨어는 CORS 미들웨어 이후에 정의됨

@app.on_event("shutdown")
async def shutdown_event():
    global cache_scheduler
    if cache_scheduler:
        cache_scheduler.stop()
        print("🛑 캐시 스케줄러 중지됨")

# 테스트 엔드포인트
@app.get("/test")
async def test():
    return {"message": "Hello World", "status": "working"}





@app.get("/", response_class=HTMLResponse)
async def root():
    # 실시간 데이터베이스 통계
    stats = get_database_stats()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>StockVision API</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                min-height: 100vh;
                overflow-x: hidden;
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 40px 20px; 
            }}
            .header {{ 
                text-align: center; 
                margin-bottom: 50px; 
            }}
            .logo {{ 
                font-size: 4rem; 
                margin-bottom: 1rem; 
                text-shadow: 0 4px 8px rgba(0,0,0,0.3);
                animation: float 6s ease-in-out infinite;
            }}
            @keyframes float {{
                0%, 100% {{ transform: translateY(0px); }}
                50% {{ transform: translateY(-20px); }}
            }}
            .title {{ 
                font-size: 3.5rem; 
                margin-bottom: 1rem; 
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .subtitle {{ 
                font-size: 1.3rem; 
                margin-bottom: 3rem; 
                opacity: 0.9; 
                line-height: 1.6;
                max-width: 800px;
                margin-left: auto;
                margin-right: auto;
            }}
            .nav-links {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-bottom: 30px;
            }}
            .nav-link {{
                background: rgba(255,255,255,0.2);
                color: white;
                padding: 12px 24px;
                border-radius: 25px;
                text-decoration: none;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.3);
                backdrop-filter: blur(10px);
            }}
            .nav-link:hover {{
                background: rgba(255,255,255,0.3);
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .stats-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 25px; 
                margin-bottom: 50px; 
            }}
            .stat-card {{ 
                background: rgba(255,255,255,0.1); 
                padding: 30px; 
                border-radius: 20px; 
                backdrop-filter: blur(15px); 
                border: 1px solid rgba(255,255,255,0.2); 
                transition: all 0.3s ease;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                transition: left 0.5s;
            }}
            .stat-card:hover::before {{
                left: 100%;
            }}
            .stat-card:hover {{ 
                transform: translateY(-10px) scale(1.02); 
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }}
            .stat-icon {{ 
                font-size: 2.5rem; 
                margin-bottom: 1rem; 
                opacity: 0.8; 
            }}
            .stat-number {{ 
                font-size: 2.5rem; 
                font-weight: bold; 
                margin-bottom: 0.5rem; 
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .stat-label {{ 
                opacity: 0.8; 
                font-size: 1rem; 
                font-weight: 500;
            }}
            .docs-grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                gap: 25px; 
                margin-bottom: 50px; 
            }}
            .doc-card {{ 
                background: rgba(255,255,255,0.1); 
                padding: 30px; 
                border-radius: 20px; 
                backdrop-filter: blur(15px); 
                border: 1px solid rgba(255,255,255,0.2); 
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .doc-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                transition: left 0.5s;
            }}
            .doc-card:hover::before {{
                left: 100%;
            }}
            .doc-card:hover {{ 
                transform: translateY(-10px) scale(1.02); 
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            }}
            .doc-card h3 {{ 
                margin: 0 0 20px 0; 
                font-size: 1.4rem; 
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .doc-card p {{ 
                margin: 0 0 25px 0; 
                opacity: 0.8; 
                line-height: 1.6; 
                font-size: 0.95rem;
            }}
            .doc-link {{ 
                display: inline-block; 
                background: rgba(255,255,255,0.2); 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 12px; 
                transition: all 0.3s ease;
                font-weight: 500;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            .doc-link:hover {{ 
                background: rgba(255,255,255,0.3); 
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.2);
            }}
            .footer {{ 
                text-align: center; 
                opacity: 0.8; 
                padding: 30px 0;
                border-top: 1px solid rgba(255,255,255,0.1);
            }}
            .footer p {{ 
                margin: 10px 0;
                font-size: 0.95rem;
            }}
            .status-indicator {{
                display: inline-block;
                width: 12px;
                height: 12px;
                background: #4ade80;
                border-radius: 50%;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 40px 0;
            }}
            .feature-item {{
                background: rgba(255,255,255,0.05);
                padding: 20px;
                border-radius: 15px;
                text-align: center;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .feature-icon {{
                font-size: 2rem;
                margin-bottom: 15px;
                opacity: 0.8;
            }}
            .tech-stack {{
                background: rgba(255,255,255,0.05);
                padding: 25px;
                border-radius: 20px;
                margin: 30px 0;
                border: 1px solid rgba(255,255,255,0.1);
            }}
            .tech-stack h3 {{
                margin-bottom: 20px;
                text-align: center;
                font-size: 1.3rem;
            }}
            .tech-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
            }}
            .tech-item {{
                background: rgba(255,255,255,0.1);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                font-size: 0.9rem;
            }}
            @media (max-width: 768px) {{
                .title {{ font-size: 2.5rem; }}
                .subtitle {{ font-size: 1.1rem; }}
                .stats-grid {{ grid-template-columns: 1fr; }}
                .docs-grid {{ grid-template-columns: 1fr; }}
                .container {{ padding: 20px 15px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">🚀</div>
                <h1 class="title">StockVision API</h1>
                <p class="subtitle">
                    AI 기반 주식 동향 예측과 가상 거래로 스마트한 투자 결정을 내리세요.<br>
                    머신러닝 모델과 실시간 데이터 분석으로 투자 기회를 발견하고, 리스크 없는 가상 환경에서 전략을 검증하세요.
                </p>
                
                <!-- 네비게이션 링크 -->
                <div class="nav-links">
                    <a href="/api/v1/logs/" class="nav-link">
                        📊 로그 대시보드
                    </a>
                    <a href="/docs" class="nav-link">
                        📚 API 문서
                    </a>
                    <a href="/health" class="nav-link">
                        🏥 시스템 상태
                    </a>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-number">{stats['total_stocks']}</div>
                    <div class="stat-label">등록된 주식</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">📈</div>
                    <div class="stat-number">{stats['total_prices']}</div>
                    <div class="stat-label">가격 데이터</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🤖</div>
                    <div class="stat-number">{stats['total_indicators']}</div>
                    <div class="stat-label">기술적 지표</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">⚡</div>
                    <div class="stat-number">
                        <span class="status-indicator"></span>Active
                    </div>
                    <div class="stat-label">시스템 상태</div>
                </div>
            </div>

            <div class="tech-stack">
                <h3>🛠️ 기술 스택</h3>
                <div class="tech-grid">
                    <div class="tech-item">Python 3.13.7</div>
                    <div class="tech-item">FastAPI 0.116.1</div>
                    <div class="tech-item">SQLite</div>
                    <div class="tech-item">yfinance</div>
                    <div class="tech-item">scikit-learn</div>
                    <div class="tech-item">TensorFlow</div>
                </div>
            </div>

            <div class="feature-grid">
                <div class="feature-item">
                    <div class="feature-icon">📊</div>
                    <div>실시간 데이터 수집</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">🤖</div>
                    <div>AI 예측 모델</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">💼</div>
                    <div>가상 거래 시스템</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">📈</div>
                    <div>기술적 지표</div>
                </div>
            </div>
            
            <div class="docs-grid">
                <div class="doc-card">
                    <h3><i class="fas fa-book"></i> Swagger UI</h3>
                    <p>상세한 API 문서와 인터랙티브 테스트 환경. 개발자가 API를 테스트하고 디버깅하기에 최적화되어 있습니다.</p>
                    <a href="/docs" class="doc-link">문서 보기 <i class="fas fa-arrow-right"></i></a>
                </div>
                <div class="doc-card">
                    <h3><i class="fas fa-file-alt"></i> ReDoc</h3>
                    <p>깔끔하고 읽기 쉬운 API 문서. 사용자 친화적인 인터페이스로 API를 이해하기 쉽게 만들어줍니다.</p>
                    <a href="/redoc" class="doc-link">문서 보기 <i class="fas fa-arrow-right"></i></a>
                </div>
                <div class="doc-card">
                    <h3><i class="fas fa-bolt"></i> RapiDoc</h3>
                    <p>현대적이고 빠른 API 문서. Material Design 기반의 직관적인 UI로 최고의 사용자 경험을 제공합니다.</p>
                    <a href="/rapidoc" class="doc-link">문서 보기 <i class="fas fa-arrow-right"></i></a>
                </div>
                <div class="doc-card">
                    <h3><i class="fas fa-search"></i> API 탐색</h3>
                    <p>모든 API 엔드포인트를 직접 탐색하고 테스트할 수 있습니다. 실시간 데이터로 API 동작을 확인하세요.</p>
                    <a href="/api/v1/stocks/" class="doc-link">API 보기 <i class="fas fa-arrow-right"></i></a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>🚀 StockVision으로 스마트한 투자 결정을 내리세요!</strong></p>
                <p>Version 1.0.0 | Python 3.13.7 | FastAPI 0.116.1 | SQLite</p>
                <p>마지막 업데이트: {stats['last_updated']}</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/docs", response_class=HTMLResponse)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 2,
            "defaultModelExpandDepth": 2,
            "docExpansion": "list",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True,
            "requestInterceptor": "function(request) { console.log('API Request:', request); return request; }",
            "responseInterceptor": "function(response) { console.log('API Response:', response); return response; }",
        }
    )

@app.get("/redoc", response_class=HTMLResponse)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
        redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

@app.get("/rapidoc", response_class=HTMLResponse)
async def rapidoc_html():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>StockVision API - RapiDoc</title>
        <meta charset="utf-8">
        <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
        <style>
            body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        </style>
    </head>
    <body>
        <rapi-doc 
            spec-url="/openapi.json"
            theme="light"
            show-header="false"
            allow-authentication="true"
            allow-server-selection="true"
            allow-api-list-style-selection="true"
            nav-bg-color="#667eea"
            nav-text-color="#ffffff"
            nav-hover-bg-color="#764ba2"
            nav-hover-text-color="#ffffff"
            nav-accent-color="#ffffff"
            primary-color="#667eea"
            render-style="read"
            show-method-in-nav-bar="true"
            nav-item-spacing="relaxed"
            use-path-in-nav-bar="true"
            nav-bar-width="300px"
            response-area-height="400px"
            show-curl-before-try="true"
            layout="row"
            sort-tags="true"
            goto-path=""
            fill-request-fields-with-example="true"
            persist-auth="true"
            show-common-extensions="true"
            show-extensions="true"
            regular-font="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
            mono-font="'Consolas', 'Monaco', 'Courier New', monospace"
            font-size="14px"
            primary-color="#667eea"
            nav-bg-color="#667eea"
            nav-text-color="#ffffff"
            nav-hover-bg-color="#764ba2"
            nav-hover-text-color="#ffffff"
            nav-accent-color="#ffffff"
            nav-item-spacing="relaxed"
            nav-bar-width="300px"
            response-area-height="400px"
            show-curl-before-try="true"
            layout="row"
            sort-tags="true"
            goto-path=""
            fill-request-fields-with-example="true"
            persist-auth="true"
            show-common-extensions="true"
            show-extensions="true"
        >
        </rapi-doc>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    stats = get_database_stats()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "python_version": "3.13.7",
        "fastapi_version": "0.116.1",
        "database": "SQLite (개발)",
        "database_stats": stats,
        "features": [
            "주식 데이터 수집",
            "기술적 지표 계산", 
            "AI 예측 모델",
            "가상 거래 시스템"
        ],
        "uptime": "서버 실행 중",
        "environment": "development"
    }

@app.get("/api-info")
async def api_info():
    stats = get_database_stats()
    return {
        "title": app.title,
        "version": app.version,
        "description": "AI 기반 주식 동향 예측 및 가상 거래 시스템",
        "database_stats": stats,
        "endpoints": {
            "docs": "/docs - Swagger UI",
            "redoc": "/redoc - ReDoc", 
            "rapidoc": "/rapidoc - RapiDoc",
            "health": "/health - 서버 상태",
            "stocks": "/api/v1/stocks/ - 주식 데이터",
            "openapi": "/openapi.json - OpenAPI 스키마"
        },
        "tags": [
            "stocks - 주식 정보 및 데이터",
            "predictions - AI 예측 모델",
            "trading - 가상 거래 시스템"
        ],
        "features": {
            "real_time_data": "yfinance를 통한 실시간 주식 데이터",
            "technical_indicators": "RSI, MACD, EMA, 볼린저 밴드 등",
            "ai_prediction": "Random Forest, LSTM 기반 주가 예측",
            "virtual_trading": "리스크 없는 가상 거래 시스템"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
