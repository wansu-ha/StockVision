from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import stocks

app = FastAPI(
    title="StockVision API",
    description="AI 기반 주식 동향 예측 및 가상 거래 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(stocks.router)

@app.get("/")
async def root():
    return {"message": "StockVision API에 오신 것을 환영합니다!"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2025-01-27T00:00:00Z"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
