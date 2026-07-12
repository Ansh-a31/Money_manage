from pymongo import MongoClient
from logger import logger
from datetime import datetime


# Status: Working properly.
def push(doc=None,collection_name= None):
# Connect to the local MongoDB server
    # amazonq-ignore-next-line
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Money_Manage']

    # Choose collection (similar to a table in SQL)
    collection = db[collection_name]

    # Insert a document
    # doc = {"name": "Alice", "age": 25}
    insert_result = collection.insert_one(doc)
    logger.info(f"[{datetime.now()}]: [push_mongo] Inserted document id: {insert_result.inserted_id}")

    # # Find a document
    # result = collection.find_one({"name": "Alice"})
    # print(result)


# Status: Working properly.
def fetch_last(query=None, collection_name= None):
    # Return latest created object.
    # amazonq-ignore-next-line
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Money_Manage']

    # Choose collection (similar to a table in SQL)
    collection = db[collection_name]
    # amazonq-ignore-next-line
    insert_result = collection.find(query).sort({"created_at":-1})
    return list(insert_result)


# Status: Working properly.
def push_many(doc=None,collection='week_data'):
    """
    Push many documents to MongoDB.
    """
    # Connect to the local MongoDB server
    # amazonq-ignore-next-line
    client = MongoClient('mongodb://localhost:27017/')

    # Choose database (will create if it doesn't exist)
    db = client['Money_Manage']

    db_collection = db[collection]

    insert_result = db_collection.insert_many(doc)
    logger.info(f"[{datetime.now()}] [push_many]: Inserted document in collection: {collection}.")


# Status: Working properly.
def delete(doc=None, collection='week_data'):
    """
    Deletes many documents from MongoDB.
    """
    # Connect to the local MongoDB server
    # amazonq-ignore-next-line
    client = MongoClient('mongodb://localhost:27017/')
    # Choose database (will create if it doesn't exist)
    db = client['Money_Manage']

    db_collection = db[collection]

    # Delete documents
    delete_result = db_collection.delete_many({})
    logger.info(f"[{datetime.now()}]: [delete_data_mongo] Deleted {delete_result.deleted_count} documents from MongoDB collection: {collection}")


def update(query=None, update_doc=None, collection_name=None):
    client = MongoClient('mongodb://localhost:27017/')
    db = client['Money_Manage']
    collection = db[collection_name]
    result = collection.update_one(query, {"$set": update_doc})
    logger.info(f"[{datetime.now()}]: [update_mongo] Matched: {result.matched_count} | Modified: {result.modified_count}")
