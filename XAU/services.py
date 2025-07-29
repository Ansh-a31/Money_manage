import certifi
import requests

def get_xauusd_price():
    url = "https://financialmodelingprep.com/api/v3/quotes/commodity?apikey=demo"
    response = requests.get(url, verify=certifi.where())
    if response.status_code == 200:
        data = response.json()
        gold_data = next((item for item in data if item["symbol"] == "XAUUSD"), None)
        if gold_data:
            print(f"XAU/USD: ${gold_data['price']}")
        else:
            print("Gold data not found in response.")
    else:
        print("Failed to get data:", response.status_code)

get_xauusd_price()
