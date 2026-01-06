"""
업비트 암호화폐 추천 및 모니터링 시스템
메인 실행 파일
"""
import sys
import config
from colorama import Fore, Style, init
from upbit_client import UpbitClient
from trend_analyzer import TrendAnalyzer
from recommender import StockRecommender
from risk_manager import RiskManager
from monitor import StockMonitor
from whale_analyzer import WhaleAnalyzer
from surge_analyzer import SurgeAnalyzer

# colorama 초기화
init(autoreset=True)

def print_header():
    """프로그램 헤더 출력"""
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{'업비트 암호화폐 추천 및 모니터링 시스템':^100}")
    print(f"{'='*100}{Style.RESET_ALL}\n")

def print_recommendations(recommendations):
    """
    추천 종목을 출력합니다.
    
    Args:
        recommendations: 추천 종목 리스트
    """
    if not recommendations:
        print(f"{Fore.RED}추천할 종목이 없습니다.{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.GREEN}{'='*120}")
    print(f"{'추천 종목 목록':^120}")
    print(f"{'='*120}{Style.RESET_ALL}\n")
    
    print(f"{'순위':<5} {'종목':<15} {'현재가':>12} {'총점':>8} {'RSI':>8} {'MACD':>8} {'BB':>8} {'MA':>8} {'거래량':>8} {'BTC':>8} {'고래':>8} {'급등':>8}")
    print("-" * 140)
    
    for i, rec in enumerate(recommendations, 1):
        ticker = rec['ticker']
        current_price = rec.get('current_price', 0)
        total_score = rec['total_score']
        rsi_score = rec['rsi_score']
        macd_score = rec['macd_score']
        bb_score = rec['bb_score']
        ma_score = rec['ma_score']
        volume_score = rec['volume_score']
        btc_score = rec['btc_score']
        whale_score = rec.get('whale_score', 0.5)
        surge_score = rec.get('surge_score', 0.5)
        
        # 점수에 따라 색상 설정
        if total_score >= 0.7:
            color = Fore.GREEN
        elif total_score >= 0.5:
            color = Fore.YELLOW
        else:
            color = Fore.WHITE
        
        # 급등 점수에 따라 추가 강조
        surge_color = Fore.GREEN if surge_score >= 0.7 else (Fore.YELLOW if surge_score >= 0.5 else Fore.WHITE)
        
        print(f"{color}{i:<5} {ticker:<15} {current_price:>12,.0f} {total_score:>8.2f} {rsi_score:>8.2f} {macd_score:>8.2f} {bb_score:>8.2f} {ma_score:>8.2f} {volume_score:>8.2f} {btc_score:>8.2f} {whale_score:>8.2f} {surge_color}{surge_score:>8.2f}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}{'='*120}{Style.RESET_ALL}\n")

def print_risk_info(recommendations, risk_manager):
    """
    추천 종목의 리스크 정보를 출력합니다.
    
    Args:
        recommendations: 추천 종목 리스트
        risk_manager: RiskManager 인스턴스
    """
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{'추천 종목 리스크 정보':^120}")
    print(f"{'='*120}{Style.RESET_ALL}\n")
    
    print(f"{'종목':<15} {'현재가':>12} {'진입가':>12} {'손절가':>12} {'익절가':>12} {'손절%':>8} {'익절%':>8} {'리스크/보상':>12}")
    print("-" * 120)
    
    for rec in recommendations:
        ticker = rec['ticker']
        current_price = rec.get('current_price', 0)
        indicators = rec.get('indicators', {})
        
        risk_params = risk_manager.calculate_all_risk_parameters(
            current_price,
            indicators
        )
        
        entry_price = risk_params['entry_price']
        stop_loss = risk_params['stop_loss_price']
        take_profit = risk_params['take_profit_price']
        stop_loss_pct = risk_params['stop_loss_percent']
        take_profit_pct = risk_params['take_profit_percent']
        risk_reward = risk_params['risk_reward_ratio']
        
        print(f"{ticker:<15} {current_price:>12,.0f} {entry_price:>12,.0f} {stop_loss:>12,.0f} {take_profit:>12,.0f} {stop_loss_pct:>8.2f}% {take_profit_pct:>8.2f}% {risk_reward:>12.2f}")
    
    print(f"\n{Fore.CYAN}{'='*120}{Style.RESET_ALL}\n")

def main():
    """메인 함수"""
    print_header()
    
    # 클라이언트 및 분석기 초기화
    print(f"{Fore.YELLOW}시스템 초기화 중...{Style.RESET_ALL}")
    upbit_client = UpbitClient()
    trend_analyzer = TrendAnalyzer(upbit_client)
    whale_analyzer = WhaleAnalyzer(upbit_client)
    surge_analyzer = SurgeAnalyzer(upbit_client)
    recommender = StockRecommender(upbit_client, trend_analyzer, whale_analyzer, surge_analyzer)
    risk_manager = RiskManager()
    monitor = StockMonitor(upbit_client, risk_manager, whale_analyzer)
    
    try:
        # 추천 종목 조회
        print(f"\n{Fore.YELLOW}추천 종목 분석 중... (시간이 다소 걸릴 수 있습니다){Style.RESET_ALL}\n")
        recommendations = recommender.recommend_stocks(top_n=10)
        
        if not recommendations:
            print(f"{Fore.RED}추천할 종목을 찾을 수 없습니다.{Style.RESET_ALL}")
            return
        
        # 추천 종목 출력
        print_recommendations(recommendations)
        
        # 리스크 정보 출력
        print_risk_info(recommendations, risk_manager)
        
        # 모니터링 시작 여부 확인
        print(f"\n{Fore.CYAN}모니터링을 시작하시겠습니까? (y/n): {Style.RESET_ALL}", end="")
        choice = input().strip().lower()
        
        if choice == 'y' or choice == 'yes':
            # 상위 5개 종목만 모니터링에 추가
            top_stocks = recommendations[:5]
            print(f"\n{Fore.GREEN}상위 {len(top_stocks)}개 종목을 모니터링에 추가합니다...{Style.RESET_ALL}\n")
            
            for stock in top_stocks:
                monitor.add_stock(stock)
                print(f"{Fore.GREEN}✓ {stock['ticker']} 추가 완료{Style.RESET_ALL}")
            
            # 모니터링 시작
            monitor.start_monitoring()
        else:
            print(f"\n{Fore.YELLOW}모니터링을 시작하지 않습니다.{Style.RESET_ALL}")
            print(f"{Fore.CYAN}프로그램을 종료합니다.{Style.RESET_ALL}\n")
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}프로그램이 중단되었습니다.{Style.RESET_ALL}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}오류 발생: {e}{Style.RESET_ALL}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

