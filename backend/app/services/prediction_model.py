import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from typing import Dict, List, Optional, Tuple
from app.models.stock import StockPrice, TechnicalIndicator
from app.core.database import SessionLocal
from datetime import datetime, timedelta
import logging
import joblib
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictionModel:
    def __init__(self):
        self.session = SessionLocal()
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = "models"
        
        # 모델 저장 디렉토리 생성
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
    
    def prepare_features(self, stock_id: int, days: int = 365) -> Tuple[pd.DataFrame, pd.Series]:
        """예측을 위한 특성 데이터 준비"""
        try:
            # 가격 데이터 조회
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            prices = self.session.query(StockPrice).filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= start_date
            ).order_by(StockPrice.date).all()
            
            if not prices:
                return pd.DataFrame(), pd.Series()
            
            # 가격 데이터를 DataFrame으로 변환
            price_data = []
            for price in prices:
                price_data.append({
                    'date': price.date,
                    'open': price.open,
                    'high': price.high,
                    'low': price.low,
                    'close': price.close,
                    'volume': price.volume
                })
            
            df = pd.DataFrame(price_data)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 기술적 지표 조회
            indicators = self.session.query(TechnicalIndicator).filter(
                TechnicalIndicator.stock_id == stock_id,
                TechnicalIndicator.date >= start_date
            ).order_by(TechnicalIndicator.date).all()
            
            # 지표 데이터를 DataFrame으로 변환
            indicator_data = {}
            for indicator in indicators:
                if indicator.indicator_type not in indicator_data:
                    indicator_data[indicator.indicator_type] = {}
                indicator_data[indicator.indicator_type][indicator.date] = indicator.value
            
            # 지표 DataFrame 생성
            for indicator_type, values in indicator_data.items():
                df[indicator_type] = pd.Series(values)
            
            # 특성 생성
            features = pd.DataFrame()
            
            # 가격 기반 특성
            features['price_change'] = df['close'].pct_change()
            features['high_low_ratio'] = df['high'] / df['low']
            features['volume_ma'] = df['volume'].rolling(window=5).mean()
            features['price_ma_5'] = df['close'].rolling(window=5).mean()
            features['price_ma_20'] = df['close'].rolling(window=20).mean()
            
            # 기술적 지표 특성
            if 'rsi' in df.columns:
                features['rsi'] = df['rsi']
            if 'ema_20' in df.columns:
                features['ema_20'] = df['ema_20']
            if 'ema_50' in df.columns:
                features['ema_50'] = df['ema_50']
            if 'macd' in df.columns:
                features['macd'] = df['macd']
            if 'signal' in df.columns:
                features['signal'] = df['signal']
            
            # 시계열 특성
            features['day_of_week'] = df.index.dayofweek
            features['month'] = df.index.month
            
            # NaN 값 처리
            features = features.ffill().fillna(0)
            
            # 타겟 변수 (다음 날 종가)
            target = df['close'].shift(-1)
            
            # 마지막 행 제거 (타겟이 없는 경우)
            features = features[:-1]
            target = target[:-1]
            
            return features, target
            
        except Exception as e:
            logger.error(f"특성 준비 실패 {stock_id}: {str(e)}")
            return pd.DataFrame(), pd.Series()
    
    def train_model(self, stock_id: int, days: int = 365) -> bool:
        """Random Forest 모델 훈련"""
        try:
            logger.info(f"모델 훈련 시작: {stock_id}")
            
            # 특성과 타겟 준비
            features, target = self.prepare_features(stock_id, days)
            
            if features.empty or target.empty:
                logger.warning(f"훈련 데이터 없음: {stock_id}")
                return False
            
            # 데이터 분할
            X_train, X_test, y_train, y_test = train_test_split(
                features, target, test_size=0.2, random_state=42
            )
            
            # 특성 스케일링
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # 모델 훈련
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            self.model.fit(X_train_scaled, y_train)
            
            # 예측 및 성능 평가
            y_pred = self.model.predict(X_test_scaled)
            
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            logger.info(f"모델 성능 - MSE: {mse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")
            
            # 모델 저장
            model_filename = f"{self.model_path}/stock_{stock_id}_model.pkl"
            scaler_filename = f"{self.model_path}/stock_{stock_id}_scaler.pkl"
            
            joblib.dump(self.model, model_filename)
            joblib.dump(self.scaler, scaler_filename)
            
            logger.info(f"모델 저장 완료: {stock_id}")
            return True
            
        except Exception as e:
            logger.error(f"모델 훈련 실패 {stock_id}: {str(e)}")
            return False
    
    def load_model(self, stock_id: int) -> bool:
        """저장된 모델 로드"""
        try:
            model_filename = f"{self.model_path}/stock_{stock_id}_model.pkl"
            scaler_filename = f"{self.model_path}/stock_{stock_id}_scaler.pkl"
            
            if not (os.path.exists(model_filename) and os.path.exists(scaler_filename)):
                logger.warning(f"저장된 모델 없음: {stock_id}")
                return False
            
            self.model = joblib.load(model_filename)
            self.scaler = joblib.load(scaler_filename)
            
            logger.info(f"모델 로드 완료: {stock_id}")
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패 {stock_id}: {str(e)}")
            return False
    
    def predict_next_day(self, stock_id: int) -> Optional[Dict]:
        """다음 날 주가 예측"""
        try:
            # 모델 로드
            if not self.load_model(stock_id):
                return None
            
            # 최신 특성 데이터 준비
            features, _ = self.prepare_features(stock_id, days=30)
            
            if features.empty:
                return None
            
            # 가장 최근 특성 사용
            latest_features = features.iloc[-1:].values
            
            # 특성 스케일링
            scaled_features = self.scaler.transform(latest_features)
            
            # 예측
            prediction = self.model.predict(scaled_features)[0]
            
            # 현재 가격 조회
            current_price = self.session.query(StockPrice).filter(
                StockPrice.stock_id == stock_id
            ).order_by(StockPrice.date.desc()).first()
            
            if not current_price:
                return None
            
            # 예측 결과
            result = {
                'predicted_price': float(prediction),
                'current_price': float(current_price.close),
                'price_change': float(prediction - current_price.close),
                'price_change_percent': float((prediction - current_price.close) / current_price.close * 100),
                'prediction_date': datetime.now().strftime('%Y-%m-%d'),
                'confidence': 0.7  # 기본 신뢰도
            }
            
            return result
            
        except Exception as e:
            logger.error(f"예측 실패 {stock_id}: {str(e)}")
            return None
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
