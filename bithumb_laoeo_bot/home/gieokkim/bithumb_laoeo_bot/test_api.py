import json
import pybithumb

try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    api_key = config['BITHUMB_API_KEY']
    secret_key = config['BITHUMB_SECRET_KEY']
    
    bithumb = pybithumb.Bithumb(api_key, secret_key)
    raw_data = bithumb.get_balance("BTC")
    
    print("✅ 빗썸 서버 응답 원본 데이터:")
    print(raw_data)

except Exception as e:
    print(f"❌ 오류 발생: {e}")
