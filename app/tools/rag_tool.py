from typing import Any, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.config.constants import DEFAULT_TOP_K
from app.core.db.vector_db import vector_db


class RAGSearchInput(BaseModel):
    query: str = Field(
        ..., description="The legal query to search for in Japanese law documents"
    )
    top_k: int = Field(
        DEFAULT_TOP_K, description="Number of relevant documents to retrieve"
    )


class RAGTool(BaseTool):
    name = "japanese_law_rag_search"
    description = "Search for relevant Japanese law documents using RAG (Retrieval Augmented Generation)"
    args_schema: Type[BaseModel] = RAGSearchInput

    def _run(self, query: str, top_k: int = DEFAULT_TOP_K) -> str:
        """
        Execute the RAG search for Japanese law documents
        """
        try:
            # In a real implementation, you would convert the query to an embedding
            # For now, we'll simulate the process
            import torch
            from transformers import AutoModel, AutoTokenizer

            # Initialize tokenizer and model for embedding (using a multilingual model)
            tokenizer = AutoTokenizer.from_pretrained(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            model = AutoModel.from_pretrained(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )

            # Tokenize and encode the query
            inputs = tokenizer(
                query, return_tensors="pt", padding=True, truncation=True
            )
            with torch.no_grad():
                outputs = model(**inputs)
                # Mean pooling to get sentence embedding
                query_embedding = (
                    outputs.last_hidden_state.mean(dim=1).numpy()[0].tolist()
                )

            # Search for similar documents in vector DB
            results = vector_db.search_similar_laws(query_embedding, top_k)

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "title": result["title"],
                        "content": (
                            result["content"][:500] + "..."
                            if len(result["content"]) > 500
                            else result["content"]
                        ),  # Truncate long content
                        "category": result["category"],
                        "date": result["date"],
                        "similarity_score": 1
                        - result["distance"],  # Convert distance to similarity
                    }
                )

            return str(formatted_results)

        except Exception as e:
            return f"Error during RAG search: {str(e)}"

    def _arun(self, query: str, top_k: int = DEFAULT_TOP_K) -> str:
        """
        Async version of the RAG search
        """
        raise NotImplementedError("RAGTool does not support async")


# Initialize the tool
rag_tool = RAGTool()
