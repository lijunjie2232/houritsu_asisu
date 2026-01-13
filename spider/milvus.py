from pymilvus import AsyncMilvusClient


async def init_db():
    client = AsyncMilvusClient(
        uri="http://localhost:19530",
        token="root:Milvus"
    )

    client.create_user(user_name="root", password="aKJYNCrDY454")
