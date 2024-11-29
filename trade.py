import numpy as np

FEE_RATE = 0.0005

def calculate_sma(data, window):
    """단순 이동 평균(SMA) 계산"""
    return np.mean(data[-window:])

def get_balance(upbit, symbol):
    """현재 잔고 확인 함수"""
    try:
        balance = upbit.fetch_balance()
        krw_balance = balance['total'].get('KRW', 0)
        coin_balance = balance['total'].get(symbol.split('/')[0], 0)
        return krw_balance, coin_balance
    except Exception as e:
        return 0, 0

def place_buy_order(upbit, symbol, amount, log):
    """시장가 매수 주문 실행"""
    try:
        order = upbit.create_market_buy_order(symbol, amount)
        log(f"매수 주문 완료: {symbol}, 금액: {amount:,.2f} KRW")
        return order
    except Exception as e:
        log(f"매수 주문 오류: {e}")
        return None

def place_sell_order(upbit, symbol, amount, log):
    """시장가 매도 주문 실행"""
    try:
        order = upbit.create_market_sell_order(symbol, amount)
        log(f"매도 주문 완료: {symbol}, 수량: {amount:,.10f}")
        return order
    except Exception as e:
        log(f"매도 주문 오류: {e}")
        return None

def golden_cross_strategy(upbit, symbol, fee_rate, buy_executed, last_buy_price, log):
    """골든 크로스 전략"""
    try:
        ohlcv = upbit.fetch_ohlcv(symbol, timeframe='1m', limit=120)
        sma_120 = calculate_sma([candle[4] for candle in ohlcv], 120)

        ticker = upbit.fetch_ticker(symbol)
        current_price = ticker['last']
        krw_balance, coin_balance = get_balance(upbit, symbol)

        if not buy_executed and current_price >= sma_120 * 1.003:
            available_krw_for_buy = krw_balance * (1 - fee_rate)
            place_buy_order(upbit, symbol, available_krw_for_buy, log)
            return True, current_price

        if buy_executed and current_price < sma_120 and current_price < sma_120 * 0.99:
            place_sell_order(upbit, symbol, coin_balance, log)
            return False, 0

        return buy_executed, last_buy_price
    except Exception as e:
        log(f"오류 발생 (골든 크로스): {e}")
        return buy_executed, last_buy_price

def opening_price_following_strategy(upbit, symbol, fee_rate, buy_executed, last_buy_price, log):
    """1분봉 시가 추적 전략"""
    try:
        ohlcv = upbit.fetch_ohlcv(symbol, timeframe='1m', limit=2)
        last_open_price = ohlcv[-2][1] if len(ohlcv) > 1 else 0

        ticker = upbit.fetch_ticker(symbol)
        current_price = ticker['last']
        krw_balance, coin_balance = get_balance(upbit, symbol)

        if not buy_executed and current_price > last_open_price:
            available_krw_for_buy = krw_balance * (1 - fee_rate)
            place_buy_order(upbit, symbol, available_krw_for_buy, log)
            return True, current_price

        if buy_executed and (current_price < last_buy_price * 0.994 or current_price > last_buy_price * 1.012):
            place_sell_order(upbit, symbol, coin_balance, log)
            return False, 0

        return buy_executed, last_buy_price
    except Exception as e:
        log(f"오류 발생 (1분봉 시가 추적): {e}")
        return buy_executed, last_buy_price

def volatility_breakout_strategy(upbit, symbol, fee_rate, buy_executed, last_buy_price, log):
    """변동성 돌파 전략"""
    try:
        ohlcv = upbit.fetch_ohlcv(symbol, timeframe='1d', limit=2)
        if len(ohlcv) < 2:
            log("전일 데이터가 부족합니다. 전략을 실행할 수 없습니다.")
            return buy_executed, last_buy_price, False

        prev_day = ohlcv[-2]
        prev_close = prev_day[4]
        prev_high = prev_day[2]
        prev_low = prev_day[3]
        volatility_range = (prev_high - prev_low) / 2
        breakout_price = prev_close + volatility_range

        ticker = upbit.fetch_ticker(symbol)
        current_price = ticker['last']
        krw_balance, coin_balance = get_balance(upbit, symbol)

        if not buy_executed and current_price >= breakout_price:
            available_krw_for_buy = krw_balance * (1 - fee_rate)
            place_buy_order(upbit, symbol, available_krw_for_buy, log)
            return True, current_price, True

        if buy_executed and current_price < last_buy_price * 0.99:
            place_sell_order(upbit, symbol, coin_balance, log)
            return False, 0, True

        return buy_executed, last_buy_price, True
    except Exception as e:
        log(f"오류 발생 (변동성 돌파 전략): {e}")
        return buy_executed, last_buy_price, False
