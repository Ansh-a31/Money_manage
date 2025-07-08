import requests

API_KEY = "your_api_key"
url = f"https://www.alphavantage.co/query?function=COMMODITY_EXCHANGE_RATE&from_currency=XAU&to_currency=USD&apikey={API_KEY}"
response = requests.get(url)
data = response.json()
price = data["Realtime Commodity Exchange Rate"]["5. Exchange Rate"]
print(f"Gold price: {price} USD")
