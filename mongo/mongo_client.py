from pymongo import MongoClient
from logger import logger

def mongo_client(doc=None):
# Connect to the local MongoDB server
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Scrapper']

    # Choose collection (similar to a table in SQL)
    collection = db['email_logs']

    # Insert a document
    # doc = {"name": "Alice", "age": 25}
    insert_result = collection.insert_one(doc)
    logger.info(f"Inserted document id: {insert_result.inserted_id}")

    # # Find a document
    # result = collection.find_one({"name": "Alice"})
    # print(result)

