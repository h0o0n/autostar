"""
백테스팅 모듈
과거 데이터를 사용하여 전략의 성과를 검증합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from upbit_client import UpbitClient
from indicators import TechnicalIndicators
from trend_analyzer import TrendAnalyzer
from recommender import StockRecommender
from risk_manager import RiskManager
from whale_analyzer import WhaleAnalyzer
from surge_analyzer import SurgeAnalyzer
import config

class Backtester:
    """백테스팅을 수행하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
        """
        self.client = upbit_client
        self.trend_analyzer = TrendAnalyzer(upbit_client)
        self.whale_analyzer = WhaleAnalyzer(upbit_client)  # 백테스팅에서는 사용 안 함
        self.surge_analyzer = SurgeAnalyzer(upbit_client)
        self.recommender = StockRecommender(
            upbit_client, 
            self.trend_analyzer, 
            None,  # 고래 분석기는 백테스팅에서 제외
            self.surge_analyzer
        )
        self.risk_manager = RiskManager()
    
    def get_historical_data(self, ticker: str, start_date: str, end_date: str, interval: str = "day") -> Optional[pd.DataFrame]:
        """
        과거 데이터를 가져옵니다.
        
        Args:
            ticker: 티커 심볼
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            interval: 시간 단위
            
        Returns:
            OHLCV 데이터프레임
        """
        try:
            # 시작일과 종료일 사이의 일수 계산
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            days = (end - start).days
            
            # 충분한 데이터 가져오기 (여유 있게)
            count = days + 100
            
            df = self.client.get_ohlcv(ticker, interval=interval, count=count)
            if df is None or df.empty:
                return None
            
            # 날짜 필터링 (인덱스가 날짜인 경우)
            if isinstance(df.index, pd.DatetimeIndex):
                df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            return df
        except Exception as e:
            print(f"{ticker} 과거 데이터 조회 오류: {e}")
            return None
    
    def simulate_trade(self, ticker: str, entry_date: str, entry_price: float, 
                      exit_date: str, exit_price: float, position_size: float) -> Dict:
        """
        단일 거래를 시뮬레이션합니다.
        
        Args:
            ticker: 티커 심볼
            entry_date: 진입일
            entry_price: 진입가
            exit_date: 청산일
            exit_price: 청산가
            position_size: 포지션 크기 (수량)
            
        Returns:
            거래 결과 딕셔너리
        """
        entry_value = entry_price * position_size
        exit_value = exit_price * position_size
        profit = exit_value - entry_value
        profit_percent = (profit / entry_value * 100) if entry_value > 0 else 0
        
        return {
            'ticker': ticker,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'position_size': position_size,
            'entry_value': entry_value,
            'exit_value': exit_value,
            'profit': profit,
            'profit_percent': profit_percent
        }
    
    def backtest_strategy(self, ticker: str, start_date: str, end_date: str, 
                         initial_capital: float = 10000000) -> Dict:
        """
        단일 종목에 대한 백테스팅을 수행합니다.
        
        Args:
            ticker: 티커 심볼
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            initial_capital: 초기 자본금
            
        Returns:
            백테스팅 결과 딕셔너리
        """
        # 과거 데이터 가져오기
        df = self.get_historical_data(ticker, start_date, end_date)
        if df is None or df.empty:
            return {'error': '데이터 없음'}
        
        # 비트코인 추세 데이터도 가져오기 (각 시점별로)
        btc_df = self.get_historical_data("KRW-BTC", start_date, end_date)
        
        trades = []  # 거래 내역
        current_capital = initial_capital
        position = None  # 현재 포지션 {date, price, size, stop_loss, take_profit_levels}
        
        # 각 날짜별로 시뮬레이션
        for i in range(len(df)):
            current_date = df.index[i] if isinstance(df.index, pd.DatetimeIndex) else i
            current_price = df['close'].iloc[i]
            
            # 현재 시점의 데이터로 지표 계산
            historical_df = df.iloc[:i+1]  # 현재까지의 데이터
            
            if len(historical_df) < 60:  # 충분한 데이터가 없으면 스킵
                continue
            
            # 포지션이 없으면 매수 신호 확인
            if position is None:
                # 기술적 지표 계산
                tech_indicators = TechnicalIndicators(historical_df)
                indicators = tech_indicators.calculate_all_indicators({
                    'RSI_PERIOD': config.RSI_PERIOD,
                    'MACD_FAST': config.MACD_FAST,
                    'MACD_SLOW': config.MACD_SLOW,
                    'MACD_SIGNAL': config.MACD_SIGNAL,
                    'BB_PERIOD': config.BB_PERIOD,
                    'BB_STD': config.BB_STD,
                    'MA_SHORT': config.MA_SHORT,
                    'MA_MEDIUM': config.MA_MEDIUM,
                    'MA_LONG': config.MA_LONG,
                })
                
                # 비트코인 추세 분석 (현재 시점 기준)
                btc_trend = None
                if btc_df is not None and len(btc_df) > i:
                    btc_historical = btc_df.iloc[:i+1]
                    if len(btc_historical) >= 60:
                        # 비트코인 추세 분석 (간단 버전)
                        btc_ma5 = btc_historical['close'].rolling(window=5).mean().iloc[-1]
                        btc_ma20 = btc_historical['close'].rolling(window=20).mean().iloc[-1]
                        btc_current = btc_historical['close'].iloc[-1]
                        
                        is_uptrend = (btc_ma5 > btc_ma20) and (btc_current > btc_ma5)
                        is_downtrend = (btc_ma5 < btc_ma20) and (btc_current < btc_ma5)
                        
                        btc_trend = {
                            'trend_direction': '상승' if is_uptrend else ('하락' if is_downtrend else '횡보'),
                            'is_uptrend': is_uptrend,
                            'is_downtrend': is_downtrend,
                            'trend_strength': abs(btc_ma5 - btc_ma20) / btc_ma20 if btc_ma20 > 0 else 0
                        }
                
                # 점수 계산
                if btc_trend:
                    score_data = self.recommender.calculate_total_score(ticker, indicators, btc_trend)
                    
                    # 매수 조건: 점수가 높고, 비트코인이 하락 추세가 아닐 때
                    if score_data['total_score'] >= 0.6 and not btc_trend.get('is_downtrend', False):
                        # 리스크 파라미터 계산
                        risk_params = self.risk_manager.calculate_all_risk_parameters(
                            current_price,
                            indicators,
                            btc_trend=btc_trend
                        )
                        
                        # 포지션 진입
                        position_size = risk_params['position_size']
                        if position_size > 0 and current_capital >= risk_params['position_value']:
                            position = {
                                'entry_date': current_date,
                                'entry_price': risk_params['entry_price'],
                                'position_size': position_size,
                                'stop_loss': risk_params['stop_loss_price'],
                                'take_profit_levels': risk_params.get('take_profit_levels', []),
                                'exited_levels': [],
                                'entry_value': risk_params['position_value']
                            }
                            current_capital -= risk_params['position_value']
            
            # 포지션이 있으면 청산 조건 확인
            else:
                entry_price = position['entry_price']
                stop_loss = position['stop_loss']
                take_profit_levels = position['take_profit_levels']
                exited_levels = position['exited_levels']
                
                # 손절 확인
                if current_price <= stop_loss:
                    # 손절 실행
                    exit_value = current_price * position['position_size']
                    current_capital += exit_value
                    
                    trade = self.simulate_trade(
                        ticker, position['entry_date'], entry_price,
                        current_date, current_price, position['position_size']
                    )
                    trade['exit_reason'] = '손절'
                    trades.append(trade)
                    position = None
                
                # 분할 익절 확인
                elif take_profit_levels:
                    total_exit_value = 0
                    new_exited_levels = []
                    
                    for level in take_profit_levels:
                        level_num = level['level']
                        profit_price = level['profit_price']
                        ratio = level['ratio']
                        
                        if level_num not in exited_levels and current_price >= profit_price:
                            # 이 레벨 익절
                            exit_size = position['position_size'] * ratio
                            exit_value = current_price * exit_size
                            total_exit_value += exit_value
                            new_exited_levels.append(level_num)
                            
                            # 부분 익절 거래 기록
                            trade = self.simulate_trade(
                                ticker, position['entry_date'], entry_price,
                                current_date, current_price, exit_size
                            )
                            trade['exit_reason'] = f'익절 레벨 {level_num}'
                            trades.append(trade)
                    
                    if new_exited_levels:
                        position['exited_levels'].extend(new_exited_levels)
                        current_capital += total_exit_value
                        
                        # 모든 레벨 익절 완료
                        if len(position['exited_levels']) >= len(take_profit_levels):
                            position = None
        
        # 최종 결과 계산
        final_value = current_capital
        if position:
            # 미청산 포지션이 있으면 현재가로 청산
            final_value += current_price * position['position_size']
        
        total_return = (final_value - initial_capital) / initial_capital * 100
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['profit'] > 0])
        losing_trades = len([t for t in trades if t['profit'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t['profit'] for t in trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        return {
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'trades': trades
        }
    
    def backtest_multiple_stocks(self, tickers: List[str], start_date: str, end_date: str,
                                 initial_capital: float = 10000000, max_positions: int = 5) -> Dict:
        """
        여러 종목에 대한 백테스팅을 수행합니다.
        
        Args:
            tickers: 티커 리스트
            start_date: 시작일
            end_date: 종료일
            initial_capital: 초기 자본금
            max_positions: 최대 동시 포지션 수
            
        Returns:
            종합 백테스팅 결과
        """
        results = []
        
        for ticker in tickers:
            print(f"{ticker} 백테스팅 중...")
            result = self.backtest_strategy(ticker, start_date, end_date, initial_capital)
            if 'error' not in result:
                results.append(result)
        
        if not results:
            return {'error': '백테스팅 결과 없음'}
        
        # 종합 결과 계산
        total_return = np.mean([r['total_return'] for r in results])
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        total_trades = sum([r['total_trades'] for r in results])
        
        return {
            'summary': {
                'total_stocks': len(results),
                'avg_return': total_return,
                'avg_win_rate': avg_win_rate,
                'total_trades': total_trades
            },
            'individual_results': results
        }

