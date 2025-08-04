from pymongo import MongoClient
from logger import logger


# Status: Working properly.
def push_mongo(doc=None):
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


# Status: Working properly.
def fetch_last():
    # Return latest created object.
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Scrapper']

    # Choose collection (similar to a table in SQL)
    collection = db['email_logs']
    insert_result = collection.find().sort({"created_at":-1})
    return list(insert_result)


# Status: Working properly.
def push_many(doc=None,collection='week_data'):
    """
    Push many documents to MongoDB.
    """
# Connect to the local MongoDB server
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Scrapper']

    # Choose collection (similar to a table in SQL)
    db_collection = db[collection]

    # Insert a document
    # doc = {"name": "Alice", "age": 25}
    insert_result = db_collection.insert_many(doc)
    logger.info(f"Inserted document id: {insert_result.inserted_id}")