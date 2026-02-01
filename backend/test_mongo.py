from dotenv import load_dotenv
load_dotenv()
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    collections = await db.list_collection_names()
    print('MongoDB connected! Collections:', collections)
    client.close()

asyncio.run(test())
