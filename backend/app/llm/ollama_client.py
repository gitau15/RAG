import requests
import json
import logging
from typing import Dict, List, Optional, Generator
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use
        """
        self.base_url = base_url or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = 300  # 5 minutes timeout for generation
        
    def pull_model(self, model_name: str = None) -> bool:
        """
        Pull/download a model from Ollama registry
        
        Args:
            model_name: Name of the model to pull (defaults to configured model)
            
        Returns:
            Boolean indicating success
        """
        model = model_name or self.model
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {str(e)}")
            return False
    
    def list_models(self) -> List[Dict]:
        """
        List available models
        
        Returns:
            List of available models
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []
    
    def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """
        Generate text response from the model
        
        Args:
            prompt: User prompt
            system_prompt: System instruction/context
            **kwargs: Additional parameters for generation
            
        Returns:
            Generated text response
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                **kwargs
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            raise
    
    def generate_stream(self, prompt: str, system_prompt: str = "", **kwargs) -> Generator[str, None, None]:
        """
        Generate streaming text response from the model
        
        Args:
            prompt: User prompt
            system_prompt: System instruction/context
            **kwargs: Additional parameters for generation
            
        Yields:
            Chunks of generated text
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": True,
                **kwargs
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'response' in chunk:
                        yield chunk['response']
                        
        except Exception as e:
            logger.error(f"Failed to generate streaming response: {str(e)}")
            raise
    
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """
        Chat completion using message history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for generation
            
        Returns:
            Generated response
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                **kwargs
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except Exception as e:
            logger.error(f"Failed to generate chat response: {str(e)}")
            raise
    
    def chat_stream(self, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """
        Streaming chat completion using message history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for generation
            
        Yields:
            Chunks of generated text
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                **kwargs
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
                        
        except Exception as e:
            logger.error(f"Failed to generate streaming chat response: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """
        Check if Ollama service is healthy
        
        Returns:
            Boolean indicating health status
        """
        try:
            response = requests.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception:
            return False

# Global instance
ollama_client = OllamaClient()