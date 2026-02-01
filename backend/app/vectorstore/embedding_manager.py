from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
import logging

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding manager with sentence transformer model
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Embedding model '{self.model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model '{self.model_name}': {str(e)}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self.model.encode(texts, show_progress_bar=True)
            # Convert to list format for ChromaDB
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Failed to embed documents: {str(e)}")
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector
        """
        try:
            embedding = self.model.encode([query])[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to embed query: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors
        
        Returns:
            Dimension of embedding vectors
        """
        if self.model:
            return self.model.get_sentence_embedding_dimension()
        return 0

# Global instance
embedding_manager = EmbeddingManager()