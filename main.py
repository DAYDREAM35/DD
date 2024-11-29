import time
import threading
import tkinter as tk
from tkinter import messagebox
from upbit_config import create_upbit_api
from trade import golden_cross_strategy, opening_price_following_strategy, volatility_breakout_strategy

# GUI 클래스
class TradingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DDAT - 업비트 자동 매매")
        
        # 화면 중앙으로 실행
        window_width = 900
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_left = int(screen_width / 2 - window_width / 2)
        self.root.geometry(f'{window_width}x{window_height}+{position_left}+{position_top}')
        
        # GUI
        self.create_widgets()
        
        # 프로그램 상태
        self.running = False
        self.upbit = None
        self.symbol = None
        self.trade_method = None
        self.loss_limit = None
        self.access_key = None
        self.secret_key = None
        self.buy_executed = False
        self.last_buy_price = 0
    
    def create_widgets(self):
        # 엑세스 키와 시크릿 키 입력
        tk.Label(self.root, text="업비트 엑세스 키:",font=("Arial", 12)).pack()
        self.access_key_entry = tk.Entry(self.root, width=70)
        self.access_key_entry.pack()

        tk.Label(self.root, text="업비트 시크릿 키:",font=("Arial", 12)).pack()
        self.secret_key_entry = tk.Entry(self.root, show="*", width=70)
        self.secret_key_entry.pack()

        # 티커 입력
        tk.Label(self.root, text="감시할 코인 티커 (예: BTC):",font=("Arial", 12)).pack()
        self.ticker_entry = tk.Entry(self.root, width=70)
        self.ticker_entry.pack()

        # 매매 기법 선택 버튼
        tk.Label(self.root, text="매매 기법:",font=("Arial", 12)).pack()
        self.trade_method_var = tk.StringVar(value="120min")
        tk.Radiobutton(self.root, text="120분선 골든 크로스", variable=self.trade_method_var, value="120min", font=("Arial", 12)).pack()
        tk.Radiobutton(self.root, text="1분봉 시가 추적", variable=self.trade_method_var, value="1min", font=("Arial", 12)).pack()
        tk.Radiobutton(self.root, text="변동성 돌파", variable=self.trade_method_var, value="volatility", font=("Arial", 12)).pack()

        # 스탑로스 금액
        tk.Label(self.root, text="스탑로스 금액 (원화):",font=("Arial", 12)).pack()
        self.loss_limit_entry = tk.Entry(self.root, width=70)
        self.loss_limit_entry.pack()

        # 실행 및 로그 출력
        self.start_button = tk.Button(self.root, text="매매 시작", command=self.start_trading, width=20, height=2, font=("Arial", 14))
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(self.root, text="매매 중지", command=self.stop_trading, state=tk.DISABLED, width=20, height=2, font=("Arial", 14))
        self.stop_button.pack(pady=10)

        # 강제 매도 버튼 추가
        self.sell_button = tk.Button(self.root, text="강제 매도", command=self.sell_all_wallet, width=20, height=2, font=("Arial", 14))
        self.sell_button.pack(pady=10)

        self.log_text = tk.Text(self.root, state="disabled", height=20, width=100)
        self.log_text.pack()

    def log(self, message):
        
        self.log_text.config(state="normal")
        self.log_text.insert("end", "-" * 100 + "\n")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.insert("end", "-" * 100 + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def validate_inputs(self):
        
        self.access_key = self.access_key_entry.get().strip()
        self.secret_key = self.secret_key_entry.get().strip()
        self.symbol = self.ticker_entry.get().strip().upper()
        
        if not self.symbol.endswith("/KRW"):
            self.symbol = f"{self.symbol}/KRW"
            self.buy_executed = False
            self.last_buy_price = 0
            self.log(f"코인 {self.symbol} 설정 완료.")   
        
        self.trade_method = self.trade_method_var.get()
        try:
            self.loss_limit = float(self.loss_limit_entry.get().strip())
            if self.loss_limit <= 0:
                raise ValueError("스탑로스 금액은 0보다 커야 합니다.")
        except ValueError as e:
            self.log(f"입력 오류: {e}")
            return False
        return True

    def start_trading(self):
        
        if not self.validate_inputs():
            messagebox.showerror("입력 오류", "모든 입력을 확인하세요.")
            return

        try:
            self.upbit = create_upbit_api(self.access_key, self.secret_key)
            self.upbit.fetch_balance()
            self.log("API 인증 성공!")
        except Exception as e:
            self.log(f"API 인증 실패: {e}")
            return

        self.running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # 매매 루프
        self.trade_thread = threading.Thread(target=self.trade_loop)
        self.trade_thread.start()

    def stop_trading(self):
        
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log("매매 중지 요청됨.")

    def trade_loop(self):
        
        try:
            while self.running:
                balance = self.upbit.fetch_balance()
                total_assets = self.get_total_assets(balance)
                if total_assets <= self.loss_limit:
                    self.log(f"총 자산이 {self.loss_limit} KRW 이하로 하락. 매도 후 종료합니다.")
                    self.sell_all_wallet()
                    break

                ticker_data = self.upbit.fetch_ticker(self.symbol)
                current_price = ticker_data['last']
                coin_balance = balance['total'].get(self.symbol.split('/')[0], 0)
                krw_balance = balance['total'].get("KRW", 0)

                message = (
                    f"현재 {self.symbol} 시세: {current_price} KRW\n"
                    f"보유 {self.symbol} 코인 수량: {coin_balance}\n"
                    f"내 KRW 잔고: {krw_balance}\n"
                    f"매수 가격: {self.last_buy_price}"
                )
                self.log(message)

                if self.trade_method == "120min":
                    self.buy_executed, self.last_buy_price = golden_cross_strategy(
                        self.upbit, self.symbol, 0.0005, self.buy_executed, self.last_buy_price, self.log
                    )
                elif self.trade_method == "1min":
                    self.buy_executed, self.last_buy_price = opening_price_following_strategy(
                        self.upbit, self.symbol, 0.0005, self.buy_executed, self.last_buy_price, self.log
                    )
                elif self.trade_method == "volatility":
                    self.buy_executed, self.last_buy_price, _ = volatility_breakout_strategy(
                        self.upbit, self.symbol, 0.0005, self.buy_executed, self.last_buy_price, self.log
                    )

                time.sleep(0.3)

        except Exception as e:
            self.log(f"오류 발생: {e}")
        finally:
            self.stop_trading()

    def sell_all_wallet(self):
        
        try:
            balance = self.upbit.fetch_balance()
            for coin, amount in balance['total'].items():
                if coin != "KRW" and amount > 0:
                    ticker = f"{coin}/KRW"
                    self.upbit.create_market_sell_order(ticker, amount)
                    self.log(f"{ticker} 매도 완료.")
        except Exception as e:
            self.log(f"매도 중 오류 발생: {e}")

    def get_total_assets(self, balance):
        
        krw_balance = balance['total'].get("KRW", 0)
        coin_balance_value = sum(
            balance['total'][coin] * self.upbit.fetch_ticker(f"{coin}/KRW")['last']
            for coin in balance['total'] if coin != "KRW"
        )
        return krw_balance + coin_balance_value

# 프로그램 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()
