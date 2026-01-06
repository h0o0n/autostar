"""
기술적 지표 계산 모듈
RSI, MACD, 볼린저 밴드, 이동평균선 등의 기술적 지표를 계산합니다.
"""
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
from typing import Dict, Optional

class TechnicalIndicators:
    """기술적 지표를 계산하는 클래스"""
    
    def __init__(self, df: pd.DataFrame):
        """
        초기화
        
        Args:
            df: OHLCV 데이터프레임 (columns: open, high, low, close, volume)
        """
        self.df = df.copy()
        if not df.empty:
            self.close = df['close']
            self.high = df['high']
            self.low = df['low']
            self.volume = df['volume']
    
    def calculate_rsi(self, period: int = 14) -> Optional[float]:
        """
        RSI(Relative Strength Index)를 계산합니다.
        RSI는 과매수/과매도 상태를 판단하는 지표입니다.
        
        Args:
            period: RSI 계산 기간 (기본값: 14)
            
        Returns:
            최신 RSI 값 (0-100)
        """
        if self.df.empty or len(self.df) < period:
            return None
        
        try:
            rsi_indicator = RSIIndicator(close=self.close, window=period)
            rsi = rsi_indicator.rsi()
            return rsi.iloc[-1] if not rsi.empty else None
        except Exception as e:
            print(f"RSI 계산 오류: {e}")
            return None
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """
        MACD(Moving Average Convergence Divergence)를 계산합니다.
        MACD는 추세의 방향과 강도를 나타내는 지표입니다.
        
        Args:
            fast: 빠른 이동평균 기간
            slow: 느린 이동평균 기간
            signal: 시그널 라인 기간
            
        Returns:
            MACD 정보 딕셔너리 (macd, signal, histogram)
        """
        if self.df.empty or len(self.df) < slow:
            return None
        
        try:
            macd_indicator = MACD(
                close=self.close,
                window_fast=fast,
                window_slow=slow,
                window_sign=signal
            )
            
            macd_line = macd_indicator.macd()
            signal_line = macd_indicator.macd_signal()
            histogram = macd_indicator.macd_diff()
            
            if macd_line.empty or signal_line.empty:
                return None
            
            return {
                'macd': macd_line.iloc[-1],
                'signal': signal_line.iloc[-1],
                'histogram': histogram.iloc[-1] if not histogram.empty else 0
            }
        except Exception as e:
            print(f"MACD 계산 오류: {e}")
            return None
    
    def calculate_bollinger_bands(self, period: int = 20, std: float = 2.0) -> Optional[Dict]:
        """
        볼린저 밴드를 계산합니다.
        볼린저 밴드는 변동성을 기반으로 과매수/과매도를 판단합니다.
        
        Args:
            period: 이동평균 기간
            std: 표준편차 배수
            
        Returns:
            볼린저 밴드 정보 딕셔너리 (upper, middle, lower, position)
        """
        if self.df.empty or len(self.df) < period:
            return None
        
        try:
            bb_indicator = BollingerBands(
                close=self.close,
                window=period,
                window_dev=std
            )
            
            bb_upper = bb_indicator.bollinger_hband()
            bb_middle = bb_indicator.bollinger_mavg()
            bb_lower = bb_indicator.bollinger_lband()
            
            if bb_upper.empty or bb_middle.empty or bb_lower.empty:
                return None
            
            current_price = self.close.iloc[-1]
            upper = bb_upper.iloc[-1]
            middle = bb_middle.iloc[-1]
            lower = bb_lower.iloc[-1]
            
            # 현재가의 볼린저 밴드 내 위치 (0-1, 0=하단, 1=상단)
            if upper != lower:
                position = (current_price - lower) / (upper - lower)
            else:
                position = 0.5
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'position': position
            }
        except Exception as e:
            print(f"볼린저 밴드 계산 오류: {e}")
            return None
    
    def calculate_moving_averages(self, short: int = 5, medium: int = 20, long: int = 60) -> Optional[Dict]:
        """
        이동평균선을 계산합니다.
        
        Args:
            short: 단기 이동평균 기간
            medium: 중기 이동평균 기간
            long: 장기 이동평균 기간
            
        Returns:
            이동평균선 정보 딕셔너리
        """
        if self.df.empty:
            return None
        
        try:
            ma_short = self.close.rolling(window=short).mean().iloc[-1] if len(self.df) >= short else None
            ma_medium = self.close.rolling(window=medium).mean().iloc[-1] if len(self.df) >= medium else None
            ma_long = self.close.rolling(window=long).mean().iloc[-1] if len(self.df) >= long else None
            current_price = self.close.iloc[-1]
            
            # 이동평균선 정렬 상태 확인
            alignment_score = 0
            if ma_short and ma_medium:
                if ma_short > ma_medium:
                    alignment_score += 0.5
                if ma_medium and ma_long and ma_medium > ma_long:
                    alignment_score += 0.5
            
            return {
                'ma_short': ma_short,
                'ma_medium': ma_medium,
                'ma_long': ma_long,
                'current_price': current_price,
                'alignment_score': alignment_score  # 상승 정렬 점수 (0-1)
            }
        except Exception as e:
            print(f"이동평균선 계산 오류: {e}")
            return None
    
    def calculate_volume_indicator(self) -> Optional[Dict]:
        """
        거래량 지표를 계산합니다.
        
        Returns:
            거래량 정보 딕셔너리
        """
        if self.df.empty or len(self.df) < 20:
            return None
        
        try:
            current_volume = self.volume.iloc[-1]
            avg_volume = self.volume.rolling(window=20).mean().iloc[-1]
            
            # 거래량 비율 (현재 거래량 / 평균 거래량)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            return {
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio
            }
        except Exception as e:
            print(f"거래량 지표 계산 오류: {e}")
            return None
    
    def calculate_all_indicators(self, config: dict) -> Dict:
        """
        모든 기술적 지표를 계산합니다.
        
        Args:
            config: 설정 딕셔너리 (config.py에서 가져온 설정)
            
        Returns:
            모든 지표를 포함한 딕셔너리
        """
        indicators = {}
        
        # RSI 계산
        indicators['rsi'] = self.calculate_rsi(period=config.get('RSI_PERIOD', 14))
        
        # MACD 계산
        indicators['macd'] = self.calculate_macd(
            fast=config.get('MACD_FAST', 12),
            slow=config.get('MACD_SLOW', 26),
            signal=config.get('MACD_SIGNAL', 9)
        )
        
        # 볼린저 밴드 계산
        indicators['bollinger'] = self.calculate_bollinger_bands(
            period=config.get('BB_PERIOD', 20),
            std=config.get('BB_STD', 2.0)
        )
        
        # 이동평균선 계산
        indicators['moving_averages'] = self.calculate_moving_averages(
            short=config.get('MA_SHORT', 5),
            medium=config.get('MA_MEDIUM', 20),
            long=config.get('MA_LONG', 60)
        )
        
        # 거래량 지표 계산
        indicators['volume'] = self.calculate_volume_indicator()
        
        return indicators

