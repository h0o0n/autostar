"""
급등 가능성 분석 모듈
단기(몇 시간 내) 급등 가능성을 분석합니다.
피보나치 되돌림 분석을 포함합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from upbit_client import UpbitClient

class SurgeAnalyzer:
    """급등 가능성을 분석하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
        """
        self.client = upbit_client
    
    def analyze_volume_surge(self, df: pd.DataFrame, periods: list = [5, 15, 30, 60]) -> Dict:
        """
        거래량 급증 패턴을 분석합니다.
        최근 거래량이 평균 대비 얼마나 증가했는지 확인합니다.
        
        Args:
            df: OHLCV 데이터프레임
            periods: 분석할 기간 리스트 (분 단위)
            
        Returns:
            거래량 급증 분석 결과
        """
        if df.empty or len(df) < max(periods):
            return {'score': 0.0, 'details': {}}
        
        current_volume = df['volume'].iloc[-1]
        avg_volumes = {}
        surge_ratios = {}
        
        for period in periods:
            if len(df) >= period:
                avg_volume = df['volume'].iloc[-period:].mean()
                avg_volumes[period] = avg_volume
                if avg_volume > 0:
                    surge_ratios[period] = current_volume / avg_volume
                else:
                    surge_ratios[period] = 1.0
        
        # 가장 높은 급증 비율 사용
        max_surge = max(surge_ratios.values()) if surge_ratios else 1.0
        
        # 점수 계산 (2배 이상이면 높은 점수)
        if max_surge >= 5.0:
            volume_score = 1.0
        elif max_surge >= 3.0:
            volume_score = 0.8
        elif max_surge >= 2.0:
            volume_score = 0.6
        elif max_surge >= 1.5:
            volume_score = 0.4
        else:
            volume_score = max(0.0, (max_surge - 1.0) * 0.8)
        
        return {
            'score': volume_score,
            'current_volume': current_volume,
            'max_surge_ratio': max_surge,
            'surge_ratios': surge_ratios,
            'avg_volumes': avg_volumes
        }
    
    def analyze_price_momentum(self, df: pd.DataFrame) -> Dict:
        """
        가격 모멘텀을 분석합니다.
        최근 가격 상승 추세와 가속도를 확인합니다.
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            가격 모멘텀 분석 결과
        """
        if df.empty or len(df) < 10:
            return {'score': 0.0, 'details': {}}
        
        closes = df['close'].values
        current_price = closes[-1]
        
        # 최근 가격 변화율 (1분, 5분, 15분, 30분)
        momentum_scores = {}
        
        periods = [1, 5, 15, 30]
        for period in periods:
            if len(closes) > period:
                past_price = closes[-period-1]
                change_rate = (current_price - past_price) / past_price * 100
                momentum_scores[period] = change_rate
        
        # 가속도 계산 (변화율이 증가하는지)
        acceleration = 0.0
        if len(momentum_scores) >= 2:
            short_term = momentum_scores.get(1, 0)
            long_term = momentum_scores.get(30, 0)
            if long_term != 0:
                acceleration = short_term / abs(long_term) if abs(long_term) > 0.1 else 0
        
        # 모멘텀 점수 계산
        # 최근 변화율이 높고, 가속도가 양수면 높은 점수
        recent_momentum = momentum_scores.get(5, 0)
        
        if recent_momentum > 5.0 and acceleration > 1.2:
            momentum_score = 1.0
        elif recent_momentum > 3.0 and acceleration > 1.0:
            momentum_score = 0.8
        elif recent_momentum > 1.0:
            momentum_score = 0.6
        elif recent_momentum > 0:
            momentum_score = 0.4
        else:
            momentum_score = max(0.0, (recent_momentum + 5) / 10)  # -5% ~ +5%를 0~1로 매핑
        
        return {
            'score': momentum_score,
            'recent_momentum': recent_momentum,
            'acceleration': acceleration,
            'momentum_by_period': momentum_scores
        }
    
    def calculate_fibonacci_levels(self, high: float, low: float) -> Dict[float, float]:
        """
        피보나치 되돌림 레벨을 계산합니다.
        
        Args:
            high: 고점
            low: 저점
            
        Returns:
            피보나치 레벨 딕셔너리 {비율: 가격}
        """
        price_range = high - low
        
        # 피보나치 되돌림 레벨 (상승 후 하락 시)
        fib_levels = {
            0.0: low,           # 0% (저점)
            0.236: low + price_range * 0.236,  # 23.6%
            0.382: low + price_range * 0.382,  # 38.2%
            0.5: low + price_range * 0.5,       # 50%
            0.618: low + price_range * 0.618,   # 61.8% (황금비)
            0.786: low + price_range * 0.786,   # 78.6%
            1.0: high,          # 100% (고점)
            1.272: high + price_range * 0.272,  # 127.2% (확장)
            1.618: high + price_range * 0.618,  # 161.8% (황금비 확장)
        }
        
        return fib_levels
    
    def analyze_fibonacci_support(self, df: pd.DataFrame) -> Dict:
        """
        피보나치 되돌림 레벨에서의 지지/저항을 분석합니다.
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            피보나치 분석 결과
        """
        if df.empty or len(df) < 30:
            return {'score': 0.0, 'details': {}}
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        current_price = closes[-1]
        
        # 최근 고점과 저점 찾기 (최근 30개 캔들 기준)
        recent_high = highs[-30:].max()
        recent_low = lows[-30:].min()
        high_idx = np.where(highs[-30:] == recent_high)[0]
        low_idx = np.where(lows[-30:] == recent_low)[0]
        
        if len(high_idx) == 0 or len(low_idx) == 0:
            return {'score': 0.0, 'details': {}}
        
        high_pos = high_idx[-1] + len(df) - 30
        low_pos = low_idx[-1] + len(df) - 30
        
        # 추세 방향 판단 (고점과 저점의 위치)
        if high_pos > low_pos:
            # 상승 추세 후 하락 (되돌림)
            swing_high = recent_high
            swing_low = recent_low
            trend_direction = "상승_되돌림"
        else:
            # 하락 추세 후 상승 (반등)
            swing_high = recent_high
            swing_low = recent_low
            trend_direction = "하락_반등"
        
        # 피보나치 레벨 계산
        fib_levels = self.calculate_fibonacci_levels(swing_high, swing_low)
        
        # 현재가가 어느 피보나치 레벨 근처에 있는지 확인
        nearest_level = None
        nearest_ratio = None
        min_distance = float('inf')
        
        for ratio, level_price in fib_levels.items():
            distance = abs(current_price - level_price) / level_price
            if distance < min_distance:
                min_distance = distance
                nearest_level = level_price
                nearest_ratio = ratio
        
        # 피보나치 레벨 근처에서 지지/저항 확인
        support_score = 0.0
        breakout_score = 0.0
        
        # 중요한 피보나치 레벨 (38.2%, 50%, 61.8%)
        important_levels = [0.382, 0.5, 0.618]
        
        for ratio in important_levels:
            level_price = fib_levels[ratio]
            distance_pct = abs(current_price - level_price) / level_price * 100
            
            # 현재가가 피보나치 레벨 근처(1% 이내)에 있고, 상승 중이면 지지 신호
            if distance_pct < 1.0:
                if trend_direction == "상승_되돌림":
                    # 되돌림 후 지지선에서 반등
                    if ratio <= 0.618:  # 61.8% 이하에서 지지
                        support_score = max(support_score, 1.0 - ratio)  # 낮은 레벨일수록 강한 지지
                
                # 피보나치 레벨 돌파 확인
                if current_price > level_price * 1.01:  # 1% 이상 돌파
                    breakout_score = max(breakout_score, 0.8)
                elif current_price > level_price * 0.99:  # 레벨 근처
                    breakout_score = max(breakout_score, 0.5)
        
        # 61.8% (황금비) 레벨에서의 반등은 특히 강한 신호
        fib_618 = fib_levels[0.618]
        if abs(current_price - fib_618) / fib_618 < 0.01:  # 1% 이내
            if trend_direction == "상승_되돌림" and current_price >= fib_618:
                support_score = max(support_score, 0.9)
        
        # 피보나치 확장 레벨 돌파 (127.2%, 161.8%)
        fib_127 = fib_levels.get(1.272)
        fib_162 = fib_levels.get(1.618)
        
        if fib_127 and current_price > fib_127:
            breakout_score = max(breakout_score, 0.9)
        if fib_162 and current_price > fib_162:
            breakout_score = max(breakout_score, 1.0)
        
        # 종합 피보나치 점수
        fib_score = max(support_score, breakout_score)
        
        return {
            'score': fib_score,
            'nearest_level': nearest_level,
            'nearest_ratio': nearest_ratio,
            'support_score': support_score,
            'breakout_score': breakout_score,
            'trend_direction': trend_direction,
            'swing_high': swing_high,
            'swing_low': swing_low,
            'fib_levels': fib_levels
        }
    
    def analyze_breakout_pattern(self, df: pd.DataFrame) -> Dict:
        """
        브레이크아웃 패턴을 분석합니다.
        저항선 돌파, 삼각수렴 패턴 등을 감지합니다.
        
        Args:
            df: OHLCV 데이터프레임
            
        Returns:
            브레이크아웃 패턴 분석 결과
        """
        if df.empty or len(df) < 20:
            return {'score': 0.0, 'details': {}}
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        current_price = closes[-1]
        
        # 최근 고점/저점 분석
        recent_high = highs[-20:].max()
        recent_low = lows[-20:].min()
        price_range = recent_high - recent_low
        
        if price_range == 0:
            return {'score': 0.0, 'details': {}}
        
        # 현재가의 위치 (0-1, 1에 가까울수록 고점 근처)
        price_position = (current_price - recent_low) / price_range
        
        # 저항선 돌파 확인
        resistance_breakout = 0.0
        if current_price >= recent_high * 0.98:  # 최근 고점의 98% 이상
            resistance_breakout = 1.0
        elif current_price >= recent_high * 0.95:
            resistance_breakout = 0.7
        
        # 삼각수렴 패턴 (고점은 낮아지고 저점은 높아지는 패턴)
        triangle_pattern = 0.0
        if len(highs) >= 20:
            early_highs = highs[-20:-10]
            late_highs = highs[-10:]
            early_lows = lows[-20:-10]
            late_lows = lows[-10:]
            
            if (late_highs.mean() < early_highs.mean() and 
                late_lows.mean() > early_lows.mean()):
                # 삼각수렴 패턴 감지
                if price_position > 0.7:  # 상단 근처에서 돌파 준비
                    triangle_pattern = 0.8
        
        # 볼륨 증가와 함께 가격 상승
        volume_increase = 0.0
        if len(df) >= 10:
            recent_volume = df['volume'].iloc[-5:].mean()
            past_volume = df['volume'].iloc[-10:-5].mean()
            if past_volume > 0:
                volume_ratio = recent_volume / past_volume
                if volume_ratio > 1.5 and price_position > 0.6:
                    volume_increase = min(1.0, (volume_ratio - 1.5) * 0.5)
        
        # 종합 브레이크아웃 점수
        breakout_score = max(resistance_breakout, triangle_pattern, volume_increase)
        
        return {
            'score': breakout_score,
            'price_position': price_position,
            'resistance_breakout': resistance_breakout,
            'triangle_pattern': triangle_pattern,
            'volume_increase': volume_increase,
            'recent_high': recent_high,
            'recent_low': recent_low
        }
    
    def analyze_short_term_surge_potential(self, ticker: str) -> Dict:
        """
        종목의 단기 급등 가능성을 종합 분석합니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            급등 가능성 분석 결과
        """
        # 단기 데이터 가져오기 (1분봉, 최근 60개 = 1시간)
        df_1m = self.client.get_ohlcv(ticker, interval="minute1", count=60)
        if df_1m is None or df_1m.empty:
            return {'total_score': 0.0, 'components': {}}
        
        # 각 지표 분석
        volume_surge = self.analyze_volume_surge(df_1m, periods=[5, 15, 30, 60])
        price_momentum = self.analyze_price_momentum(df_1m)
        breakout = self.analyze_breakout_pattern(df_1m)
        
        # 피보나치 분석 (일봉 데이터 사용 - 더 정확한 스윙 포인트)
        df_daily = self.client.get_ohlcv(ticker, interval="day", count=60)
        fibonacci = {'score': 0.0, 'details': {}}
        if df_daily is not None and not df_daily.empty:
            fibonacci = self.analyze_fibonacci_support(df_daily)
        
        # 종합 점수 계산 (가중 평균)
        total_score = (
            volume_surge['score'] * 0.30 +  # 거래량 급증 30%
            price_momentum['score'] * 0.25 +  # 가격 모멘텀 25%
            breakout['score'] * 0.20 +  # 브레이크아웃 패턴 20%
            fibonacci['score'] * 0.25  # 피보나치 분석 25%
        )
        
        return {
            'total_score': total_score,
            'volume_surge': volume_surge,
            'price_momentum': price_momentum,
            'breakout': breakout,
            'fibonacci': fibonacci,
            'ticker': ticker,
            'current_price': df_1m['close'].iloc[-1] if not df_1m.empty else None
        }
    
    def get_surge_score(self, ticker: str) -> float:
        """
        종목의 급등 가능성 점수를 간단히 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            급등 가능성 점수 (0-1)
        """
        analysis = self.analyze_short_term_surge_potential(ticker)
        return analysis.get('total_score', 0.0)

