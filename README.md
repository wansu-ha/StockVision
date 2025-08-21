# StockVision 🚀

AI 기반 주식 동향 예측 및 가상 거래 시스템

## 📊 프로젝트 개요

StockVision은 머신러닝을 활용한 주식 동향 예측과 가상 거래 시스템을 제공합니다. 실제 투자 전에 전략을 검증할 수 있어 안전한 투자 결정을 도와줍니다.

## ✨ 주요 기능

- **📈 AI 기반 주식 예측**: LSTM, Random Forest, Ensemble 모델
- **💼 가상 거래 시스템**: 실제 투자 전 전략 검증
- **🤖 자동 거래 시스템**: 설정된 규칙에 따른 자동 매매
- **📊 백테스팅**: 과거 데이터로 전략 성과 분석
- **📱 현대적인 웹 인터페이스**: React + TypeScript

## 🏗️ 기술 스택

### Backend
- **Python 3.13.7** + FastAPI
- **데이터베이스**: SQLite (개발) → PostgreSQL (운영)
- **데이터 수집**: yfinance
- **기술적 지표**: pandas, numpy
- **ML 프레임워크**: scikit-learn, TensorFlow, Keras

### Frontend (예정)
- **React 18** + TypeScript
- **스타일링**: Tailwind CSS
- **차트**: Recharts
- **상태 관리**: Zustand

## 🚀 빠른 시작

```bash
# 백엔드 실행
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

## 📚 문서

- [프로젝트 청사진](docs/project-blueprint.md)
- [개발 계획](docs/integrated-development-plan.md)
- [아키텍처 설계](docs/architecture.md)
- [변경 로그](CHANGELOG.md)

## 📞 연락처

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요.

---

**개발 시작일**: 2025년 1월 27일  
**현재 단계**: 백엔드 완성, 프론트엔드 개발 준비 