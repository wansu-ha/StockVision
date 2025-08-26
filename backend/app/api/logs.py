from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

router = APIRouter()

# 로그 디렉토리
LOG_DIR = Path("logs")

@router.get("/", response_class=HTMLResponse)
async def logs_dashboard():
    """로그 대시보드 메인 페이지"""
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>StockVision 로그 대시보드</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; 
                min-height: 100vh;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto; 
                padding: 20px; 
            }
            .header { 
                text-align: center; 
                margin-bottom: 30px; 
            }
            .title { 
                font-size: 2.5rem; 
                margin-bottom: 1rem; 
            }
            .stats-container { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }
            .stat-card { 
                background: rgba(255,255,255,0.1); 
                padding: 20px; 
                border-radius: 10px; 
                text-align: center; 
                backdrop-filter: blur(10px); 
            }
            .stat-number { 
                font-size: 2rem; 
                font-weight: bold; 
                margin-bottom: 10px; 
            }
            .filters { 
                background: rgba(255,255,255,0.1); 
                padding: 20px; 
                border-radius: 10px; 
                margin-bottom: 20px; 
                backdrop-filter: blur(10px); 
            }
            .filter-group { 
                display: flex; 
                gap: 16px; 
                align-items: flex-start;
                flex-wrap: wrap; 
                width: 100%;
            }
            
            /* 모던한 입력 그룹 스타일 */
            .input-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
                min-width: 0;
                justify-content: flex-end;
            }
            
            .input-group label { 
                font-size: 12px;
                font-weight: 600;
                color: rgba(255,255,255,0.9);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin: 0;
                padding: 0;
            }
            
            .input-group select { 
                padding: 8px 10px; 
                border: 2px solid rgba(255,255,255,0.2); 
                border-radius: 6px; 
                background: rgba(255,255,255,0.95); 
                color: #333; 
                font-size: 14px;
                min-width: 120px;
                max-width: 140px;
                height: 36px !important;
                min-height: 36px !important;
                max-height: 36px !important;
                line-height: 20px;
                box-sizing: border-box;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .input-group select:focus {
                outline: none;
                border-color: rgba(255,255,255,0.5);
                background: rgba(255,255,255,1);
                box-shadow: 0 0 0 3px rgba(255,255,255,0.1);
            }
            
            .input-group input { 
                padding: 8px 10px; 
                border: 2px solid rgba(255,255,255,0.2); 
                border-radius: 6px; 
                background: rgba(255,255,255,0.95); 
                color: #333; 
                font-size: 14px;
                flex: 1 1 250px;
                min-width: 250px;
                max-width: 500px;
                height: 36px !important;
                min-height: 36px !important;
                max-height: 36px !important;
                line-height: 20px;
                box-sizing: border-box;
                transition: all 0.3s ease;
            }
            
            /* 날짜 입력창은 좁게 */
            .input-group input[type="date"] {
                flex: 0 1 140px;
                min-width: 140px;
                max-width: 160px;
            }
            
            /* 날짜 범위 그룹 스타일 */
            .date-range-group {
                display: flex;
                gap: 10px;
                align-items: flex-end;
            }
            
            .date-range-group .input-group {
                flex: 0 1 auto;
            }
            
            .date-range-group .input-group label {
                font-size: 12px;
            }
            
            .input-group input:focus {
                outline: none;
                border-color: rgba(255,255,255,0.5);
                background: rgba(255,255,255,1);
                box-shadow: 0 0 0 3px rgba(255,255,255,0.1);
            }
            
            /* 브라우저 기본 스타일 무시 */
            .input-group input[type="date"],
            .input-group input[type="text"] {
                -webkit-appearance: none;
                -moz-appearance: none;
                appearance: none;
                height: 36px !important;
                min-height: 36px !important;
                max-height: 36px !important;
                line-height: 20px;
                box-sizing: border-box;
            }
            
            .input-group select {
                -webkit-appearance: none;
                -moz-appearance: none;
                appearance: none;
                background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6,9 12,15 18,9'%3e%3c/polyline%3e%3c/svg%3e");
                background-repeat: no-repeat;
                background-position: right 8px center;
                background-size: 16px;
                padding-right: 32px;
            }
            .log-container { 
                background: rgba(255,255,255,0.1); 
                padding: 20px; 
                border-radius: 10px; 
                backdrop-filter: blur(10px); 
                width: 100%;
                box-sizing: border-box;
                margin: 0 auto;
                /* filters와 동일한 너비 */
                max-width: none;
            }
            
            /* 그리드 테이블 스타일 */
            .log-table {
                width: 100%;
                border-collapse: collapse;
                max-width: 100%;
                box-sizing: border-box;
                margin: 0 auto;
            }
            
            .log-header {
                display: grid;
                grid-template-columns: 120px 80px 120px 1fr 60px;
                gap: 15px;
                padding: 12px;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
                margin-bottom: 10px;
                font-weight: bold;
                color: rgba(255,255,255,0.9);
                font-size: 13px;
                width: 100%;
                box-sizing: border-box;
                max-width: 100%;
                margin: 0 auto;
                text-align: center;
            }
            
            /* 컬럼명 강제 가운데 정렬 */
            .log-header .log-col {
                text-align: center !important;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .log-col {
                text-align: center;
            }
            
            /* 시간 컬럼: 왼쪽 정렬 */
            .log-header > div:nth-child(1),
            .log-entry > div:nth-child(1) {
                text-align: left;
            }
            
            /* 요약 컬럼: 왼쪽 정렬 */
            .log-header > div:nth-child(4),
            .log-entry > div:nth-child(4) {
                text-align: left;
            }
            
            /* 나머지 컬럼: 가운데 정렬 */
            .log-header > div:nth-child(2),
            .log-header > div:nth-child(3),
            .log-header > div:nth-child(5),
            .log-entry > div:nth-child(2),
            .log-entry > div:nth-child(3),
            .log-entry > div:nth-child(5) {
                text-align: center;
            }
            
            /* 상태 이모지 컬럼: 가운데 정렬 강화 */
            .log-entry > div:nth-child(5) {
                display: flex;
                justify-content: center;
                align-items: center;
            }
            
            .log-entries {
                display: flex;
                flex-direction: column;
                gap: 4px;
                overflow: visible;
                width: 100%;
                box-sizing: border-box;
                max-width: 100%;
                margin: 0 auto;
            }
            
            .log-entry { 
                display: grid;
                grid-template-columns: 120px 80px 120px 1fr 60px;
                gap: 15px;
                padding: 8px 12px; 
                border-radius: 8px; 
                background: rgba(255,255,255,0.05); 
                font-family: 'Courier New', monospace; 
                font-size: 12px;
                align-items: center;
                cursor: pointer;
                transition: all 0.3s ease;
                border: 1px solid rgba(255,255,255,0.1);
                min-height: 40px;
                width: 100%;
                box-sizing: border-box;
                max-width: 100%;
                margin: 0 auto;
            }
            
            .log-entry:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.3);
            }
            
            .log-entry.expanded {
                background: rgba(255,255,255,0.15);
                border-color: rgba(255,255,255,0.5);
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                padding: 12px;
                min-height: 50px;
            }
            
            .log-entry:hover {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.3);
                transform: translateY(-1px);
            }
            
            .log-entry.expanded:hover {
                background: rgba(255,255,255,0.2);
                border-color: rgba(255,255,255,0.6);
            }
            
            .log-info { border-left: 4px solid #28a745; }
            .log-warning { border-left: 4px solid #ffc107; }
            .log-error { border-left: 4px solid #dc3545; }
            
            /* 아코디언 상세 정보 */
            .log-details {
                grid-column: 1 / -1;
                background: rgba(0,0,0,0.3);
                border-radius: 6px;
                padding: 0;
                margin-top: 0;
                font-size: 11px;
                line-height: 1.4;
                max-height: 0;
                overflow: hidden;
                transition: all 0.3s ease;
                opacity: 0;
                cursor: default;
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            .log-details.show {
                max-height: 500px;
                opacity: 1;
                margin-top: 8px;
                padding: 15px;
            }
            
            .log-details:hover {
                background: rgba(0,0,0,0.4);
                border-color: rgba(255,255,255,0.2);
            }
            
            .log-details-section {
                margin-bottom: 15px;
            }
            
            .log-details-section h4 {
                color: #ffc107;
                margin-bottom: 8px;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .log-details-row {
                display: flex;
                margin-bottom: 4px;
            }
            
            .log-details-label {
                color: rgba(255,255,255,0.7);
                min-width: 120px;
                font-weight: 500;
            }
            
            .log-details-value {
                color: rgba(255,255,255,0.9);
                flex: 1;
            }
            
            /* 버튼 및 배지 스타일 */
            .expand-btn {
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.3s ease;
            }
            
            .expand-btn:hover {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.5);
            }
            
            .log-level-badge {
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border: 1px solid;
                display: inline-block;
                min-width: 50px;
                text-align: center;
            }
            
            .log-level-badge.log-info {
                background: rgba(40, 167, 69, 0.2);
                color: #28a745;
                border-color: rgba(40, 167, 69, 0.5);
            }
            
            .log-level-badge.log-warning {
                background: rgba(255, 193, 7, 0.2);
                color: #ffc107;
                border-color: rgba(255, 193, 7, 0.5);
            }
            
            .log-level-badge.log-error {
                background: rgba(220, 53, 69, 0.2);
                color: #dc3545;
                border-color: rgba(220, 53, 69, 0.5);
            }
            
            .log-level-badge.log-debug {
                background: rgba(108, 117, 125, 0.2);
                color: #6c757d;
                border-color: rgba(108, 117, 125, 0.5);
            }
            
            .log-level-badge.log-critical {
                background: rgba(220, 53, 69, 0.3);
                color: #ffffff;
                border-color: #dc3545;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            .refresh-btn { 
                padding: 8px 16px; 
                background: #28a745; 
                border: none; 
                border-radius: 6px; 
                color: white; 
                cursor: pointer; 
                margin-left: 10px; 
                white-space: nowrap;
                flex-shrink: 0;
                min-width: fit-content;
                height: 36px !important;
                min-height: 36px !important;
                max-height: 36px !important;
                line-height: 20px;
                font-size: 14px;
                font-weight: 500;
            }
            .refresh-btn:hover { 
                background: #218838; 
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            
            /* 페이지네이션 컨트롤 스타일 */
            .pagination-controls {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: rgba(255,255,255,0.1);
                padding: 15px 20px;
                border-radius: 10px;
                margin: 20px 0;
                backdrop-filter: blur(10px);
                flex-wrap: wrap;
                gap: 15px;
            }
            
            .log-limit-control {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .log-limit-control label {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255,255,255,0.9);
                white-space: nowrap;
            }
            
            .log-limit-control select {
                padding: 6px 12px;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 6px;
                background: rgba(255,255,255,0.95);
                color: #333;
                font-size: 14px;
                cursor: pointer;
                height: 36px;
                min-width: 80px;
            }
            
            .pagination-info {
                display: flex;
                align-items: center;
                gap: 5px;
                text-align: left;
            }
            
            .pagination-info span {
                font-size: 14px;
                color: rgba(255,255,255,0.9);
                font-weight: 500;
            }
            
            #total-logs {
                font-size: 12px;
                color: rgba(255,255,255,0.7);
            }
            
            .pagination-buttons {
                display: flex;
                align-items: center;
                gap: 10px;
                justify-content: center;
                flex: 1;
            }
            
            .page-btn {
                padding: 8px 16px;
                background: rgba(255,255,255,0.2);
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 6px;
                color: white;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s ease;
                height: 36px;
                min-width: 80px;
            }
            
            .page-btn:hover:not(:disabled) {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.5);
            }
            
            .page-btn:disabled {
                background: rgba(255,255,255,0.1);
                border-color: rgba(255,255,255,0.2);
                color: rgba(255,255,255,0.5);
                cursor: not-allowed;
            }
            
            .page-numbers {
                display: flex;
                gap: 5px;
            }
            
            .page-number {
                padding: 6px 12px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 4px;
                color: white;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
                min-width: 40px;
                text-align: center;
            }
            
            .page-number:hover {
                background: rgba(255,255,255,0.2);
                border-color: rgba(255,255,255,0.5);
            }
            
            .page-number.active {
                background: rgba(255,255,255,0.3);
                border-color: rgba(255,255,255,0.6);
                font-weight: bold;
            }
            
            /* 로딩 스피너 */
            .loading-spinner {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                color: rgba(255,255,255,0.8);
            }
            
            .spinner {
                width: 40px;
                height: 40px;
                border: 4px solid rgba(255,255,255,0.3);
                border-top: 4px solid rgba(255,255,255,0.8);
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* 버튼 그룹 스타일 */
            .button-group {
                display: flex;
                gap: 8px;
                align-items: center;
                flex-shrink: 0;
                height: 36px;
            }
            
            /* 반응형 디자인 개선 */
            @media (max-width: 768px) {
                .filter-group {
                    flex-wrap: wrap;
                    gap: 12px;
                    width: 100%;
                }
                .input-group {
                    min-width: 0;
                }
                .input-group select {
                    min-width: 100px;
                    max-width: 120px;
                }
                .input-group input {
                    min-width: 200px;
                    max-width: none;
                    flex: 1 1 200px;
                }
                .button-group {
                    width: 100%;
                    justify-content: center;
                    margin-top: 0;
                    height: 36px;
                }
                .stats-container {
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                }
                .rate-limit-stats {
                    grid-template-columns: 1fr;
                    gap: 15px;
                }
            }
            
            @media (max-width: 480px) {
                .stats-container {
                    grid-template-columns: 1fr;
                }
                .container {
                    padding: 20px 15px;
                }
                .header h1 {
                    font-size: 1.8rem;
                }
                .filters {
                    padding: 15px;
                }
                .filter-group {
                    gap: 6px;
                    flex-wrap: wrap;
                    width: 100%;
                }
                .filter-group label {
                    font-size: 13px;
                    flex: 0 0 auto;
                }
                .input-group select {
                    min-width: 80px;
                    max-width: 90px;
                    padding: 6px 4px;
                    font-size: 13px;
                    height: 32px;
                }
                .input-group input {
                    min-width: 150px;
                    max-width: none;
                    padding: 6px 8px;
                    font-size: 13px;
                    width: 100%;
                    flex: 1 1 150px;
                    height: 32px;
                }
                .refresh-btn {
                    padding: 6px 12px;
                    font-size: 13px;
                    margin-left: 0;
                    height: 32px;
                }
            }
            
            /* 야후 파이낸스 제한 상태 스타일 */
            .rate-limit-container {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }
            .rate-limit-container h3 {
                margin-bottom: 15px;
                color: #ff6b6b;
            }
            .rate-limit-stats {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 15px;
            }
            .rate-limit-card {
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }
            .rate-limit-title {
                margin-bottom: 10px;
                font-weight: bold;
            }
            .rate-limit-bar {
                width: 100%;
                height: 20px;
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                overflow: hidden;
                margin-bottom: 10px;
            }
            .rate-limit-progress {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
                transition: width 0.3s ease;
                border-radius: 10px;
            }
            .rate-limit-text {
                font-size: 14px;
                font-weight: bold;
            }
            .rate-limit-status {
                text-align: center;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                background: rgba(40, 167, 69, 0.2);
            }
            .rate-limit-status.warning {
                background: rgba(255, 193, 7, 0.3);
                color: #ffc107;
            }
            .rate-limit-status.danger {
                background: rgba(220, 53, 69, 0.3);
                color: #dc3545;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="title">📊 StockVision 로그 대시보드</h1>
                <p>실시간 시스템 모니터링 및 로그 분석</p>
            </div>
            
            <!-- 실시간 통계 -->
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-number" id="total-count">0</div>
                    <div>전체 로그 수</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="yahoo-count">0</div>
                    <div>야후 API 호출</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="error-count">0</div>
                    <div>오류 발생</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-response">0ms</div>
                    <div>평균 응답시간</div>
                </div>
            </div>
            
            <!-- 야후 파이낸스 제한 상태 -->
            <div class="rate-limit-container">
                <h3>🚨 야후 파이낸스 API 제한 상태</h3>
                <div class="rate-limit-stats">
                    <div class="rate-limit-card" id="hourly-limit">
                        <div class="rate-limit-title">시간당 제한</div>
                        <div class="rate-limit-bar">
                            <div class="rate-limit-progress" id="hourly-progress"></div>
                        </div>
                        <div class="rate-limit-text" id="hourly-text">0 / 1000</div>
                    </div>
                    <div class="rate-limit-card" id="minute-limit">
                        <div class="rate-limit-title">분당 제한</div>
                        <div class="rate-limit-bar">
                            <div class="rate-limit-progress" id="minute-progress"></div>
                        </div>
                        <div class="rate-limit-text" id="minute-text">0 / 17</div>
                    </div>
                </div>
                <div class="rate-limit-status" id="rate-limit-status">상태: 정상</div>
            </div>
            
            <!-- 로그 필터 -->
            <div class="filters">
                <div class="filter-group">
                    <div class="input-group">
                        <label>로그 타입</label>
                        <select id="log-type">
                            <option value="all">전체</option>
                            <option value="api">API</option>
                            <option value="yahoo">야후 파이낸스</option>
                            <option value="combined">통합</option>
                        </select>
                    </div>
                    
                    <div class="input-group">
                        <label>로그 레벨</label>
                        <select id="log-level">
                            <option value="all">모든 레벨</option>
                            <option value="INFO">INFO</option>
                            <option value="WARNING">WARNING</option>
                            <option value="ERROR">ERROR</option>
                        </select>
                    </div>
                    
                    <div class="date-range-group">
                        <div class="input-group">
                            <label>시작일</label>
                            <input type="date" id="start-date" value="2025-08-26">
                        </div>
                        <div class="input-group">
                            <label>종료일</label>
                            <input type="date" id="end-date" value="2025-08-26">
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label>검색</label>
                        <input type="text" id="text-filter" placeholder="심볼, 메시지, 서비스 등 검색...">
                    </div>
                    
                    <div class="input-group">
                        <label>ㅤ</label>
                        <div class="button-group">
                            <button class="refresh-btn" onclick="refreshLogs()">새로고침</button>
                            <button class="refresh-btn" onclick="updateStats()">통계 업데이트</button>
                        </div>
                    </div>
                </div>
                
                <!-- 로그 개수 제한 및 페이지네이션 -->
                
            </div>
            
            <!-- 실시간 로그 -->
            <div class="log-container" id="log-container">
                <div class="log-table">
                                <div class="log-header">
                <div class="log-col" style="text-align: center;">시간</div>
                <div class="log-col" style="text-align: center;">레벨</div>
                <div class="log-col" style="text-align: center;">서비스</div>
                <div class="log-col" style="text-align: center;">요약</div>
                <div class="log-col" style="text-align: center;">상태</div>
            </div>
                    <div class="log-entries" id="log-entries">
                        <div class="log-entry log-info">로그를 불러오는 중...</div>
                    </div>
                    <div id="loading-spinner" class="loading-spinner" style="display: none;">
                        <div class="spinner"></div>
                        <div>로그를 불러오는 중...</div>
                    </div>
                </div>
            </div>
            
            <!-- 페이지네이션 -->
            <div class="pagination-controls">
                <div class="pagination-info">
                    <span id="total-logs">총 0개 로그</span>
                </div>
                <div class="pagination-buttons">
                    <div class="page-numbers" id="page-numbers"></div>
                </div>
                <div class="log-limit-control">
                    <label>로그 개수:</label>
                    <select id="log-limit" onchange="changeLogLimit()">
                        <option value="10">10개</option>
                        <option value="20" selected>20개</option>
                        <option value="50">50개</option>
                        <option value="100">100개</option>
                    </select>
                </div>
            </div>
        </div>
        
        <script>
            // 전역 변수 선언
            let currentType = 'all';
            let currentLevel = 'all';
            let currentStartDate = '';
            let currentEndDate = '';
            let textFilter = '';
            let currentPage = 1;
            let totalPages = 1;
            let totalLogs = 0;
            let logsPerPage = 20;
            let lastLogId = null;
            let isUserInteracting = false;
            
            // 실시간 통계 업데이트
            async function updateStats() {
                try {
                    console.log('updateStats 함수 시작');
                    const response = await fetch('/api/v1/logs/stats');
                    const stats = await response.json();
                    console.log('받은 통계 데이터:', stats);
                    
                    // stats.data 구조 확인
                    if (stats.success && stats.data) {
                        // 통계 카드 업데이트
                        const totalCountElement = document.getElementById('total-count');
                        const yahooCountElement = document.getElementById('yahoo-count');
                        const errorCountElement = document.getElementById('error-count');
                        const avgResponseElement = document.getElementById('avg-response');
                        
                        if (totalCountElement) {
                            totalCountElement.textContent = stats.data.today.total_logs || 0;
                        }
                        if (yahooCountElement) {
                            yahooCountElement.textContent = stats.data.today.yahoo_calls || 0;
                        }
                        if (errorCountElement) {
                            errorCountElement.textContent = stats.data.today.errors || 0;
                        }
                        if (avgResponseElement) {
                            const avgTime = stats.data.today.avg_response_time || 0;
                            avgResponseElement.textContent = Math.round(avgTime * 1000) + 'ms';
                        }
                        
                        // 야후 파이낸스 제한 상태 업데이트
                        if (stats.data.rate_limits) {
                            updateRateLimitStatus(stats.data.rate_limits);
                        }
                    } else {
                        console.error('통계 데이터 구조 오류:', stats);
                    }
                } catch (error) {
                    console.error('통계 업데이트 실패:', error);
                }
            }
            
            // 야후 파이낸스 제한 상태 업데이트
            function updateRateLimitStatus(rateLimits) {
                const hourlyUsage = rateLimits.hourly_usage || 0;
                const minuteUsage = rateLimits.minute_usage || 0;
                const status = rateLimits.status || 'normal';
                
                // 시간당 제한 업데이트
                const hourlyProgress = document.getElementById('hourly-progress');
                const hourlyText = document.getElementById('hourly-text');
                hourlyProgress.style.width = (hourlyUsage * 100) + '%';
                hourlyText.textContent = `${Math.round(hourlyUsage * 1000)} / 1000`;
                
                // 분당 제한 업데이트
                const minuteProgress = document.getElementById('minute-progress');
                const minuteText = document.getElementById('minute-text');
                minuteProgress.style.width = (minuteUsage * 100) + '%';
                minuteText.textContent = `${Math.round(minuteUsage * 17)} / 17`;
                
                // 상태 표시 업데이트
                const statusElement = document.getElementById('rate-limit-status');
                statusElement.className = 'rate-limit-status';
                
                if (status === 'warning') {
                    statusElement.textContent = '상태: ⚠️ 경고 (80% 이상 사용)';
                    statusElement.classList.add('warning');
                } else if (status === 'hourly_limit_exceeded' || status === 'minute_limit_exceeded') {
                    statusElement.textContent = '상태: 🚨 제한 초과';
                    statusElement.classList.add('danger');
                } else {
                    statusElement.textContent = '상태: ✅ 정상';
                }
                
                // 80% 이상일 때 빨간색으로 표시
                if (hourlyUsage >= 0.8 || minuteUsage >= 0.8) {
                    document.getElementById('hourly-limit').style.border = '2px solid #dc3545';
                    document.getElementById('minute-limit').style.border = '2px solid #dc3545';
                } else {
                    document.getElementById('hourly-limit').style.border = 'none';
                    document.getElementById('minute-limit').style.border = 'none';
                }
            }
            
            // 새로운 로그 확인 (항상 API 호출, 변경사항만 UI 업데이트)
            async function checkForNewLogs() {
                try {
                    const response = await fetch(`/api/v1/logs/entries?type=${currentType}&level=${currentLevel}&start_date=${currentStartDate || ''}&end_date=${currentEndDate || ''}&text=${textFilter || ''}&limit=10&page=1`);
                    const result = await response.json();
                    
                    if (result.success && result.data.length > 0) {
                        // 첫 번째 로그의 ID 확인
                        const firstLog = result.data[0];
                        const currentLogId = generateLogId(firstLog);
                        
                        // 새로운 로그가 있는지 확인
                        if (lastLogId !== currentLogId) {
                            // 새로운 로그만 추가
                            const newLogs = result.data.filter(log => {
                                const logId = generateLogId(log);
                                return logId !== lastLogId;
                            });
                            
                            if (newLogs.length > 0) {
                                console.log(`${newLogs.length}개의 새로운 로그 발견`);
                                
                                // 새 로그를 맨 위에 추가
                                newLogs.forEach(log => {
                                    addNewLogToTop(log);
                                });
                                
                                // 마지막 로그 ID 업데이트
                                lastLogId = currentLogId;
                                
                                // 통계 업데이트
                                updateStats();
                            } else {
                                console.log('새로운 로그 없음');
                            }
                        } else {
                            console.log('로그 변경사항 없음');
                        }
                    }
                } catch (error) {
                    console.log('로그 확인 실패:', error);
                }
            }
            
            // 로그 ID 생성 (고유 식별자)
            function generateLogId(log) {
                return `${log.timestamp}_${log.service}_${log.message.substring(0, 50)}`;
            }
            
            // 새 로그를 맨 위에 추가
            function addNewLogToTop(log) {
                const entriesContainer = document.getElementById('log-entries');
                if (!entriesContainer) return;
                
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                
                const summary = extractLogSummary(log.message);
                const status = getLogStatus(log.level);
                
                entry.innerHTML = `
                    <div>${formatTime(log.timestamp)}</div>
                    <div><span class="log-level-badge log-${log.level.toLowerCase()}">${log.level}</span></div>
                    <div>${log.service || 'Unknown'}</div>
                    <div>${summary}</div>
                    <div>${status}</div>
                `;
                
                // 클릭 이벤트 추가
                entry.addEventListener('click', function() {
                    toggleLogDetails(this);
                });
                
                // 상세 정보 생성
                const details = document.createElement('div');
                details.className = 'log-details';
                details.innerHTML = createLogDetails(log);
                details.addEventListener('click', function(e) {
                    e.stopPropagation();
                });
                
                entry.appendChild(details);
                
                // 맨 위에 추가
                entriesContainer.insertBefore(entry, entriesContainer.firstChild);
                
                // 로그 개수 제한 (최대 100개)
                const allEntries = entriesContainer.querySelectorAll('.log-entry');
                if (allEntries.length > 100) {
                    entriesContainer.removeChild(allEntries[allEntries.length - 1]);
                }
            }
            
            // 로그 새로고침
            async function refreshLogs() {
                const logType = document.getElementById('log-type').value;
                const logLevel = document.getElementById('log-level').value;
                const startDate = document.getElementById('start-date').value;
                const endDate = document.getElementById('end-date').value;
                const textFilter = document.getElementById('text-filter').value;
                
                console.log('refreshLogs 시작:', { logType, logLevel, startDate, endDate, textFilter });
                console.log('전역 변수 상태:', { lastLogId, currentPage, logsPerPage });
                console.log('전역 변수 상태:', { lastLogId, currentPage, logsPerPage });
                
                // 로딩 상태 표시
                const loadingSpinner = document.getElementById('loading-spinner');
                const logEntries = document.getElementById('log-entries');
                if (loadingSpinner) loadingSpinner.style.display = 'flex';
                if (logEntries) logEntries.style.display = 'none';
                
                try {
                    const response = await fetch(`/api/v1/logs/entries?type=${logType}&level=${logLevel}&start_date=${startDate}&end_date=${endDate}&text=${textFilter}&limit=${logsPerPage}&page=${currentPage}`);
                    const result = await response.json();
                    
                    console.log('API 응답:', result);
                    
                    // log-entries 요소 확인
                    const entriesContainer = document.getElementById('log-entries');
                    console.log('log-entries 요소:', entriesContainer);
                    
                    if (!entriesContainer) {
                        console.error('log-entries 요소를 찾을 수 없습니다. DOM 구조를 확인하세요.');
                        return;
                    }
                    
                    // result.data 구조 확인
                    if (result.success && result.data && Array.isArray(result.data)) {
                        // 초기 로그 ID 설정 (자동 업데이트용)
                        if (result.data.length > 0 && (typeof lastLogId === 'undefined' || !lastLogId)) {
                            const firstLog = result.data[0];
                            lastLogId = generateLogId(firstLog);
                            console.log('초기 로그 ID 설정:', lastLogId);
                        }
                        
                        // 페이지네이션 계산 - 백엔드에서 받은 총 로그 개수 사용
                        totalLogs = result.total_count || result.data.length;
                        totalPages = Math.ceil(totalLogs / logsPerPage);
                        
                        // 현재 페이지가 총 페이지 수를 초과하면 마지막 페이지로 조정
                        if (currentPage > totalPages) {
                            currentPage = totalPages || 1;
                        }
                        
                        // 백엔드에서 받은 로그를 직접 표시
                        entriesContainer.innerHTML = '';
                        
                        result.data.forEach(log => {
                            // 로그 요약 정보 추출
                            const summary = extractLogSummary(log.message);
                            const status = getLogStatus(log.level);
                            
                            // 로그 엔트리 생성
                            const entry = document.createElement('div');
                            entry.className = `log-entry log-${log.level.toLowerCase()}`;
                            
                            // 그리드 컬럼 내용
                            entry.innerHTML = `
                                <div>${formatTime(log.timestamp)}</div>
                                <div><span class="log-level-badge log-${log.level.toLowerCase()}">${log.level}</span></div>
                                <div>${log.service || 'Unknown'}</div>
                                <div>${summary}</div>
                                <div>${status}</div>
                            `;
                            
                            // 상세 정보 추가
                            const details = document.createElement('div');
                            details.className = 'log-details';
                            details.innerHTML = createLogDetails(log);
                            
                            // 상세 정보 영역 클릭 시 이벤트 전파 방지
                            details.addEventListener('click', function(e) {
                                e.stopPropagation();
                                console.log('상세 정보 영역 클릭됨 - 이벤트 전파 방지');
                            });
                            
                            entry.appendChild(details);
                            
                            // 클릭 이벤트 추가 (로그 행 전체 클릭)
                            entry.addEventListener('click', function(e) {
                                console.log('로그 엔트리 클릭됨:', this);
                                console.log('클릭된 요소:', e.target);
                                toggleLogDetails(this);
                            });
                            
                            entriesContainer.appendChild(entry);
                        });
                        
                        // 페이지네이션 UI 업데이트
                        updatePaginationUI();
                    } else {
                        console.error('로그 데이터 구조 오류:', result);
                        entriesContainer.innerHTML = '<div class="log-entry log-error">로그 데이터를 불러올 수 없습니다.</div>';
                        
                        // 페이지네이션 초기화
                        totalLogs = 0;
                        totalPages = 1;
                        currentPage = 1;
                        updatePaginationUI();
                    }
                    
                    // 로딩 상태 해제
                    if (loadingSpinner) loadingSpinner.style.display = 'none';
                    if (logEntries) logEntries.style.display = 'block';
                } catch (error) {
                    console.error('로그 새로고침 실패:', error);
                    
                    // 에러 발생 시에도 로딩 상태 해제
                    if (loadingSpinner) loadingSpinner.style.display = 'none';
                    if (logEntries) logEntries.style.display = 'block';
                }
            }
            
            // 로그 요약 정보 추출
            function extractLogSummary(message) {
                if (message.includes('API Request:')) {
                    try {
                        const messageData = JSON.parse(message.split(': ')[1]);
                        if (messageData.request) {
                            const method = messageData.request.method || '';
                            const path = messageData.request.path || '';
                            return `${method} ${path}`;
                        }
                    } catch (e) {
                        // JSON 파싱 실패 시 정규식으로 추출
                        const match = message.match(/"(method|path)":\s*"([^"]+)"/g);
                        if (match) {
                            const method = match.find(m => m.includes('method'))?.split('"')[3] || '';
                            const path = match.find(m => m.includes('path'))?.split('"')[3] || '';
                            return `${method} ${path}`;
                        }
                    }
                }
                if (message.includes('API Response:')) {
                    try {
                        const messageData = JSON.parse(message.split(': ')[1]);
                        if (messageData.response) {
                            const status = messageData.response.status_code || '';
                            const time = messageData.response.response_time || '';
                            return `응답 완료 (${status}) - ${time}s`;
                        }
                    } catch (e) {
                        return 'API 응답 완료';
                    }
                }
                if (message.includes('API Error:')) {
                    try {
                        const messageData = JSON.parse(message.split(': ')[1]);
                        if (messageData.error) {
                            const errorType = messageData.error.type || '';
                            return `오류: ${errorType}`;
                        }
                    } catch (e) {
                        return 'API 오류 발생';
                    }
                }
                if (message.includes('Yahoo API Call:')) {
                    try {
                        const messageData = JSON.parse(message.split(': ')[1]);
                        if (messageData.symbol && messageData.data_type) {
                            return `${messageData.symbol} ${messageData.data_type}`;
                        }
                    } catch (e) {
                        return '야후 API 호출';
                    }
                }
                if (message.includes('API:')) {
                    // 통합 로그 (간단한 요약)
                    const parts = message.split(' - ');
                    if (parts.length >= 2) {
                        return parts[0].replace('API: ', '');
                    }
                }
                return message.length > 50 ? message.substring(0, 50) + '...' : message;
            }
            
            // 로그 상태 아이콘
            function getLogStatus(level) {
                switch(level.toUpperCase()) {
                    case 'INFO': return '✅';
                    case 'WARNING': return '⚠️';
                    case 'ERROR': return '❌';
                    case 'DEBUG': return '🔍';
                    case 'CRITICAL': return '🚨';
                    default: return 'ℹ️';
                }
            }
            
            // 시간 포맷팅
            function formatTime(timestamp) {
                const date = new Date(timestamp);
                return date.toLocaleTimeString('ko-KR', { 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });
            }
            
            // 로그 상세 정보 생성
            function createLogDetails(log) {
                let details = '';
                
                // 기본 정보
                details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                details += '<h4>기본 정보</h4>';
                details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">시간:</span><span class="log-details-value">${formatTime(log.timestamp)}</span></div>`;
                details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">레벨:</span><span class="log-details-value"><span class="log-level-badge log-${log.level.toLowerCase()}">${log.level}</span></span></div>`;
                details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">서비스:</span><span class="log-details-value">${getServiceDisplayName(log.service)}</span></div>`;
                if (log.traceid) {
                    details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Trace ID:</span><span class="log-details-value">${log.traceid}</span></div>`;
                }
                if (log.log_type && log.log_type !== 'other') {
                    details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">타입:</span><span class="log-details-value">${log.log_type.toUpperCase()}</span></div>`;
                }
                details += '</div>';
                
                // 서비스별 상세 정보
                if (log.service === 'stock-api' || log.message.includes('API Request:') || log.message.includes('API Response:')) {
                    details += createAPIRequestDetails(log);
                } else if (log.service === 'yahoo-finance' || log.message.includes('Yahoo API Call:')) {
                    details += createYahooFinanceDetails(log);
                } else if (log.service === 'combined' || log.message.includes('API:')) {
                    details += createCombinedDetails(log);
                }
                
                // 메시지 정보
                details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                details += '<h4>메시지</h4>';
                details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">내용:</span><span class="log-details-value">${log.message}</span></div>`;
                details += '</div>';
                
                return details;
            }
            
            // API 요청 상세 정보
            function createAPIRequestDetails(log) {
                let details = '';
                
                try {
                    const messageData = JSON.parse(log.message.split(': ')[1]);
                    
                    details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                    details += '<h4>API 요청 정보</h4>';
                    
                    if (messageData.request) {
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Method:</span><span class="log-details-value">${messageData.request.method}</span></div>`;
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Path:</span><span class="log-details-value">${messageData.request.path}</span></div>`;
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">IP:</span><span class="log-details-value">${messageData.ip_address || 'Unknown'}</span></div>`;
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Trace ID:</span><span class="log-details-value">${messageData.trace_id || 'N/A'}</span></div>`;
                    }
                    
                    if (messageData.response) {
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Status:</span><span class="log-details-value">${messageData.response.status_code}</span></div>`;
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Response Time:</span><span class="log-details-value">${messageData.response.response_time}s</span></div>`;
                        details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">Data Size:</span><span class="log-details-value">${messageData.response.data_size} bytes</span></div>`;
                    }
                    
                    details += '</div>';
                } catch (e) {
                    details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                    details += '<h4>API 요청 정보</h4>';
                    details += '<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">상태:</span><span class="log-details-value">파싱 오류</span></div>';
                    details += '</div>';
                }
                
                return details;
            }
            
            // 야후 파이낸스 상세 정보
            function createYahooFinanceDetails(log) {
                let details = '';
                
                try {
                    const messageData = JSON.parse(log.message.split(': ')[1]);
                    
                    details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                    details += '<h4>야후 파이낸스 정보</h4>';
                    details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">심볼:</span><span class="log-details-value">${messageData.symbol || 'N/A'}</span></div>`;
                    details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">데이터 타입:</span><span class="log-details-value">${messageData.data_type || 'N/A'}</span></div>`;
                    details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">호출 횟수:</span><span class="log-details-value">${messageData.call_count || 'N/A'}</span></div>`;
                    details += '</div>';
                } catch (e) {
                    details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                    details += '<h4>야후 파이낸스 정보</h4>';
                    details += '<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">상태:</span><span class="log-details-value">파싱 오류</span></div>';
                    details += '</div>';
                }
                
                return details;
            }
            
            // 통합 로그 상세 정보
            function createCombinedDetails(log) {
                let details = '';
                
                details += '<div class="log-details-section" onclick="event.stopPropagation()">';
                details += '<h4>통합 정보</h4>';
                details += `<div class="log-details-row" onclick="event.stopPropagation()"><span class="log-details-label">요약:</span><span class="log-details-value">${log.message}</span></div>`;
                details += '</div>';
                
                return details;
            }
            
            // 서비스 표시 이름 변환
            function getServiceDisplayName(service) {
                const serviceNames = {
                    'stock-api': '📡 Stock API',
                    'yahoo-finance': '📈 Yahoo Finance',
                    'combined': '🔗 통합 로그',
                    'Unknown': '❓ 알 수 없음'
                };
                return serviceNames[service] || service || '❓ 알 수 없음';
            }
            
            // 로그 상세 정보 토글
            function toggleLogDetails(logEntry) {
                // logEntry가 이미 DOM 요소인지 확인
                if (!logEntry || !logEntry.classList) {
                    console.error('유효하지 않은 로그 엔트리:', logEntry);
                    return;
                }
                
                const details = logEntry.querySelector('.log-details');
                if (!details) {
                    console.error('log-details 요소를 찾을 수 없습니다:', logEntry);
                    return;
                }
                
                const isExpanded = details.classList.contains('show');
                
                if (isExpanded) {
                    details.classList.remove('show');
                    logEntry.classList.remove('expanded');
                    console.log('로그 상세 정보 접기');
                } else {
                    details.classList.add('show');
                    logEntry.classList.add('expanded');
                    console.log('로그 상세 정보 펼치기');
                }
            }
            
            // 페이지네이션 변수는 위에서 이미 선언됨
            
            // 로그 개수 제한 변경
            function changeLogLimit() {
                const limit = parseInt(document.getElementById('log-limit').value);
                logsPerPage = limit;
                currentPage = 1; // 첫 페이지로 이동
                refreshLogs();
            }
            
            // 페이지 이동
            function goToPage(pageNum) {
                if (typeof pageNum === 'number' && pageNum >= 1 && pageNum <= totalPages) {
                    currentPage = pageNum;
                    refreshLogs();
                    updatePaginationUI();
                }
            }
            
            // 페이지네이션 UI 업데이트
            function updatePaginationUI() {
                const pageNumbers = document.getElementById('page-numbers');
                const totalLogsElement = document.getElementById('total-logs');
                
                // 총 로그 수 업데이트
                totalLogsElement.textContent = `총 ${totalLogs}개 로그`;
                
                // 페이지 번호 버튼들
                pageNumbers.innerHTML = '';
                
                // 항상 1, 2 페이지 표시
                if (totalPages > 0) {
                    // 첫 번째 페이지
                    addPageButton(1);
                    
                    // 두 번째 페이지 (있는 경우)
                    if (totalPages > 1) {
                        addPageButton(2);
                    }
                    
                    // 현재 페이지 주변 표시
                    const startPage = Math.max(3, currentPage - 2);
                    const endPage = Math.min(totalPages - 2, currentPage + 2);
                    
                    // 첫 번째 구간과 현재 페이지 구간 사이에 "..." 표시
                    if (startPage > 3) {
                        addEllipsis();
                    }
                    
                    // 현재 페이지 주변 표시
                    for (let i = startPage; i <= endPage; i++) {
                        addPageButton(i);
                    }
                    
                    // 현재 페이지 구간과 마지막 구간 사이에 "..." 표시
                    if (endPage < totalPages - 2) {
                        addEllipsis();
                    }
                    
                    // 마지막 두 페이지 표시
                    if (totalPages > 2) {
                        if (totalPages - 1 > endPage) {
                            addPageButton(totalPages - 1);
                        }
                        addPageButton(totalPages);
                    }
                }
                
                // 페이지 버튼 추가 함수
                function addPageButton(pageNum) {
                    const pageBtn = document.createElement('div');
                    pageBtn.className = `page-number ${pageNum === currentPage ? 'active' : ''}`;
                    pageBtn.textContent = pageNum;
                    pageBtn.onclick = () => goToPage(pageNum);
                    pageNumbers.appendChild(pageBtn);
                }
                
                // "..." 표시 함수
                function addEllipsis() {
                    const ellipsis = document.createElement('div');
                    ellipsis.className = 'page-ellipsis';
                    ellipsis.textContent = '...';
                    pageNumbers.appendChild(ellipsis);
                }
            }
            
            // 페이지 로드 시 초기화
            document.addEventListener('DOMContentLoaded', function() {
                console.log('페이지 로드됨, 초기화 시작');
                
                // DOM 요소 확인
                const logContainer = document.getElementById('log-container');
                const logEntries = document.getElementById('log-entries');
                const logTable = document.querySelector('.log-table');
                
                console.log('DOM 요소 확인:', {
                    logContainer: !!logContainer,
                    logEntries: !!logEntries,
                    logTable: !!logTable
                });
                
                if (!logEntries) {
                    console.error('log-entries 요소가 없습니다. HTML 구조를 확인하세요.');
                    return;
                }
                
                // 잠시 대기 후 초기화 (DOM이 완전히 준비될 때까지)
                setTimeout(() => {
                    console.log('지연된 초기화 시작');
                    updateStats();
                    refreshLogs();
                }, 100);
                
                            // 초기 로그 ID는 refreshLogs에서 설정됨
            
            // 30초마다 통계 업데이트 (무한 루프 방지)
            setInterval(updateStats, 30000);
            
            // 실시간 로그 업데이트 (10초마다, 사용자 상호작용 중에는 중단)
            // lastLogId와 isUserInteracting은 위에서 이미 선언됨
            
            // 사용자 상호작용 감지
            document.addEventListener('mousedown', () => { isUserInteracting = true; });
            document.addEventListener('keydown', () => { isUserInteracting = true; });
            document.addEventListener('scroll', () => { isUserInteracting = true; });
            
            // 상호작용 종료 후 3초 뒤 업데이트 재개
            document.addEventListener('mouseup', () => {
                setTimeout(() => { isUserInteracting = false; }, 3000);
            });
            document.addEventListener('keyup', () => {
                setTimeout(() => { isUserInteracting = false; }, 3000);
            });
            
            // 스마트 업데이트: 주기적으로 새로운 로그 확인
            setInterval(() => {
                console.log('자동 업데이트 체크 중...', new Date().toLocaleTimeString());
                if (!isUserInteracting) {
                    console.log('사용자 상호작용 없음 - 로그 확인 시작');
                    checkForNewLogs();
                } else {
                    console.log('사용자 상호작용 중 - 업데이트 건너뜀');
                }
            }, 10000);
            });
            
            // 추가 안전장치: window.onload 이벤트도 사용
            window.addEventListener('load', function() {
                console.log('window.load 이벤트 발생');
                
                const logEntries = document.getElementById('log-entries');
                if (logEntries && !logEntries.hasChildNodes()) {
                    console.log('window.load에서 로그 새로고침 실행');
                    refreshLogs();
                }
            });
        </script>
    </body>
</html>
    """
    
    return HTMLResponse(content=html_content)

@router.get("/stats")
async def get_log_stats():
    """로그 통계 정보"""
    
    try:
        # 야후 파이낸스 제한 상태 가져오기
        from app.core.rate_limit_monitor import rate_limit_monitor
        rate_limit_status = rate_limit_monitor.get_usage_summary()
        
        # 간단한 통계 계산 (실제로는 더 정교한 계산 필요)
        stats = {
            "today": {
                "total_logs": 0,
                "api_requests": 0,
                "yahoo_calls": 0,
                "errors": 0,
                "avg_response_time": 0.0
            },
            "rate_limits": {
                "hourly_usage": rate_limit_status["hourly_usage"],
                "minute_usage": rate_limit_status["minute_usage"],
                "hourly_warning": rate_limit_status["hourly_warning"],
                "minute_warning": rate_limit_status["minute_warning"],
                "status": rate_limit_status["status"],
                "can_request": rate_limit_status["can_request"]
            }
        }
        
        # 오늘 날짜의 로그 파일들 확인
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 모든 로그 파일에서 전체 로그 수 계산
        total_logs = 0
        
        # API 로그 파일 확인
        api_log_file = LOG_DIR / "api" / "api.log"
        if api_log_file.exists():
            with open(api_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                api_count = len([line for line in lines if today in line])
                stats["today"]["api_requests"] = api_count
                total_logs += api_count
        
        # 야후 파이낸스 로그 파일 확인
        yahoo_log_file = LOG_DIR / "yahoo_finance" / "yahoo.log"
        if yahoo_log_file.exists():
            with open(yahoo_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                yahoo_count = len([line for line in lines if today in line])
                stats["today"]["yahoo_calls"] = yahoo_count
                total_logs += yahoo_count
        
        # 통합 로그 파일 확인
        combined_log_file = LOG_DIR / "combined" / "combined.log"
        if combined_log_file.exists():
            with open(combined_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                combined_count = len([line for line in lines if today in line])
                total_logs += combined_count
        
        # 전체 로그 수 저장
        stats["today"]["total_logs"] = total_logs
        
        return {"success": True, "data": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.get("/entries")
async def get_log_entries(
    type: str = Query("all", description="로그 타입"),
    level: str = Query("all", description="로그 레벨"),
    date: str = Query(None, description="로그 날짜"),
    text: str = Query(None, description="전체 텍스트 검색"),
    limit: int = Query(100, description="최대 로그 개수"),
    page: int = Query(1, description="페이지 번호")
):
    """로그 엔트리 조회"""
    
    try:
        logs = []
        
        # 로그 파일 경로 결정
        if type == "api":
            log_file = LOG_DIR / "api" / "api.log"
        elif type == "yahoo":
            log_file = LOG_DIR / "yahoo_finance" / "yahoo.log"
        elif type == "combined":
            log_file = LOG_DIR / "combined" / "combined.log"
        else:
            # 모든 로그 파일에서 조회
            log_files = [
                LOG_DIR / "api" / "api.log",
                LOG_DIR / "yahoo_finance" / "yahoo.log",
                LOG_DIR / "combined" / "combined.log"
            ]
        
        # log_files 변수 초기화 확인
        if 'log_files' not in locals():
            log_files = [log_file]
        
        # 로그 파일들에서 데이터 읽기
        all_logs = []  # 모든 로그를 먼저 수집
        
        for log_file in log_files:
            if not log_file.exists():
                continue
                
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # 로그 파싱 (간단한 형태)
                    try:
                        parts = line.strip().split(' | ')
                        if len(parts) >= 4:
                            timestamp = parts[0]
                            log_level = parts[1]
                            service = parts[2]
                            message = ' | '.join(parts[3:])
                            
                            # 필터링
                            if level != "all" and log_level != level:
                                continue
                                
                            if date and date not in timestamp:
                                continue
                                
                            if text and text.lower() not in message.lower():
                                continue
                            
                            # traceid 추출
                            traceid = None
                            if "trace_id" in message:
                                try:
                                    # JSON 형태의 traceid 추출
                                    import re
                                    trace_match = re.search(r'"trace_id":\s*"([^"]+)"', message)
                                    if trace_match:
                                        traceid = trace_match.group(1)
                                except:
                                    pass
                            
                            # 로그 타입 판별 (Request/Response)
                            log_type = "other"
                            if "API Request:" in message:
                                log_type = "request"
                            elif "API Response:" in message:
                                log_type = "response"
                            
                            all_logs.append({
                                "timestamp": timestamp,
                                "level": log_level,
                                "service": service,
                                "message": message,
                                "traceid": traceid,
                                "log_type": log_type
                            })
                    except:
                        continue
        
        # 로그 정렬: 단순 시간순 정렬
        def sort_logs(logs):
            # 시간순으로 정렬 (최신이 위로)
            return sorted(logs, key=lambda x: x['timestamp'], reverse=True)
        
        # 로그 정렬 적용
        all_logs = sort_logs(all_logs)
        
        # 총 로그 개수 (페이지네이션용)
        total_count = len(all_logs)
        
        # 페이지네이션 계산
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        # limit 파라미터에 따라 로그 제한
        if limit and limit > 0:
            logs = all_logs[start_index:end_index]
        else:
            logs = all_logs
        
        return {"success": True, "data": logs, "count": len(logs), "total_count": total_count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")

@router.get("/stream")
async def stream_logs():
    """실시간 로그 스트리밍 (Server-Sent Events)"""
    
    async def event_generator():
        while True:
            # 새로운 로그가 있을 때마다 전송
            # 실제 구현에서는 로그 파일 변경 감지 필요
            yield f"data: {json.dumps({'timestamp': datetime.now().isoformat(), 'message': '로그 스트리밍 테스트'})}\n\n"
            await asyncio.sleep(5)
    
    return StreamingResponse(event_generator(), media_type="text/plain")
