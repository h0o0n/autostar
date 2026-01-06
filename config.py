"""
설정 파일
업비트 API 키 및 프로그램 설정을 관리합니다.
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 업비트 API 키 (선택사항 - 공개 API만 사용시 불필요)
UPBIT_ACCESS_KEY = os.getenv('UPBIT_ACCESS_KEY', '')
UPBIT_SECRET_KEY = os.getenv('UPBIT_SECRET_KEY', '')

# 모니터링 설정
UPDATE_INTERVAL = 60  # 초 단위 (60초 = 1분마다 업데이트) - REST API 사용시
USE_WEBSOCKET = True  # WebSocket 사용 여부 (True: 실시간, False: REST API 주기적 조회)
MIN_VOLUME_24H = 1000000000  # 최소 24시간 거래대금 (1억원)

# WebSocket 설정
WS_URL = "wss://api.upbit.com/websocket/v1"  # 업비트 WebSocket URL
WS_PING_INTERVAL = 30  # WebSocket ping 간격 (초)
WS_PING_TIMEOUT = 10  # WebSocket ping 타임아웃 (초)
WS_RECONNECT_DELAY = 5  # 재연결 대기 시간 (초)
WS_MAX_RECONNECT_ATTEMPTS = 10  # 최대 재연결 시도 횟수

# 기술적 지표 설정
RSI_PERIOD = 14  # RSI 기간
RSI_OVERSOLD = 30  # RSI 과매도 기준
RSI_OVERBOUGHT = 70  # RSI 과매수 기준

MACD_FAST = 12  # MACD 빠른 이동평균
MACD_SLOW = 26  # MACD 느린 이동평균
MACD_SIGNAL = 9  # MACD 시그널

BB_PERIOD = 20  # 볼린저 밴드 기간
BB_STD = 2  # 볼린저 밴드 표준편차

MA_SHORT = 5  # 단기 이동평균선
MA_MEDIUM = 20  # 중기 이동평균선
MA_LONG = 60  # 장기 이동평균선

# 리스크 관리 설정
STOP_LOSS_PERCENT = 3.0  # 손절가 설정 비율 (%)
TAKE_PROFIT_PERCENT = 5.0  # 익절가 설정 비율 (%)
MAX_POSITION_SIZE = 0.1  # 최대 포지션 크기 (전체 자산의 10%)

# 고래 활동 분석 설정
WHALE_MIN_TRADE_AMOUNT = 50000000  # 고래 거래로 간주할 최소 거래금액 (5천만원)
WHALE_ANALYSIS_PERIOD = 300  # 고래 활동 분석 기간 (초, 5분)
WHALE_BUY_RATIO_THRESHOLD = 0.6  # 고래 매수 비율 임계값 (60% 이상이면 매수 신호)

# 추천 점수 가중치
WEIGHT_RSI = 0.12  # RSI 가중치
WEIGHT_MACD = 0.15  # MACD 가중치
WEIGHT_BB = 0.10  # 볼린저 밴드 가중치
WEIGHT_MA = 0.12  # 이동평균선 가중치
WEIGHT_VOLUME = 0.08  # 거래량 가중치
WEIGHT_BTC_CORRELATION = 0.08  # 비트코인 상관관계 가중치
WEIGHT_WHALE = 0.15  # 고래 활동 가중치
WEIGHT_SURGE = 0.20  # 급등 가능성 가중치 (새로 추가)

