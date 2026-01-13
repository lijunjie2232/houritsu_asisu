from typing import Any, Dict, List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config.constants import DEFAULT_TOP_K
from app.config.settings import settings


class VectorDBManager:
    def __init__(self):
        self.collection_name = settings.COLLECTION_NAME
        self.connect()

    def connect(self):
        """Connect to Milvus server"""
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            user=settings.MILVUS_USER,
            password=settings.MILVUS_PASSWORD,
        )

    def create_collection_if_not_exists(self):
        """Create collection if it doesn't exist"""
        if not utility.has_collection(self.collection_name):
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                ),
                FieldSchema(
                    name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536
                ),  # Assuming OpenAI embeddings
                FieldSchema(name="law_title", dtype=DataType.VARCHAR, max_length=500),
                FieldSchema(
                    name="law_content", dtype=DataType.VARCHAR, max_length=65535
                ),
                FieldSchema(
                    name="law_category", dtype=DataType.VARCHAR, max_length=100
                ),
                FieldSchema(name="law_date", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]

            schema = CollectionSchema(fields, description="Japanese Laws Collection")
            collection = Collection(name=self.collection_name, schema=schema)

            # Create index
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 1024},
            }
            collection.create_index(field_name="embedding", index_params=index_params)

            return collection
        else:
            return Collection(self.collection_name)

    def insert_law_document(self, embedding: List[float], law_data: Dict[str, Any]):
        """Insert a law document into the collection"""
        collection = self.create_collection_if_not_exists()

        data = [
            [embedding],
            [law_data.get("title", "")],
            [law_data.get("content", "")],
            [law_data.get("category", "")],
            [law_data.get("date", "")],
            [law_data.get("metadata", {})],
        ]

        result = collection.insert(data)
        collection.load()  # Load collection into memory for searching

        return result.insert_ids

    def search_similar_laws(
        self, query_embedding: List[float], top_k: int = DEFAULT_TOP_K
    ) -> List[Dict[str, Any]]:
        """Search for similar law documents based on embedding similarity"""
        collection = Collection(self.collection_name)
        collection.load()  # Ensure collection is loaded

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=[
                "law_title",
                "law_content",
                "law_category",
                "law_date",
                "metadata",
            ],
        )

        # Format results
        formatted_results = []
        for hit in results[0]:  # Results for first (and only) query
            formatted_results.append(
                {
                    "id": hit.id,
                    "distance": hit.distance,
                    "title": hit.entity.get("law_title"),
                    "content": hit.entity.get("law_content"),
                    "category": hit.entity.get("law_category"),
                    "date": hit.entity.get("law_date"),
                    "metadata": hit.entity.get("metadata"),
                }
            )

        return formatted_results

    def delete_collection(self):
        """Delete the entire collection (use carefully!)"""
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)


# Global instance
vector_db = VectorDBManager()
