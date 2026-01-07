"""
고래 활동 분석 모듈
대형고래들의 매수/매도 활동을 감지하고 분석합니다.
"""
import config
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
from upbit_client import UpbitClient

class WhaleAnalyzer:
    """고래 활동을 분석하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
        """
        self.client = upbit_client
        self.min_trade_amount = config.WHALE_MIN_TRADE_AMOUNT
        self.analysis_period = config.WHALE_ANALYSIS_PERIOD
        self.buy_ratio_threshold = config.WHALE_BUY_RATIO_THRESHOLD
        
        # 티커별 고래 거래 데이터 저장 (최근 N초간의 거래)
        # 구조: {ticker: deque([{timestamp, trade_price, trade_volume, ask_bid}, ...])}
        self.whale_trades: Dict[str, deque] = {}
    
    def add_trade(self, ticker: str, trade_data: Dict):
        """
        체결 데이터를 추가합니다.
        
        Args:
            ticker: 티커 심볼
            trade_data: 체결 데이터 딕셔너리
                      - trade_price: 체결 가격
                      - trade_volume: 체결 수량
                      - ask_bid: 체결 종류 ('ASK': 매도, 'BID': 매수)
                      - timestamp: 체결 시각
        """
        if ticker not in self.whale_trades:
            self.whale_trades[ticker] = deque(maxlen=1000)  # 최대 1000개 거래 저장
        
        trade_price = trade_data.get('trade_price', 0)
        trade_volume = trade_data.get('trade_volume', 0)
        trade_amount = trade_price * trade_volume  # 거래금액
        
        # 고래 거래만 저장 (최소 거래금액 이상)
        if trade_amount >= self.min_trade_amount:
            self.whale_trades[ticker].append({
                'timestamp': datetime.now(),
                'trade_price': trade_price,
                'trade_volume': trade_volume,
                'trade_amount': trade_amount,
                'ask_bid': trade_data.get('ask_bid', 'UNKNOWN')  # 'ASK': 매도, 'BID': 매수
            })
    
    def analyze_whale_activity(self, ticker: str) -> Optional[Dict]:
        """
        티커의 고래 활동을 분석합니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            고래 활동 분석 결과 딕셔너리
            - buy_ratio: 매수 비율 (0-1)
            - sell_ratio: 매도 비율 (0-1)
            - total_trades: 총 고래 거래 건수
            - total_buy_amount: 총 매수 금액
            - total_sell_amount: 총 매도 금액
            - net_amount: 순 거래 금액 (매수 - 매도)
            - score: 고래 활동 점수 (0-1, 높을수록 매수 신호)
        """
        if ticker not in self.whale_trades or len(self.whale_trades[ticker]) == 0:
            return None
        
        # 최근 N초간의 거래만 분석
        cutoff_time = datetime.now() - timedelta(seconds=self.analysis_period)
        recent_trades = [
            trade for trade in self.whale_trades[ticker]
            if trade['timestamp'] >= cutoff_time
        ]
        
        if len(recent_trades) == 0:
            return None
        
        # 매수/매도 분류
        buy_trades = [t for t in recent_trades if t['ask_bid'] == 'BID']
        sell_trades = [t for t in recent_trades if t['ask_bid'] == 'ASK']
        
        # 총 거래 금액 계산
        total_buy_amount = sum(t['trade_amount'] for t in buy_trades)
        total_sell_amount = sum(t['trade_amount'] for t in sell_trades)
        total_amount = total_buy_amount + total_sell_amount
        
        if total_amount == 0:
            return None
        
        # 매수/매도 비율
        buy_ratio = total_buy_amount / total_amount
        sell_ratio = total_sell_amount / total_amount
        
        # 순 거래 금액 (매수 - 매도, 양수면 순매수)
        net_amount = total_buy_amount - total_sell_amount
        
        # 고래 활동 점수 계산 (0-1)
        # 매수 비율이 높을수록, 순매수 금액이 클수록 높은 점수
        if buy_ratio >= self.buy_ratio_threshold:
            # 매수 비율이 임계값 이상이면 높은 점수
            base_score = 0.7 + (buy_ratio - self.buy_ratio_threshold) * 0.6  # 0.7 ~ 1.0
        else:
            # 매수 비율이 낮으면 낮은 점수
            base_score = buy_ratio / self.buy_ratio_threshold * 0.7  # 0 ~ 0.7
        
        # 순매수 금액에 따라 점수 조정
        if net_amount > 0:
            # 순매수인 경우 점수 증가
            amount_bonus = min(net_amount / (self.min_trade_amount * 10), 0.2)  # 최대 0.2 보너스
            score = min(1.0, base_score + amount_bonus)
        else:
            # 순매도인 경우 점수 감소
            amount_penalty = min(abs(net_amount) / (self.min_trade_amount * 10), 0.3)  # 최대 0.3 페널티
            score = max(0.0, base_score - amount_penalty)
        
        return {
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'total_trades': len(recent_trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_buy_amount': total_buy_amount,
            'total_sell_amount': total_sell_amount,
            'net_amount': net_amount,
            'score': score
        }
    
    def get_whale_score(self, ticker: str) -> float:
        """
        티커의 고래 활동 점수를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            고래 활동 점수 (0-1, 없으면 0.5)
        """
        activity = self.analyze_whale_activity(ticker)
        if activity:
            return activity['score']
        return 0.5  # 데이터가 없으면 중립 점수

