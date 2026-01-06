"""
실시간 모니터링 시스템
추천 종목의 가격 변동을 실시간으로 모니터링하고 알림을 제공합니다.
WebSocket을 사용하여 실시간 데이터를 수신합니다.
"""
import time
import config
from datetime import datetime
from typing import List, Dict, Optional
from colorama import Fore, Style, init
from upbit_client import UpbitClient
from indicators import TechnicalIndicators
from risk_manager import RiskManager
from websocket_client import UpbitWebSocketClient
from whale_analyzer import WhaleAnalyzer

# colorama 초기화 (Windows에서 색상 지원)
init(autoreset=True)

class StockMonitor:
    """종목을 모니터링하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient, risk_manager: RiskManager, whale_analyzer: Optional[WhaleAnalyzer] = None):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
            risk_manager: RiskManager 인스턴스
            whale_analyzer: WhaleAnalyzer 인스턴스 (선택사항)
        """
        self.client = upbit_client
        self.risk_manager = risk_manager
        self.whale_analyzer = whale_analyzer
        self.monitored_stocks: List[Dict] = []
        self.update_interval = config.UPDATE_INTERVAL
        self.use_websocket = config.USE_WEBSOCKET
        
        # WebSocket 클라이언트 초기화
        self.ws_client: Optional[UpbitWebSocketClient] = None
        if self.use_websocket:
            self.ws_client = UpbitWebSocketClient(on_message_callback=self._on_websocket_message)
            # 체결 데이터 콜백 설정
            if self.whale_analyzer:
                self.ws_client.set_trade_callback(self._on_trade_message)
    
    def add_stock(self, stock_data: Dict):
        """
        모니터링할 종목을 추가합니다.
        
        Args:
            stock_data: 종목 정보 딕셔너리 (recommender에서 반환된 데이터)
        """
        ticker = stock_data.get('ticker')
        current_price = stock_data.get('current_price')
        
        if not ticker or not current_price:
            return
        
        # 리스크 파라미터 계산
        indicators = stock_data.get('indicators', {})
        risk_params = self.risk_manager.calculate_all_risk_parameters(
            current_price,
            indicators
        )
        
        # 모니터링 데이터 구성
        monitor_data = {
            'ticker': ticker,
            'entry_price': risk_params['entry_price'],
            'stop_loss_price': risk_params['stop_loss_price'],
            'take_profit_price': risk_params['take_profit_price'],
            'current_price': current_price,
            'last_price': current_price,
            'price_change_percent': 0.0,
            'status': '대기중',  # 대기중, 진입, 손절, 익절
            'added_at': datetime.now(),
            'last_update': datetime.now(),
            'risk_params': risk_params,
            'indicators': indicators
        }
        
        self.monitored_stocks.append(monitor_data)
    
    def _on_websocket_message(self, ticker: str, data: Dict):
        """
        WebSocket 메시지 수신 콜백 함수 (가격 데이터)
        
        Args:
            ticker: 티커 심볼
            data: 가격 데이터 딕셔너리
        """
        # 모니터링 중인 종목인지 확인
        stock = next((s for s in self.monitored_stocks if s['ticker'] == ticker), None)
        if not stock:
            return
        
        # 가격 업데이트
        current_price = data.get('trade_price')
        if current_price:
            last_price = stock['current_price']
            stock['last_price'] = last_price
            stock['current_price'] = current_price
            stock['price_change_percent'] = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0
            stock['last_update'] = datetime.now()
            
            # 상태 업데이트
            self._update_status(stock)
    
    def _on_trade_message(self, ticker: str, trade_data: Dict):
        """
        WebSocket 체결 데이터 수신 콜백 함수
        
        Args:
            ticker: 티커 심볼
            trade_data: 체결 데이터 딕셔너리
        """
        # 고래 분석기에 체결 데이터 전달
        if self.whale_analyzer:
            self.whale_analyzer.add_trade(ticker, trade_data)
    
    def update_prices(self):
        """모니터링 중인 모든 종목의 가격을 업데이트합니다. (REST API 사용시)"""
        if self.use_websocket:
            # WebSocket 사용시 이 함수는 호출되지 않음
            return
        
        for stock in self.monitored_stocks:
            try:
                ticker = stock['ticker']
                current_price = self.client.get_current_price(ticker)
                
                if current_price:
                    last_price = stock['current_price']
                    stock['last_price'] = last_price
                    stock['current_price'] = current_price
                    stock['price_change_percent'] = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0
                    stock['last_update'] = datetime.now()
                    
                    # 상태 업데이트
                    self._update_status(stock)
            except Exception as e:
                print(f"{Fore.RED}{ticker} 가격 업데이트 오류: {e}{Style.RESET_ALL}")
    
    def _update_status(self, stock: Dict):
        """
        종목의 상태를 업데이트합니다.
        
        Args:
            stock: 종목 정보 딕셔너리
        """
        current_price = stock['current_price']
        entry_price = stock['entry_price']
        stop_loss = stock['stop_loss_price']
        take_profit = stock['take_profit_price']
        
        # 손절가 도달
        if current_price <= stop_loss:
            if stock['status'] != '손절':
                stock['status'] = '손절'
                self._print_alert(stock, "손절가 도달!")
        
        # 익절가 도달
        elif current_price >= take_profit:
            if stock['status'] != '익절':
                stock['status'] = '익절'
                self._print_alert(stock, "익절가 도달!")
        
        # 진입가 도달
        elif current_price <= entry_price * 1.01:  # 진입가의 1% 이내
            if stock['status'] == '대기중':
                stock['status'] = '진입'
                self._print_alert(stock, "진입가 근처 도달!")
    
    def _print_alert(self, stock: Dict, message: str):
        """
        알림을 출력합니다.
        
        Args:
            stock: 종목 정보 딕셔너리
            message: 알림 메시지
        """
        ticker = stock['ticker']
        current_price = stock['current_price']
        status = stock['status']
        
        color = Fore.GREEN if status == '익절' else (Fore.RED if status == '손절' else Fore.YELLOW)
        
        print(f"\n{color}{'='*60}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
        print(f"종목: {ticker}")
        print(f"현재가: {current_price:,.0f}원")
        print(f"상태: {status}")
        print(f"{'='*60}{Style.RESET_ALL}\n")
    
    def display_status(self):
        """모니터링 중인 종목들의 상태를 출력합니다."""
        if not self.monitored_stocks:
            print("모니터링 중인 종목이 없습니다.")
            return
        
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"모니터링 종목 현황 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print(f"{'='*100}{Style.RESET_ALL}\n")
        
        print(f"{'종목':<15} {'현재가':>12} {'진입가':>12} {'손절가':>12} {'익절가':>12} {'변동률':>8} {'상태':>8}")
        print("-" * 100)
        
        for stock in self.monitored_stocks:
            ticker = stock['ticker']
            current_price = stock['current_price']
            entry_price = stock['entry_price']
            stop_loss = stock['stop_loss_price']
            take_profit = stock['take_profit_price']
            change = stock['price_change_percent']
            status = stock['status']
            
            # 색상 설정
            if status == '익절':
                color = Fore.GREEN
            elif status == '손절':
                color = Fore.RED
            elif status == '진입':
                color = Fore.YELLOW
            else:
                color = Fore.WHITE
            
            change_str = f"{change:+.2f}%"
            if change > 0:
                change_color = Fore.GREEN
            elif change < 0:
                change_color = Fore.RED
            else:
                change_color = Fore.WHITE
            
            print(f"{color}{ticker:<15} {current_price:>12,.0f} {entry_price:>12,.0f} {stop_loss:>12,.0f} {take_profit:>12,.0f} {change_color}{change_str:>8}{Style.RESET_ALL} {color}{status:>8}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*100}{Style.RESET_ALL}\n")
    
    def start_monitoring(self):
        """실시간 모니터링을 시작합니다."""
        if not self.monitored_stocks:
            print("모니터링할 종목이 없습니다.")
            return
        
        print(f"\n{Fore.GREEN}실시간 모니터링을 시작합니다...{Style.RESET_ALL}")
        
        # WebSocket 사용 여부에 따라 다른 방식으로 모니터링
        if self.use_websocket and self.ws_client:
            print(f"{Fore.CYAN}WebSocket을 사용하여 실시간 데이터를 수신합니다.{Style.RESET_ALL}\n")
            
            # 구독할 티커 리스트
            tickers = [stock['ticker'] for stock in self.monitored_stocks]
            
            # WebSocket 시작
            # 가격 데이터와 체결 데이터 모두 구독 (고래 분석 사용시)
            subscribe_trades = self.whale_analyzer is not None
            self.ws_client.subscribe(tickers, subscribe_trades=subscribe_trades)
            self.ws_client.start()
            
            # WebSocket이 연결될 때까지 대기
            time.sleep(2)
            
            try:
                # 주기적으로 상태 출력 (WebSocket은 백그라운드에서 가격 업데이트)
                while self.ws_client.is_alive():
                    # 상태 출력
                    self.display_status()
                    
                    # 대기 (WebSocket은 실시간으로 가격 업데이트)
                    time.sleep(self.update_interval)
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}모니터링을 종료합니다.{Style.RESET_ALL}")
            finally:
                # WebSocket 종료
                self.ws_client.stop()
        else:
            # REST API 사용 (기존 방식)
            print(f"{Fore.CYAN}REST API를 사용하여 {self.update_interval}초마다 데이터를 조회합니다.{Style.RESET_ALL}\n")
            
            try:
                while True:
                    # 가격 업데이트
                    self.update_prices()
                    
                    # 상태 출력
                    self.display_status()
                    
                    # 대기
                    time.sleep(self.update_interval)
                    
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}모니터링을 종료합니다.{Style.RESET_ALL}")
    
    def remove_stock(self, ticker: str):
        """
        모니터링에서 종목을 제거합니다.
        
        Args:
            ticker: 제거할 티커 심볼
        """
        self.monitored_stocks = [s for s in self.monitored_stocks if s['ticker'] != ticker]
        
        # WebSocket 사용시 구독 목록 업데이트
        if self.use_websocket and self.ws_client:
            tickers = [s['ticker'] for s in self.monitored_stocks]
            self.ws_client.subscribe(tickers)
        
        print(f"{ticker} 모니터링에서 제거되었습니다.")

