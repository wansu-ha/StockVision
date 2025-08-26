import json
import time
import uuid
from typing import Dict, Any
from fastapi import Request, Response
from .logging_config import api_logger, combined_logger

class APILogger:
    """API 요청/응답 로깅 클래스"""
    
    def __init__(self):
        self.request_count = 0
        self.yahoo_api_calls = 0
    
    def log_request(self, request: Request, trace_id: str) -> Dict[str, Any]:
        """요청 로깅"""
        self.request_count += 1
        
        # IP 주소 추출
        client_ip = request.client.host if request.client else "unknown"
        
        # 쿼리 파라미터
        query_params = dict(request.query_params)
        
        # 요청 정보 로깅
        log_data = {
            "timestamp": time.time(),
            "level": "INFO",
            "service": "stock-api",
            "trace_id": trace_id,
            "request_count": self.request_count,
            "ip_address": client_ip,
            "request": {
                "method": request.method,
                "path": str(request.url.path),
                "query": query_params,
                "user_agent": request.headers.get("user-agent", ""),
                "content_length": request.headers.get("content-length", 0)
            }
        }
        
        # API 로그에 기록
        api_logger.info(f"API Request: {json.dumps(log_data, ensure_ascii=False)}")
        
        return log_data
    
    def log_response(self, request_data: Dict[str, Any], response: Response, 
                    process_time: float, status_code: int) -> None:
        """응답 로깅"""
        
        # 응답 정보 추가
        log_data = {
            **request_data,
            "response": {
                "status_code": status_code,
                "response_time": round(process_time, 3),
                "data_size": len(response.body) if hasattr(response, 'body') else 0
            }
        }
        
        # API 로그에 기록
        api_logger.info(f"API Response: {json.dumps(log_data, ensure_ascii=False)}")
        
        # 통합 로그에도 기록
        combined_logger.info(f"API: {request_data['request']['method']} {request_data['request']['path']} - {status_code} - {process_time:.3f}초")
    
    def log_error(self, request_data: Dict[str, Any], error: Exception, 
                  process_time: float) -> None:
        """오류 로깅"""
        
        log_data = {
            **request_data,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "response_time": round(process_time, 3)
            }
        }
        
        # API 로그에 오류 기록
        api_logger.error(f"API Error: {json.dumps(log_data, ensure_ascii=False)}")
        
        # 통합 로그에도 기록
        combined_logger.error(f"API Error: {request_data['request']['method']} {request_data['request']['path']} - {error}")
    
    def increment_yahoo_calls(self, symbol: str, data_type: str) -> None:
        """야후 파이낸스 API 호출 카운터 증가"""
        self.yahoo_api_calls += 1
        
        log_data = {
            "timestamp": time.time(),
            "level": "INFO",
            "service": "yahoo-finance",
            "call_count": self.yahoo_api_calls,
            "symbol": symbol,
            "data_type": data_type
        }
        
        # 야후 파이낸스 로그에 기록
        from .logging_config import yahoo_logger
        yahoo_logger.info(f"Yahoo API Call: {json.dumps(log_data, ensure_ascii=False)}")
        
        # 통합 로그에도 기록
        combined_logger.info(f"Yahoo API: {symbol} {data_type} - 호출 횟수: {self.yahoo_api_calls}")

# 전역 인스턴스
api_logger_instance = APILogger()
