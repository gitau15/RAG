import chromadb
from chromadb.config import Settings
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ChromaDBClient:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client with persistent storage"""
        try:
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"ChromaDB client initialized with path: {settings.CHROMA_DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {str(e)}")
            raise
    
    def get_client(self):
        """Get the ChromaDB client instance"""
        if not self.client:
            self._initialize_client()
        return self.client
    
    def create_collection(self, name: str, metadata: dict = None):
        """Create a new collection"""
        try:
            collection = self.client.create_collection(
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Created collection: {name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {str(e)}")
            raise
    
    def get_collection(self, name: str):
        """Get existing collection"""
        try:
            collection = self.client.get_collection(name=name)
            return collection
        except Exception as e:
            logger.error(f"Failed to get collection {name}: {str(e)}")
            raise
    
    def delete_collection(self, name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {str(e)}")
            raise
    
    def list_collections(self):
        """List all collections"""
        try:
            collections = self.client.list_collections()
            return [collection.name for collection in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            raise

# Global instance
chroma_client = ChromaDBClient()