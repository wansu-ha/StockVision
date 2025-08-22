#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.services.prediction_model import PredictionModel
from app.models.stock import Stock

def test_prediction_model():
    print('예측 모델 테스트 시작...')
    
    # 첫 번째 주식으로 모델 훈련
    predictor = PredictionModel()
    stock_id = 1  # AAPL
    
    print(f'AAPL 주식 모델 훈련 시작...')
    success = predictor.train_model(stock_id, days=365)
    
    if success:
        print('모델 훈련 성공!')
        
        # 다음 날 예측
        print('다음 날 주가 예측...')
        prediction = predictor.predict_next_day(stock_id)
        
        if prediction:
            print('예측 결과:')
            print(f'현재 가격: ${prediction["current_price"]:.2f}')
            print(f'예측 가격: ${prediction["predicted_price"]:.2f}')
            print(f'변화량: ${prediction["price_change"]:.2f}')
            print(f'변화율: {prediction["price_change_percent"]:.2f}%')
        else:
            print('예측 실패')
    else:
        print('모델 훈련 실패')
    
    print('테스트 완료')

if __name__ == "__main__":
    test_prediction_model()
