import pymongo
import os
from pathlib import Path
from dotenv import load_dotenv

# Load dotenv
env_path = Path('.')/'.env'
load_dotenv(dotenv_path=env_path)


mongoClient = pymongo.MongoClient(os.environ['MONGO_URL'])
db = mongoClient["coffee"]
collection = db["users"]

mydict = {"_id": "asdkljaslkdjalskd", "name": "John", "address": "Highway 37"}

x = collection.insert_one(mydict)
