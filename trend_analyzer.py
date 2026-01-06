"""
추세 분석 모듈
비트코인과 알트코인의 추세를 분석하고 상관관계를 계산합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from upbit_client import UpbitClient

class TrendAnalyzer:
    """추세를 분석하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
        """
        self.client = upbit_client
    
    def analyze_btc_trend(self) -> Optional[Dict]:
        """
        비트코인의 추세를 분석합니다.
        
        Returns:
            비트코인 추세 정보 딕셔너리
        """
        try:
            # 비트코인 OHLCV 데이터 가져오기
            btc_df = self.client.get_ohlcv("KRW-BTC", interval="day", count=60)
            if btc_df is None or btc_df.empty:
                print("비트코인 데이터를 가져올 수 없습니다. 네트워크 연결을 확인해주세요.")
                return None
            
            # 단기 이동평균 (5일, 20일)
            ma5 = btc_df['close'].rolling(window=5).mean().iloc[-1]
            ma20 = btc_df['close'].rolling(window=20).mean().iloc[-1]
            current_price = btc_df['close'].iloc[-1]
            
            # 추세 방향 판단 (더 정확한 분석)
            ma60 = btc_df['close'].rolling(window=60).mean().iloc[-1] if len(btc_df) >= 60 else ma20
            
            # 다중 이동평균선으로 추세 판단
            is_uptrend = (ma5 > ma20 > ma60) and (current_price > ma5)
            is_downtrend = (ma5 < ma20 < ma60) and (current_price < ma5)
            
            if is_uptrend:
                trend_direction = "상승"
                # 상승 추세 강도 계산
                trend_strength = min((ma5 - ma20) / ma20 * 100, 15) / 15  # 0-1 정규화
            elif is_downtrend:
                trend_direction = "하락"
                # 하락 추세 강도 계산
                trend_strength = min((ma20 - ma5) / ma20 * 100, 15) / 15
            else:
                # 횡보 또는 불명확
                if ma5 > ma20:
                    trend_direction = "상승"
                    trend_strength = min((ma5 - ma20) / ma20 * 100, 10) / 10 * 0.5  # 약한 상승
                else:
                    trend_direction = "하락"
                    trend_strength = min((ma20 - ma5) / ma20 * 100, 10) / 10 * 0.5  # 약한 하락
            
            # 가격 변화율 (1일, 7일, 30일)
            price_change_1d = (current_price - btc_df['close'].iloc[-2]) / btc_df['close'].iloc[-2] * 100 if len(btc_df) >= 2 else 0
            price_change_7d = (current_price - btc_df['close'].iloc[-8]) / btc_df['close'].iloc[-8] * 100 if len(btc_df) >= 8 else 0
            price_change_30d = (current_price - btc_df['close'].iloc[-31]) / btc_df['close'].iloc[-31] * 100 if len(btc_df) >= 31 else 0
            
            # 추세 신호 강도 (상승/하락 명확도)
            trend_signal = "강한_상승" if (is_uptrend and trend_strength > 0.7) else \
                          "상승" if (trend_direction == "상승") else \
                          "강한_하락" if (is_downtrend and trend_strength > 0.7) else \
                          "하락"
            
            return {
                'current_price': current_price,
                'ma5': ma5,
                'ma20': ma20,
                'ma60': ma60 if len(btc_df) >= 60 else None,
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,  # 0-1 값
                'trend_signal': trend_signal,  # 추세 신호 강도
                'is_uptrend': is_uptrend,
                'is_downtrend': is_downtrend,
                'price_change_1d': price_change_1d,
                'price_change_7d': price_change_7d,
                'price_change_30d': price_change_30d
            }
        except Exception as e:
            print(f"비트코인 추세 분석 오류: {e}")
            print("네트워크 연결 문제이거나 업비트 API 서버에 접근할 수 없습니다.")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_correlation_with_btc(self, ticker: str, period: int = 30) -> Optional[float]:
        """
        알트코인과 비트코인의 상관관계를 계산합니다.
        
        Args:
            ticker: 알트코인 티커
            period: 분석 기간 (일)
            
        Returns:
            상관계수 (-1 ~ 1)
        """
        try:
            # 비트코인 데이터
            btc_df = self.client.get_ohlcv("KRW-BTC", interval="day", count=period)
            if btc_df is None or btc_df.empty:
                return None
            
            # 알트코인 데이터
            alt_df = self.client.get_ohlcv(ticker, interval="day", count=period)
            if alt_df is None or alt_df.empty:
                return None
            
            # 데이터 길이 맞추기
            min_len = min(len(btc_df), len(alt_df))
            if min_len < 10:
                return None
            
            btc_returns = btc_df['close'].pct_change().dropna()[-min_len:]
            alt_returns = alt_df['close'].pct_change().dropna()[-min_len:]
            
            # 길이 다시 맞추기
            min_len = min(len(btc_returns), len(alt_returns))
            if min_len < 10:
                return None
            
            btc_returns = btc_returns[-min_len:]
            alt_returns = alt_returns[-min_len:]
            
            # 상관계수 계산
            correlation = np.corrcoef(btc_returns, alt_returns)[0, 1]
            return correlation if not np.isnan(correlation) else None
        except Exception as e:
            print(f"{ticker} 비트코인 상관관계 계산 오류: {e}")
            return None
    
    def calculate_relative_strength(self, ticker: str, btc_trend: Dict) -> Optional[float]:
        """
        알트코인의 비트코인 대비 상대 강도를 계산합니다.
        
        Args:
            ticker: 알트코인 티커
            btc_trend: 비트코인 추세 정보
            
        Returns:
            상대 강도 점수 (0-1, 높을수록 비트코인보다 강함)
        """
        try:
            alt_df = self.client.get_ohlcv(ticker, interval="day", count=30)
            if alt_df is None or alt_df.empty:
                return None
            
            # 알트코인 가격 변화율
            alt_current = alt_df['close'].iloc[-1]
            alt_7d_ago = alt_df['close'].iloc[-8] if len(alt_df) >= 8 else alt_df['close'].iloc[0]
            alt_change_7d = (alt_current - alt_7d_ago) / alt_7d_ago * 100
            
            # 비트코인 가격 변화율
            btc_change_7d = btc_trend.get('price_change_7d', 0)
            
            # 상대 강도 계산
            if btc_change_7d == 0:
                relative_strength = 0.5
            else:
                # 알트코인이 비트코인보다 더 많이 상승하면 높은 점수
                strength_diff = alt_change_7d - btc_change_7d
                # -20% ~ +20% 범위를 0-1로 정규화
                relative_strength = max(0, min(1, (strength_diff + 20) / 40))
            
            return relative_strength
        except Exception as e:
            print(f"{ticker} 상대 강도 계산 오류: {e}")
            return None

