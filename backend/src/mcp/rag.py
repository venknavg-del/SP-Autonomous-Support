import os
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

class ChromaRAGService:
    """
    Knowledge & RAG Layer Service using ChromaDB.
    Indexes markdown runbooks from data/runbooks/ directory
    and provides semantic search using sentence-transformers.
    """
    
    def __init__(self, data_dir: str = "data/runbooks"):
        self.data_dir = data_dir
        # Initialize local ChromaDB client
        self.chroma_client = chromadb.Client()
        
        # Use a lightweight local embedding model
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="sp_support_runbooks",
            embedding_function=self.embedding_fn
        )
        
        # Simulated Vector Store Data for historical tickets (still mock for now)
        self.historical_tickets = [
            {
                "id": "SP-101",
                "issue": "NullPointerException in PaymentService during checkout",
                "resolution": "Added explicit null check for user balance. Merged PR #4052."
            },
            {
                "id": "SP-204",
                "issue": "Application unresponsive. DB connection pool exhausted.",
                "resolution": "Increased max connections in terraform config and restarted app cluster."
            }
        ]
        
        # Auto-index runbooks on startup
        self._index_runbooks()

    def _index_runbooks(self):
        """Reads markdown files from data_dir and adds them to ChromaDB."""
        if not os.path.exists(self.data_dir):
            print(f"[RAG] Warning: Runbooks directory not found: {self.data_dir}")
            return
            
        print("[RAG] Indexing runbooks into ChromaDB...")
        documents = []
        metadatas = []
        ids = []
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(self.data_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Extract a title (first line if starts with #)
                title = filename
                lines = content.split("\n")
                if lines and lines[0].startswith("# "):
                    title = lines[0].replace("# ", "").strip()
                    
                documents.append(content)
                metadatas.append({"title": title, "source": filename})
                ids.append(filename)
                
        if documents:
            # Add or update the documents in ChromaDB
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[RAG] Successfully indexed {len(documents)} runbooks.")
        else:
            print("[RAG] No runbooks found to index.")

    async def search_similar_tickets(self, query: str) -> List[Dict[str, Any]]:
        """Simulates a semantic search over historical tickets."""
        print(f"[RAG] Searching historical tickets for '{query}'...")
        # Mock logic based on keywords for historical tickets
        if "null" in query.lower() or "payment" in query.lower():
            return [self.historical_tickets[0]]
        elif "down" in query.lower() or "pool" in query.lower() or "connection" in query.lower():
            return [self.historical_tickets[1]]
        return []

    async def retrieve_runbooks(self, query: str, n_results: int = 1) -> List[Dict[str, Any]]:
        """Retrieves relevant runbooks using vector similarity search."""
        print(f"[RAG] Retrieving relevant runbooks for '{query}'...")
        
        if self.collection.count() == 0:
            return []
            
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        runbooks = []
        if results and results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                doc_content = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                runbooks.append({
                    "title": metadata.get("title", "Runbook"),
                    "filename": metadata.get("source", "unknown"),
                    "content": doc_content
                })
                print(f"[RAG] Match found: {metadata.get('title')}")
                
        return runbooks

# Singleton instance for the app
rag_service = ChromaRAGService()
