'''
                                        NEWS MODULE 

'''


import requests

# # Fetch the latest sentiment data
url = "https://cryptolytical.netlify.app/api/sentiment"
response = requests.get(url)
sentiment_data = response.json()

# Display the sentiment scores
print(f"Current Sentiment Score: {sentiment_data['current_sentiment']}")
print(f"Comparative Sentiment Score: {sentiment_data['comparative_sentiment']}")
