"""
업비트 WebSocket 클라이언트
업비트 WebSocket API를 사용하여 실시간 시세 데이터를 수신합니다.
업비트 개발자 센터 Best Practice를 참고하여 구현했습니다.
참고: https://docs.upbit.com/kr/docs/websocket-best-practice.md
"""
import json
import threading
import time
import config
from typing import Dict, List, Optional, Callable
from datetime import datetime
import websocket
from colorama import Fore, Style, init

# colorama 초기화
init(autoreset=True)

class UpbitWebSocketClient:
    """업비트 WebSocket 클라이언트 클래스"""
    
    def __init__(self, on_message_callback: Optional[Callable] = None):
        """
        초기화
        
        Args:
            on_message_callback: 메시지 수신 시 호출할 콜백 함수
                                함수 시그니처: callback(ticker: str, data: dict)
        """
        self.ws_url = config.WS_URL
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_count = 0
        self.subscribed_tickers: List[str] = []
        self.on_message_callback = on_message_callback
        self.price_data: Dict[str, Dict] = {}  # 티커별 최신 가격 데이터 저장
        
        # WebSocket 설정
        self.ping_interval = config.WS_PING_INTERVAL
        self.ping_timeout = config.WS_PING_TIMEOUT
        self.reconnect_delay = config.WS_RECONNECT_DELAY
        self.max_reconnect_attempts = config.WS_MAX_RECONNECT_ATTEMPTS
    
    def _on_message(self, ws, message):
        """
        WebSocket 메시지 수신 핸들러
        
        Args:
            ws: WebSocket 인스턴스
            message: 수신된 메시지 (bytes)
        """
        try:
            # 바이트를 문자열로 디코딩
            if isinstance(message, bytes):
                message = message.decode('utf-8')
            
            # JSON 파싱
            data = json.loads(message)
            
            # 티커 데이터 처리 (ticker 타입)
            if isinstance(data, dict):
                code = data.get('code')
                if code:
                    # 타입 확인
                    stream_type = data.get('type') or 'ticker'  # 기본값은 ticker
                    
                    if stream_type == 'ticker':
                        # 가격 데이터 저장
                        self.price_data[code] = {
                            'ticker': code,
                            'trade_price': data.get('trade_price'),  # 현재가
                            'trade_volume': data.get('trade_volume'),  # 거래량
                            'acc_trade_price_24h': data.get('acc_trade_price_24h'),  # 24시간 누적 거래대금
                            'high_price': data.get('high_price'),  # 고가
                            'low_price': data.get('low_price'),  # 저가
                            'prev_closing_price': data.get('prev_closing_price'),  # 전일 종가
                            'signed_change_rate': data.get('signed_change_rate'),  # 부호가 있는 변화율
                            'timestamp': datetime.now()
                        }
                        
                        # 콜백 함수 호출
                        if self.on_message_callback:
                            self.on_message_callback(code, self.price_data[code])
                    
                    elif stream_type == 'trade':
                        # 체결 데이터 처리
                        trade_data = {
                            'ticker': code,
                            'trade_price': data.get('trade_price'),  # 체결 가격
                            'trade_volume': data.get('trade_volume'),  # 체결 수량
                            'ask_bid': data.get('ask_bid'),  # 체결 종류 ('ASK': 매도, 'BID': 매수)
                            'sequential_id': data.get('sequential_id'),  # 체결 번호
                            'timestamp': datetime.now()
                        }
                        
                        # 체결 데이터 저장 (최근 100개만)
                        if code not in self.trade_data:
                            self.trade_data[code] = []
                        self.trade_data[code].append(trade_data)
                        if len(self.trade_data[code]) > 100:
                            self.trade_data[code].pop(0)
                        
                        # 체결 콜백 함수 호출
                        if self.on_trade_callback:
                            self.on_trade_callback(code, trade_data)
        
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}JSON 파싱 오류: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}메시지 처리 오류: {e}{Style.RESET_ALL}")
    
    def _on_error(self, ws, error):
        """
        WebSocket 에러 핸들러
        
        Args:
            ws: WebSocket 인스턴스
            error: 에러 객체
        """
        print(f"{Fore.RED}WebSocket 에러: {error}{Style.RESET_ALL}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket 연결 종료 핸들러
        
        Args:
            ws: WebSocket 인스턴스
            close_status_code: 종료 상태 코드
            close_msg: 종료 메시지
        """
        self.is_connected = False
        print(f"{Fore.YELLOW}WebSocket 연결이 종료되었습니다. (코드: {close_status_code}){Style.RESET_ALL}")
        
        # 재연결 시도
        if self.is_running and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            print(f"{Fore.YELLOW}{self.reconnect_delay}초 후 재연결을 시도합니다... (시도 {self.reconnect_count}/{self.max_reconnect_attempts}){Style.RESET_ALL}")
            time.sleep(self.reconnect_delay)
            self._connect()
        elif self.reconnect_count >= self.max_reconnect_attempts:
            print(f"{Fore.RED}최대 재연결 시도 횟수를 초과했습니다. 연결을 종료합니다.{Style.RESET_ALL}")
            self.is_running = False
    
    def _on_open(self, ws):
        """
        WebSocket 연결 시작 핸들러
        
        Args:
            ws: WebSocket 인스턴스
        """
        self.is_connected = True
        self.reconnect_count = 0  # 재연결 성공 시 카운터 리셋
        print(f"{Fore.GREEN}WebSocket 연결이 성공했습니다.{Style.RESET_ALL}")
        
        # 구독 메시지 전송
        if self.subscribed_tickers:
            self._subscribe_tickers(self.subscribed_tickers)
        if self.subscribed_trades:
            self._subscribe_trades(self.subscribed_trades)
    
    def _subscribe_tickers(self, tickers: List[str]):
        """
        티커 구독 메시지를 전송합니다.
        
        Args:
            tickers: 구독할 티커 리스트
        """
        if not self.is_connected or not self.ws:
            return
        
        # 업비트 WebSocket 구독 형식에 맞춰 메시지 구성
        # 참고: https://docs.upbit.com/kr/reference/websocket-ticker.md
        subscribe_message = [
            {"ticket": f"upbit_monitor_{int(time.time())}"},  # 고유 티켓 ID
            {
                "type": "ticker",  # 구독 타입 (ticker: 현재가)
                "codes": tickers  # 구독할 티커 리스트
            }
        ]
        
        try:
            self.ws.send(json.dumps(subscribe_message))
            print(f"{Fore.GREEN}{len(tickers)}개 종목 구독 완료: {', '.join(tickers)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}구독 메시지 전송 오류: {e}{Style.RESET_ALL}")
    
    def _connect(self):
        """WebSocket 연결을 생성합니다."""
        try:
            # WebSocketApp 생성
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # WebSocket 실행 (forever 모드)
            # ping_interval: 연결 유지를 위한 ping 전송 간격
            # ping_timeout: ping 응답 대기 시간
            # reconnect: 자동 재연결 시도 횟수 (0이면 자동 재연결 안함, 우리는 수동으로 처리)
            self.ws.run_forever(
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                reconnect=0  # 수동 재연결 처리
            )
        except Exception as e:
            print(f"{Fore.RED}WebSocket 연결 오류: {e}{Style.RESET_ALL}")
            self.is_connected = False
    
    def subscribe(self, tickers: List[str], subscribe_trades: bool = False):
        """
        티커를 구독합니다.
        
        Args:
            tickers: 구독할 티커 리스트 (예: ['KRW-BTC', 'KRW-ETH'])
            subscribe_trades: 체결 데이터도 구독할지 여부
        """
        # 중복 제거
        new_tickers = list(set(tickers))
        self.subscribed_tickers = new_tickers
        
        if subscribe_trades:
            self.subscribed_trades = new_tickers
        
        # 이미 연결되어 있으면 즉시 구독
        if self.is_connected and self.ws:
            self._subscribe_tickers(new_tickers)
            if subscribe_trades:
                self._subscribe_trades(new_tickers)
    
    def set_trade_callback(self, callback: Callable):
        """
        체결 데이터 콜백 함수를 설정합니다.
        
        Args:
            callback: 체결 데이터 수신 시 호출할 함수
                     함수 시그니처: callback(ticker: str, trade_data: dict)
        """
        self.on_trade_callback = callback
    
    def _subscribe_trades(self, tickers: List[str]):
        """
        체결 데이터를 구독합니다.
        
        Args:
            tickers: 구독할 티커 리스트
        """
        if not self.is_connected or not self.ws:
            return
        
        # 업비트 WebSocket 체결 구독 형식
        # 참고: https://docs.upbit.com/kr/reference/websocket-trade.md
        subscribe_message = [
            {"ticket": f"upbit_trade_{int(time.time())}"},
            {
                "type": "trade",  # 구독 타입 (trade: 체결)
                "codes": tickers
            }
        ]
        
        try:
            self.ws.send(json.dumps(subscribe_message))
            print(f"{Fore.GREEN}{len(tickers)}개 종목 체결 데이터 구독 완료{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}체결 구독 메시지 전송 오류: {e}{Style.RESET_ALL}")
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        티커의 현재가를 가져옵니다.
        WebSocket으로 수신한 최신 데이터를 반환합니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            현재가 (없으면 None)
        """
        if ticker in self.price_data:
            return self.price_data[ticker].get('trade_price')
        return None
    
    def get_price_data(self, ticker: str) -> Optional[Dict]:
        """
        티커의 전체 가격 데이터를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            가격 데이터 딕셔너리 (없으면 None)
        """
        return self.price_data.get(ticker)
    
    def start(self):
        """WebSocket 연결을 시작합니다."""
        if self.is_running:
            print(f"{Fore.YELLOW}WebSocket이 이미 실행 중입니다.{Style.RESET_ALL}")
            return
        
        self.is_running = True
        
        # 별도 스레드에서 WebSocket 실행
        ws_thread = threading.Thread(target=self._connect, daemon=True)
        ws_thread.start()
        
        # 연결 확인 대기
        max_wait = 10  # 최대 10초 대기
        wait_count = 0
        while not self.is_connected and wait_count < max_wait:
            time.sleep(0.5)
            wait_count += 0.5
        
        if not self.is_connected:
            print(f"{Fore.RED}WebSocket 연결에 실패했습니다.{Style.RESET_ALL}")
    
    def stop(self):
        """WebSocket 연결을 종료합니다."""
        self.is_running = False
        if self.ws:
            self.ws.close()
        self.is_connected = False
        print(f"{Fore.YELLOW}WebSocket 연결을 종료했습니다.{Style.RESET_ALL}")
    
    def is_alive(self) -> bool:
        """
        WebSocket 연결 상태를 확인합니다.
        
        Returns:
            연결 상태 (True: 연결됨, False: 연결 안됨)
        """
        return self.is_connected and self.is_running

