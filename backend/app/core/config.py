from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Universal RAG Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    
    # ChromaDB Settings
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000
    CHROMA_DB_PATH: str = "/home/app/chroma_db"
    
    # Ollama Settings
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral:7b"
    
    # Application Settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list = [".pdf", ".txt", ".doc", ".docx"]
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    
    # Performance Settings
    MAX_RESPONSE_TIME: float = 8.0  # Maximum response time in seconds
    MAX_QUERY_K: int = 6  # Maximum number of results to retrieve
    RETRIEVAL_TIMEOUT: float = 5.0  # Timeout for retrieval operations
    GENERATION_TIMEOUT: float = 6.0  # Timeout for generation operations
    EMBEDDING_TIMEOUT: float = 30.0  # Timeout for embedding operations
    CONCURRENT_REQUESTS_LIMIT: int = 10  # Maximum concurrent requests
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()