"""
백테스팅 실행 파일
과거 데이터로 전략을 검증합니다.
"""
import sys
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from upbit_client import UpbitClient
from backtester import Backtester

# colorama 초기화
init(autoreset=True)

def print_backtest_results(result: dict):
    """
    백테스팅 결과를 출력합니다.
    
    Args:
        result: 백테스팅 결과 딕셔너리
    """
    if 'error' in result:
        print(f"{Fore.RED}오류: {result['error']}{Style.RESET_ALL}")
        return
    
    ticker = result['ticker']
    start_date = result['start_date']
    end_date = result['end_date']
    initial_capital = result['initial_capital']
    final_value = result['final_value']
    total_return = result['total_return']
    total_trades = result['total_trades']
    win_rate = result['win_rate']
    total_profit = result['total_profit']
    
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{ticker} 백테스팅 결과")
    print(f"{'='*100}{Style.RESET_ALL}\n")
    
    print(f"기간: {start_date} ~ {end_date}")
    print(f"초기 자본: {initial_capital:,.0f}원")
    print(f"최종 자본: {final_value:,.0f}원")
    
    # 수익률 색상
    if total_return > 0:
        return_color = Fore.GREEN
    elif total_return < 0:
        return_color = Fore.RED
    else:
        return_color = Fore.WHITE
    
    print(f"총 수익률: {return_color}{total_return:+.2f}%{Style.RESET_ALL}")
    print(f"총 거래 횟수: {total_trades}회")
    print(f"승률: {win_rate:.2f}%")
    print(f"총 수익: {total_profit:,.0f}원")
    
    # 거래 내역
    if result['trades']:
        print(f"\n{Fore.YELLOW}거래 내역:{Style.RESET_ALL}")
        print(f"{'진입일':<12} {'청산일':<12} {'진입가':>12} {'청산가':>12} {'수익률':>10} {'사유':>15}")
        print("-" * 85)
        
        for trade in result['trades']:
            profit_color = Fore.GREEN if trade['profit'] > 0 else (Fore.RED if trade['profit'] < 0 else Fore.WHITE)
            print(f"{str(trade['entry_date']):<12} {str(trade['exit_date']):<12} "
                  f"{trade['entry_price']:>12,.0f} {trade['exit_price']:>12,.0f} "
                  f"{profit_color}{trade['profit_percent']:>+9.2f}%{Style.RESET_ALL} {trade.get('exit_reason', ''):>15}")
    
    print(f"\n{Fore.CYAN}{'='*100}{Style.RESET_ALL}\n")

def main():
    """메인 함수"""
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{'백테스팅 시스템':^100}")
    print(f"{'='*100}{Style.RESET_ALL}\n")
    
    # 백테스터 초기화
    upbit_client = UpbitClient()
    backtester = Backtester(upbit_client)
    
    # 백테스팅 기간 설정
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")  # 최근 3개월
    
    print(f"백테스팅 기간: {start_date} ~ {end_date}")
    print(f"테스트할 종목을 입력하세요 (예: KRW-ETH, 여러 개는 쉼표로 구분): ", end="")
    tickers_input = input().strip()
    
    if not tickers_input:
        print(f"{Fore.RED}종목을 입력해주세요.{Style.RESET_ALL}")
        return
    
    tickers = [t.strip() for t in tickers_input.split(',')]
    
    print(f"\n{Fore.YELLOW}백테스팅을 시작합니다...{Style.RESET_ALL}\n")
    
    # 각 종목별 백테스팅
    for ticker in tickers:
        try:
            result = backtester.backtest_strategy(
                ticker,
                start_date,
                end_date,
                initial_capital=10000000  # 1천만원
            )
            print_backtest_results(result)
        except Exception as e:
            print(f"{Fore.RED}{ticker} 백테스팅 오류: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

