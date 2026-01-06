"""
리스크 관리 모듈
진입가와 손절가를 계산하고 리스크를 관리합니다.
비트코인 추세에 따라 익절가를 조정합니다.
"""
import config
from typing import Dict, Optional

class RiskManager:
    """리스크를 관리하는 클래스"""
    
    def __init__(self):
        """초기화"""
        self.stop_loss_percent = config.STOP_LOSS_PERCENT
        self.take_profit_percent = config.TAKE_PROFIT_PERCENT
        self.max_position_size = config.MAX_POSITION_SIZE
        
        # 분할 익절 레벨 설정
        self.take_profit_levels_uptrend = config.TAKE_PROFIT_LEVELS_UPTREND
        self.take_profit_levels_downtrend = config.TAKE_PROFIT_LEVELS_DOWNTREND
        self.take_profit_levels_sideways = config.TAKE_PROFIT_LEVELS_SIDEWAYS
    
    def calculate_entry_price(self, current_price: float, indicators: Dict) -> Dict:
        """
        진입가를 계산합니다.
        기술적 지표를 기반으로 최적의 진입가를 제안합니다.
        
        Args:
            current_price: 현재가
            indicators: 기술적 지표 딕셔너리
            
        Returns:
            진입가 정보 딕셔너리
        """
        # 기본 진입가 (현재가)
        entry_price = current_price
        
        # 볼린저 밴드 하단 근처면 조금 더 낮은 가격 제안
        bb_data = indicators.get('bollinger')
        if bb_data:
            bb_lower = bb_data.get('lower')
            bb_position = bb_data.get('position', 0.5)
            
            # 하단 밴드 근처면 하단 밴드 가격을 진입가로 제안
            if bb_position < 0.3 and bb_lower:
                entry_price = min(entry_price, bb_lower * 1.01)  # 하단 밴드보다 1% 위
        
        # 이동평균선 근처면 이동평균선 가격 제안
        ma_data = indicators.get('moving_averages')
        if ma_data:
            ma_short = ma_data.get('ma_short')
            ma_medium = ma_data.get('ma_medium')
            
            if ma_short and current_price > ma_short:
                # 현재가가 단기 이동평균선 위면, 단기 이동평균선 근처 진입 제안
                entry_price = min(entry_price, ma_short * 1.02)
            elif ma_medium and current_price > ma_medium:
                entry_price = min(entry_price, ma_medium * 1.02)
        
        return {
            'suggested_entry': entry_price,
            'current_price': current_price,
            'entry_premium': ((current_price - entry_price) / current_price * 100) if current_price > 0 else 0
        }
    
    def calculate_stop_loss(self, entry_price: float, current_price: float, indicators: Dict) -> Dict:
        """
        손절가를 계산합니다.
        
        Args:
            entry_price: 진입가
            current_price: 현재가
            indicators: 기술적 지표 딕셔너리
            
        Returns:
            손절가 정보 딕셔너리
        """
        # 기본 손절가 (진입가의 손절 비율만큼 하락)
        base_stop_loss = entry_price * (1 - self.stop_loss_percent / 100)
        
        # 볼린저 밴드 하단을 고려
        stop_loss = base_stop_loss
        bb_data = indicators.get('bollinger')
        if bb_data:
            bb_lower = bb_data.get('lower')
            if bb_lower and bb_lower < base_stop_loss:
                # 볼린저 밴드 하단이 더 낮으면, 그 아래로 손절가 설정
                stop_loss = bb_lower * 0.98
        
        # 이동평균선을 고려
        ma_data = indicators.get('moving_averages')
        if ma_data:
            ma_long = ma_data.get('ma_long')
            if ma_long and ma_long < stop_loss:
                # 장기 이동평균선이 손절가보다 낮으면, 그 아래로 설정
                stop_loss = ma_long * 0.97
        
        # 손절가가 진입가보다 높으면 안됨
        stop_loss = min(stop_loss, entry_price * 0.99)
        
        return {
            'stop_loss_price': stop_loss,
            'stop_loss_percent': ((entry_price - stop_loss) / entry_price * 100) if entry_price > 0 else 0,
            'risk_amount_per_unit': entry_price - stop_loss
        }
    
    def calculate_take_profit(self, entry_price: float, btc_trend: Optional[Dict] = None) -> Dict:
        """
        분할 익절 전략을 계산합니다.
        비트코인 추세에 따라 여러 익절 레벨을 설정합니다.
        
        Args:
            entry_price: 진입가
            btc_trend: 비트코인 추세 정보 (선택사항)
            
        Returns:
            분할 익절 정보 딕셔너리
        """
        # 비트코인 추세 확인
        if btc_trend:
            is_uptrend = btc_trend.get('is_uptrend', False)
            is_downtrend = btc_trend.get('is_downtrend', False)
            trend_direction = btc_trend.get('trend_direction', '불명확')
            
            # 추세에 따라 익절 레벨 선택
            if is_downtrend or trend_direction == "하락":
                take_profit_levels = self.take_profit_levels_downtrend
                trend_mode = "하락추세"
            elif is_uptrend or trend_direction == "상승":
                take_profit_levels = self.take_profit_levels_uptrend
                trend_mode = "상승추세"
            else:
                take_profit_levels = self.take_profit_levels_sideways
                trend_mode = "횡보"
        else:
            # 추세 정보가 없으면 기본값 사용
            take_profit_levels = self.take_profit_levels_sideways
            trend_mode = "기본"
        
        # 분할 익절 레벨 계산
        take_profit_levels_detail = []
        cumulative_ratio = 0.0
        
        for profit_percent, ratio in take_profit_levels:
            profit_price = entry_price * (1 + profit_percent / 100)
            profit_amount = profit_price - entry_price
            
            take_profit_levels_detail.append({
                'level': len(take_profit_levels_detail) + 1,
                'profit_percent': profit_percent,
                'profit_price': profit_price,
                'profit_amount': profit_amount,
                'ratio': ratio,  # 이 레벨에서 익절할 비율
                'cumulative_ratio': cumulative_ratio + ratio  # 누적 비율
            })
            
            cumulative_ratio += ratio
        
        # 첫 번째 익절 레벨 (가장 낮은 레벨)
        first_take_profit = take_profit_levels_detail[0] if take_profit_levels_detail else None
        
        # 평균 익절가 계산 (가중 평균)
        avg_profit_percent = sum(
            level['profit_percent'] * level['ratio'] 
            for level in take_profit_levels_detail
        )
        
        return {
            'take_profit_levels': take_profit_levels_detail,  # 모든 익절 레벨
            'first_take_profit_price': first_take_profit['profit_price'] if first_take_profit else entry_price * 1.05,
            'first_take_profit_percent': first_take_profit['profit_percent'] if first_take_profit else 5.0,
            'avg_take_profit_percent': avg_profit_percent,
            'trend_mode': trend_mode,
            'total_levels': len(take_profit_levels_detail)
        }
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float, total_capital: float) -> Dict:
        """
        포지션 크기를 계산합니다.
        
        Args:
            entry_price: 진입가
            stop_loss_price: 손절가
            total_capital: 총 자본금
            
        Returns:
            포지션 크기 정보 딕셔너리
        """
        # 리스크 금액 (진입가와 손절가의 차이)
        risk_per_unit = entry_price - stop_loss_price
        if risk_per_unit <= 0:
            return {
                'position_size': 0,
                'position_value': 0,
                'max_risk_amount': 0
            }
        
        # 최대 리스크 금액 (총 자본의 2%)
        max_risk = total_capital * 0.02
        
        # 포지션 크기 계산 (최대 리스크 금액 / 리스크 금액)
        position_size = max_risk / risk_per_unit
        
        # 최대 포지션 크기 제한
        max_position_value = total_capital * self.max_position_size
        max_position_size_by_capital = max_position_value / entry_price
        
        position_size = min(position_size, max_position_size_by_capital)
        
        position_value = position_size * entry_price
        
        return {
            'position_size': position_size,
            'position_value': position_value,
            'max_risk_amount': position_size * risk_per_unit,
            'risk_percent_of_capital': (position_size * risk_per_unit / total_capital * 100) if total_capital > 0 else 0
        }
    
    def calculate_all_risk_parameters(self, current_price: float, indicators: Dict, 
                                     total_capital: float = 10000000, 
                                     btc_trend: Optional[Dict] = None) -> Dict:
        """
        모든 리스크 관리 파라미터를 계산합니다.
        
        Args:
            current_price: 현재가
            indicators: 기술적 지표 딕셔너리
            total_capital: 총 자본금 (기본값: 1천만원)
            btc_trend: 비트코인 추세 정보 (선택사항)
            
        Returns:
            모든 리스크 파라미터를 포함한 딕셔너리
        """
        # 진입가 계산
        entry_info = self.calculate_entry_price(current_price, indicators)
        entry_price = entry_info['suggested_entry']
        
        # 손절가 계산
        stop_loss_info = self.calculate_stop_loss(entry_price, current_price, indicators)
        
        # 익절가 계산 (비트코인 추세 반영)
        take_profit_info = self.calculate_take_profit(entry_price, btc_trend)
        
        # 포지션 크기 계산
        position_info = self.calculate_position_size(
            entry_price,
            stop_loss_info['stop_loss_price'],
            total_capital
        )
        
        # 첫 번째 익절 레벨 기준으로 리스크/보상 비율 계산
        first_profit = take_profit_info['first_take_profit_price'] - entry_price
        risk_reward_ratio = (
            first_profit / stop_loss_info['risk_amount_per_unit']
            if stop_loss_info['risk_amount_per_unit'] > 0 else 0
        )
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'stop_loss_price': stop_loss_info['stop_loss_price'],
            'stop_loss_percent': stop_loss_info['stop_loss_percent'],
            'position_size': position_info['position_size'],
            'position_value': position_info['position_value'],
            'max_risk_amount': position_info['max_risk_amount'],
            'risk_reward_ratio': risk_reward_ratio,
            # 분할 익절 정보
            'take_profit_levels': take_profit_info['take_profit_levels'],
            'first_take_profit_price': take_profit_info['first_take_profit_price'],
            'first_take_profit_percent': take_profit_info['first_take_profit_percent'],
            'avg_take_profit_percent': take_profit_info['avg_take_profit_percent'],
            'trend_mode': take_profit_info['trend_mode'],
            'total_levels': take_profit_info['total_levels']
        }

