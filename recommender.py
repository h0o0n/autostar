"""
종목 추천 엔진
여러 기술적 지표를 종합하여 매수 추천 종목을 선정합니다.
"""
import config
from typing import List, Dict, Optional
from colorama import Fore, Style
from upbit_client import UpbitClient
from indicators import TechnicalIndicators
from trend_analyzer import TrendAnalyzer
from whale_analyzer import WhaleAnalyzer
from surge_analyzer import SurgeAnalyzer

class StockRecommender:
    """종목을 추천하는 클래스"""
    
    def __init__(self, upbit_client: UpbitClient, trend_analyzer: TrendAnalyzer, 
                 whale_analyzer: Optional[WhaleAnalyzer] = None, 
                 surge_analyzer: Optional[SurgeAnalyzer] = None):
        """
        초기화
        
        Args:
            upbit_client: UpbitClient 인스턴스
            trend_analyzer: TrendAnalyzer 인스턴스
            whale_analyzer: WhaleAnalyzer 인스턴스 (선택사항)
            surge_analyzer: SurgeAnalyzer 인스턴스 (선택사항)
        """
        self.client = upbit_client
        self.trend_analyzer = trend_analyzer
        self.whale_analyzer = whale_analyzer
        self.surge_analyzer = surge_analyzer
        self.config = {
            'RSI_PERIOD': config.RSI_PERIOD,
            'RSI_OVERSOLD': config.RSI_OVERSOLD,
            'RSI_OVERBOUGHT': config.RSI_OVERBOUGHT,
            'MACD_FAST': config.MACD_FAST,
            'MACD_SLOW': config.MACD_SLOW,
            'MACD_SIGNAL': config.MACD_SIGNAL,
            'BB_PERIOD': config.BB_PERIOD,
            'BB_STD': config.BB_STD,
            'MA_SHORT': config.MA_SHORT,
            'MA_MEDIUM': config.MA_MEDIUM,
            'MA_LONG': config.MA_LONG,
            'WEIGHT_RSI': config.WEIGHT_RSI,
            'WEIGHT_MACD': config.WEIGHT_MACD,
            'WEIGHT_BB': config.WEIGHT_BB,
            'WEIGHT_MA': config.WEIGHT_MA,
            'WEIGHT_VOLUME': config.WEIGHT_VOLUME,
            'WEIGHT_BTC_CORRELATION': config.WEIGHT_BTC_CORRELATION,
            'WEIGHT_WHALE': config.WEIGHT_WHALE,
            'WEIGHT_SURGE': config.WEIGHT_SURGE,
        }
    
    def calculate_rsi_score(self, rsi: Optional[float]) -> float:
        """
        RSI 점수를 계산합니다.
        과매도 구간에 가까울수록 높은 점수 (매수 기회)
        
        Args:
            rsi: RSI 값
            
        Returns:
            RSI 점수 (0-1)
        """
        if rsi is None:
            return 0.0
        
        # 과매도 구간 (30 이하)에 가까울수록 높은 점수
        if rsi <= self.config['RSI_OVERSOLD']:
            return 1.0
        elif rsi >= self.config['RSI_OVERBOUGHT']:
            return 0.0
        else:
            # 30-70 사이를 선형으로 매핑 (30에 가까울수록 높은 점수)
            return 1.0 - (rsi - self.config['RSI_OVERSOLD']) / (self.config['RSI_OVERBOUGHT'] - self.config['RSI_OVERSOLD'])
    
    def calculate_macd_score(self, macd_data: Optional[Dict]) -> float:
        """
        MACD 점수를 계산합니다.
        MACD가 시그널을 상향 돌파하고 있을 때 높은 점수
        
        Args:
            macd_data: MACD 정보 딕셔너리
            
        Returns:
            MACD 점수 (0-1)
        """
        if macd_data is None:
            return 0.0
        
        macd = macd_data.get('macd', 0)
        signal = macd_data.get('signal', 0)
        histogram = macd_data.get('histogram', 0)
        
        # MACD가 시그널 위에 있고, 히스토그램이 양수면 높은 점수
        if macd > signal and histogram > 0:
            # 히스토그램이 양수이고 증가 추세면 높은 점수
            # 히스토그램 크기를 정규화 (현재가 대비)
            if abs(signal) > 0:
                histogram_ratio = abs(histogram) / abs(signal)
                # 0.5 ~ 2.0 범위를 0.5 ~ 1.0으로 매핑
                score = 0.5 + min(histogram_ratio / 2.0, 0.5)
            else:
                score = 0.7  # 시그널이 0에 가까우면 기본 점수
            return min(1.0, max(0.5, score))
        elif macd > signal:
            return 0.3  # MACD가 시그널 위지만 히스토그램이 음수 (약한 상승)
        elif macd < signal and histogram < 0:
            return 0.0  # MACD가 시그널 아래이고 하락 추세
        else:
            return 0.1  # MACD가 시그널 아래지만 히스토그램이 양수 (약한 하락)
    
    def calculate_bb_score(self, bb_data: Optional[Dict]) -> float:
        """
        볼린저 밴드 점수를 계산합니다.
        하단 밴드 근처에 있을수록 높은 점수 (반등 기대)
        
        Args:
            bb_data: 볼린저 밴드 정보 딕셔너리
            
        Returns:
            볼린저 밴드 점수 (0-1)
        """
        if bb_data is None:
            return 0.0
        
        position = bb_data.get('position', 0.5)
        
        # 하단 밴드 근처(0에 가까울수록) 높은 점수
        if position <= 0.2:
            return 1.0
        elif position >= 0.8:
            return 0.0
        else:
            return 1.0 - position
    
    def calculate_ma_score(self, ma_data: Optional[Dict]) -> float:
        """
        이동평균선 점수를 계산합니다.
        상승 정렬 상태일수록 높은 점수
        
        Args:
            ma_data: 이동평균선 정보 딕셔너리
            
        Returns:
            이동평균선 점수 (0-1)
        """
        if ma_data is None:
            return 0.0
        
        current_price = ma_data.get('current_price', 0)
        ma_short = ma_data.get('ma_short')
        ma_medium = ma_data.get('ma_medium')
        ma_long = ma_data.get('ma_long')
        alignment_score = ma_data.get('alignment_score', 0)
        
        if not all([current_price, ma_short, ma_medium]):
            return 0.0
        
        # 현재가가 단기 이동평균선 위에 있는지 확인
        price_above_short = 1.0 if current_price > ma_short else 0.0
        
        # 이동평균선 정렬 점수와 결합
        return (alignment_score * 0.6 + price_above_short * 0.4)
    
    def calculate_volume_score(self, volume_data: Optional[Dict]) -> float:
        """
        거래량 점수를 계산합니다.
        평균보다 거래량이 많을수록 높은 점수
        
        Args:
            volume_data: 거래량 정보 딕셔너리
            
        Returns:
            거래량 점수 (0-1)
        """
        if volume_data is None:
            return 0.0
        
        volume_ratio = volume_data.get('volume_ratio', 1.0)
        
        # 거래량 비율이 1.5배 이상이면 높은 점수
        if volume_ratio >= 2.0:
            return 1.0
        elif volume_ratio >= 1.5:
            return 0.8
        elif volume_ratio >= 1.0:
            return 0.5
        else:
            return max(0.0, volume_ratio - 0.5)
    
    def calculate_btc_correlation_score(self, correlation: Optional[float], relative_strength: Optional[float]) -> float:
        """
        비트코인 상관관계 점수를 계산합니다.
        비트코인보다 강한 상대 강도를 보일 때 높은 점수
        
        Args:
            correlation: 비트코인과의 상관계수
            relative_strength: 비트코인 대비 상대 강도
            
        Returns:
            상관관계 점수 (0-1)
        """
        if relative_strength is None:
            return 0.0
        
        # 상대 강도가 높을수록 높은 점수
        return relative_strength
    
    def calculate_total_score(self, ticker: str, indicators: Dict, btc_trend: Dict) -> Dict:
        """
        종목의 총점을 계산합니다.
        
        Args:
            ticker: 티커 심볼
            indicators: 기술적 지표 딕셔너리
            btc_trend: 비트코인 추세 정보
            
        Returns:
            점수 정보 딕셔너리
        """
        # 각 지표별 점수 계산
        rsi_score = self.calculate_rsi_score(indicators.get('rsi'))
        macd_score = self.calculate_macd_score(indicators.get('macd'))
        bb_score = self.calculate_bb_score(indicators.get('bollinger'))
        ma_score = self.calculate_ma_score(indicators.get('moving_averages'))
        volume_score = self.calculate_volume_score(indicators.get('volume'))
        
        # 비트코인 상관관계 및 상대 강도
        correlation = self.trend_analyzer.calculate_correlation_with_btc(ticker)
        relative_strength = self.trend_analyzer.calculate_relative_strength(ticker, btc_trend)
        btc_score = self.calculate_btc_correlation_score(correlation, relative_strength)
        
        # 고래 활동 점수
        # 데이터가 없으면 점수를 낮춤 (중립보다는 부정적)
        whale_score = 0.3  # 기본값 (데이터 없음 = 낮은 점수)
        whale_activity = None
        if self.whale_analyzer:
            whale_activity = self.whale_analyzer.analyze_whale_activity(ticker)
            if whale_activity:
                whale_score = whale_activity.get('score', 0.3)
            else:
                whale_score = 0.3  # 데이터 없음
        
        # 급등 가능성 점수
        # 데이터가 없으면 점수를 낮춤
        surge_score = 0.3  # 기본값 (데이터 없음 = 낮은 점수)
        surge_analysis = None
        if self.surge_analyzer:
            surge_analysis = self.surge_analyzer.analyze_short_term_surge_potential(ticker)
            if surge_analysis and surge_analysis.get('total_score') is not None:
                surge_score = surge_analysis.get('total_score', 0.3)
            else:
                surge_score = 0.3  # 데이터 없음
        
        # 비트코인 추세에 따른 필터링 및 가중치 조정
        btc_trend_direction = btc_trend.get('trend_direction', '불명확')
        btc_trend_strength = btc_trend.get('trend_strength', 0.5)
        btc_is_uptrend = btc_trend.get('is_uptrend', False)
        btc_is_downtrend = btc_trend.get('is_downtrend', False)
        
        # 비트코인 추세에 따른 점수 조정
        # 하락 추세일 때는 더 공격적으로 점수 감소
        btc_trend_multiplier = 1.0
        if btc_is_downtrend:
            # 강한 하락 추세일 때는 점수를 0.2~0.4배로 크게 감소
            # 추세가 강할수록 더 많이 감소
            btc_trend_multiplier = max(0.2, 1.0 - btc_trend_strength * 0.8)
        elif btc_is_uptrend:
            # 상승 추세일 때는 점수를 1.0~1.15배로 소폭 증가 (과도한 증가 방지)
            btc_trend_multiplier = min(1.15, 1.0 + btc_trend_strength * 0.15)
        else:
            # 횡보일 때는 약간 감소
            btc_trend_multiplier = 0.85
        
        # 거래량 점수 강화 (더 합리적인 방식)
        # 거래량이 평균의 2배 이상이면 추가 보너스
        volume_bonus = 0.0
        if volume_score >= 0.6:  # 거래량이 이미 높으면
            volume_bonus = (volume_score - 0.6) * 0.5  # 최대 0.2 보너스
        enhanced_volume_score = min(1.0, volume_score + volume_bonus)
        
        # 가중 평균으로 총점 계산 (정규화된 가중치 사용)
        # 거래량은 중요하지만 2배 가중은 너무 과함, 대신 가중치 자체를 높임
        base_score = (
            rsi_score * self.config['WEIGHT_RSI'] +
            macd_score * self.config['WEIGHT_MACD'] +
            bb_score * self.config['WEIGHT_BB'] +
            ma_score * self.config['WEIGHT_MA'] +
            enhanced_volume_score * (self.config['WEIGHT_VOLUME'] * 1.5) +  # 거래량 1.5배 가중 (정규화)
            btc_score * self.config['WEIGHT_BTC_CORRELATION'] +
            whale_score * self.config['WEIGHT_WHALE'] +
            surge_score * self.config['WEIGHT_SURGE']
        )
        
        # 가중치 합계 정규화 (거래량 1.5배 반영)
        total_weight = (
            self.config['WEIGHT_RSI'] +
            self.config['WEIGHT_MACD'] +
            self.config['WEIGHT_BB'] +
            self.config['WEIGHT_MA'] +
            self.config['WEIGHT_VOLUME'] * 1.5 +
            self.config['WEIGHT_BTC_CORRELATION'] +
            self.config['WEIGHT_WHALE'] +
            self.config['WEIGHT_SURGE']
        )
        
        # 정규화 (총 가중치로 나누기)
        if total_weight > 0:
            base_score = base_score / total_weight
        
        # 비트코인 추세에 따른 최종 점수 조정
        total_score = base_score * btc_trend_multiplier
        
        return {
            'ticker': ticker,
            'total_score': total_score,
            'base_score': base_score,  # 조정 전 점수
            'btc_trend_multiplier': btc_trend_multiplier,  # 비트코인 추세 배수
            'rsi_score': rsi_score,
            'macd_score': macd_score,
            'bb_score': bb_score,
            'ma_score': ma_score,
            'volume_score': enhanced_volume_score,  # 강화된 거래량 점수
            'btc_score': btc_score,
            'whale_score': whale_score,
            'surge_score': surge_score,
            'whale_activity': whale_activity,
            'surge_analysis': surge_analysis,
            'indicators': indicators,
            'correlation': correlation,
            'relative_strength': relative_strength,
            'btc_trend_direction': btc_trend_direction
        }
    
    def recommend_stocks(self, top_n: int = 10) -> List[Dict]:
        """
        추천 종목을 선정합니다.
        
        Args:
            top_n: 추천할 종목 개수
            
        Returns:
            추천 종목 리스트 (점수 순으로 정렬)
        """
        print("비트코인 추세 분석 중...")
        btc_trend = self.trend_analyzer.analyze_btc_trend()
        if btc_trend is None:
            print("비트코인 추세 분석 실패")
            return []
        
        trend_direction = btc_trend['trend_direction']
        trend_strength = btc_trend['trend_strength']
        trend_signal = btc_trend.get('trend_signal', '불명확')
        is_uptrend = btc_trend.get('is_uptrend', False)
        is_downtrend = btc_trend.get('is_downtrend', False)
        
        print(f"비트코인 추세: {trend_signal} (방향: {trend_direction}, 강도: {trend_strength:.2f})")
        
        # 비트코인 하락 추세일 때 경고
        if is_downtrend:
            print(f"{Fore.RED}⚠️  경고: 비트코인이 하락 추세입니다. 알트코인 추천이 제한됩니다.{Style.RESET_ALL}")
        elif is_uptrend:
            print(f"{Fore.GREEN}✓ 비트코인이 상승 추세입니다. 알트코인 추천에 유리합니다.{Style.RESET_ALL}")
        
        # KRW 마켓 티커 가져오기
        print("거래 가능한 종목 조회 중...")
        all_tickers = self.client.get_ticker_list("KRW")
        
        # 비트코인 제외
        tickers = [t for t in all_tickers if t != "KRW-BTC"]
        
        # 최소 거래량 필터링
        print(f"거래량 필터링 중... (최소 거래대금: {config.MIN_VOLUME_24H:,.0f}원)")
        tickers = self.client.filter_by_volume(tickers, config.MIN_VOLUME_24H)
        
        print(f"분석 대상 종목 수: {len(tickers)}개")
        
        # 각 종목 분석
        recommendations = []
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"[{i}/{len(tickers)}] {ticker} 분석 중...")
                
                # OHLCV 데이터 가져오기
                df = self.client.get_ohlcv(ticker, interval="day", count=200)
                if df is None or df.empty:
                    continue
                
                # 기술적 지표 계산
                tech_indicators = TechnicalIndicators(df)
                indicators = tech_indicators.calculate_all_indicators(self.config)
                
                # 총점 계산
                score_data = self.calculate_total_score(ticker, indicators, btc_trend)
                
                # 현재가 추가
                current_price = self.client.get_current_price(ticker)
                if current_price:
                    score_data['current_price'] = current_price
                    score_data['btc_trend_info'] = btc_trend  # 비트코인 추세 정보 포함
                    recommendations.append(score_data)
                
            except Exception as e:
                print(f"{ticker} 분석 중 오류 발생: {e}")
                continue
        
        # 비트코인 추세에 따른 필터링
        btc_is_downtrend = btc_trend.get('is_downtrend', False)
        btc_is_uptrend = btc_trend.get('is_uptrend', False)
        
        # 비트코인 추세에 따른 필터링
        if btc_is_downtrend:
            # 하락 추세일 때는 매우 높은 최소 점수 기준 적용 (더 보수적)
            min_score_threshold = 0.65  # 하락 추세일 때는 높은 기준
            recommendations = [r for r in recommendations if r['total_score'] >= min_score_threshold]
            
            if len(recommendations) == 0:
                print(f"{Fore.RED}⚠️  비트코인 강한 하락 추세: 추천할 종목이 없습니다. 매수를 자제하세요.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️  비트코인 하락 추세: 매우 보수적으로 {len(recommendations)}개 종목만 추천됩니다.{Style.RESET_ALL}")
        elif btc_is_uptrend:
            # 상승 추세일 때는 더 많은 종목 추천 가능
            print(f"{Fore.GREEN}✓ 비트코인 상승 추세: 알트코인 추천에 유리한 환경입니다.{Style.RESET_ALL}")
        else:
            # 횡보일 때는 보통 기준
            min_score_threshold = 0.55
            recommendations = [r for r in recommendations if r['total_score'] >= min_score_threshold]
            print(f"{Fore.YELLOW}비트코인 횡보: 보통 기준으로 추천합니다.{Style.RESET_ALL}")
        
        # 점수 순으로 정렬
        recommendations.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 상위 N개 반환
        return recommendations[:top_n]

