"""
업비트 API 클라이언트
업비트 거래소의 시세 데이터를 가져오는 모듈입니다.
"""
import pyupbit
import pandas as pd
from typing import List, Dict, Optional
import time
import requests
from datetime import datetime, timedelta

class UpbitClient:
    """업비트 API를 사용하여 시세 데이터를 가져오는 클래스"""
    
    def __init__(self):
        """업비트 클라이언트 초기화"""
        self.client = pyupbit
    
    def get_ticker_list(self, market: str = "KRW") -> List[str]:
        """
        거래 가능한 티커 리스트를 가져옵니다.
        
        Args:
            market: 시장 타입 (KRW, BTC, USDT 등)
            
        Returns:
            티커 리스트 (예: ['KRW-BTC', 'KRW-ETH', ...])
        """
        try:
            tickers = pyupbit.get_tickers(fiat=market)
            return tickers
        except Exception as e:
            print(f"티커 리스트 조회 오류: {e}")
            return []
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        현재가를 가져옵니다.
        
        Args:
            ticker: 티커 심볼 (예: 'KRW-BTC')
            
        Returns:
            현재가 (원)
        """
        try:
            price = pyupbit.get_current_price(ticker)
            return price
        except Exception as e:
            print(f"{ticker} 현재가 조회 오류: {e}")
            return None
    
    def get_ohlcv(self, ticker: str, interval: str = "day", count: int = 200) -> Optional[pd.DataFrame]:
        """
        OHLCV(시가, 고가, 저가, 종가, 거래량) 데이터를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            interval: 시간 단위 ('day', 'minute1', 'minute3', 'minute5', 'minute15', 'minute30', 'minute60', 'minute240', 'week')
            count: 가져올 데이터 개수
            
        Returns:
            OHLCV 데이터프레임
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # pyupbit 사용 시도
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
                if df is not None and not df.empty:
                    # 컬럼명이 이미 올바른지 확인
                    if 'close' not in df.columns:
                        df.columns = ['open', 'high', 'low', 'close', 'volume']
                    return df
                
                # pyupbit이 실패하면 직접 API 호출
                if df is None:
                    df = self._get_ohlcv_direct(ticker, interval, count)
                    if df is not None and not df.empty:
                        return df
                
                # 재시도
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"{ticker} OHLCV 조회 결과가 None입니다. (시도 {attempt + 1}/{max_retries})")
                return df
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"{ticker} OHLCV 조회 오류: {e}")
                # 직접 API 호출 시도
                try:
                    return self._get_ohlcv_direct(ticker, interval, count)
                except:
                    return None
        return None
    
    def _get_ohlcv_direct(self, ticker: str, interval: str, count: int) -> Optional[pd.DataFrame]:
        """
        업비트 API를 직접 호출하여 OHLCV 데이터를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            interval: 시간 단위
            count: 가져올 데이터 개수
            
        Returns:
            OHLCV 데이터프레임
        """
        try:
            # 업비트 API 엔드포인트
            url = "https://api.upbit.com/v1/candles"
            
            # interval 매핑
            interval_map = {
                'minute1': 'minutes/1',
                'minute3': 'minutes/3',
                'minute5': 'minutes/5',
                'minute15': 'minutes/15',
                'minute30': 'minutes/30',
                'minute60': 'minutes/60',
                'minute240': 'minutes/240',
                'day': 'days',
                'week': 'weeks'
            }
            
            if interval not in interval_map:
                return None
            
            params = {
                'market': ticker,
                'count': count
            }
            
            full_url = f"{url}/{interval_map[interval]}"
            
            response = requests.get(full_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    return None
                
                # 데이터프레임 생성
                df = pd.DataFrame(data)
                
                # 컬럼명 변경 및 정렬
                df = df.rename(columns={
                    'opening_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'trade_price': 'close',
                    'candle_acc_trade_volume': 'volume'
                })
                
                # 시간순 정렬 (오래된 것부터)
                df = df.sort_values('candle_date_time_kst').reset_index(drop=True)
                
                # 필요한 컬럼만 선택
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
                # 데이터 타입 변환
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
            else:
                return None
        except Exception as e:
            print(f"직접 API 호출 오류 ({ticker}): {e}")
            return None
    
    def get_24h_ticker(self, ticker: str) -> Optional[Dict]:
        """
        24시간 티커 정보를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            
        Returns:
            24시간 티커 정보 딕셔너리
        """
        try:
            ticker_data = pyupbit.get_ticker(ticker)
            return ticker_data
        except Exception as e:
            print(f"{ticker} 24시간 티커 조회 오류: {e}")
            return None
    
    def get_market_info(self) -> List[Dict]:
        """
        모든 마켓의 정보를 가져옵니다.
        
        Returns:
            마켓 정보 리스트
        """
        try:
            markets = pyupbit.get_market_all()
            return markets
        except Exception as e:
            print(f"마켓 정보 조회 오류: {e}")
            return []
    
    def get_btc_price(self) -> Optional[float]:
        """
        비트코인 현재가를 가져옵니다.
        
        Returns:
            비트코인 현재가 (원)
        """
        return self.get_current_price("KRW-BTC")
    
    def filter_by_volume(self, tickers: List[str], min_volume: float) -> List[str]:
        """
        최소 거래량 기준으로 티커를 필터링합니다.
        
        Args:
            tickers: 티커 리스트
            min_volume: 최소 24시간 거래대금
            
        Returns:
            필터링된 티커 리스트
        """
        filtered = []
        for ticker in tickers:
            try:
                ticker_data = self.get_24h_ticker(ticker)
                if ticker_data and ticker_data.get('acc_trade_price_24h', 0) >= min_volume:
                    filtered.append(ticker)
                time.sleep(0.1)  # API 호출 제한 방지
            except Exception as e:
                continue
        return filtered

