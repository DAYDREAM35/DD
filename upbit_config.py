# upbit_config.py

import ccxt

def create_upbit_api(access_key, secret_key):
    """Upbit API 객체를 생성하고, 필요한 설정을 적용하는 함수"""
    upbit = ccxt.upbit()
    upbit.apiKey = access_key
    upbit.secret = secret_key
    
    # 시장가 매수 주문에 가격을 요구하지 않도록 설정
    upbit.options['createMarketBuyOrderRequiresPrice'] = False
    
    return upbit
