#!/usr/bin/env python3
"""
Script to setup Ollama with Mistral 7B model
This script pulls the required model and verifies the setup
"""

import sys
import time
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.llm.ollama_client import OllamaClient
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_ollama():
    """Setup Ollama with Mistral 7B model"""
    print("🔧 Setting up Ollama with Mistral 7B model...")
    
    client = OllamaClient()
    
    # Check if Ollama is running
    print("Checking Ollama service health...")
    if not client.health_check():
        print("❌ Ollama service is not accessible!")
        print(f"Please ensure Ollama is running at: {settings.OLLAMA_HOST}")
        return False
    
    print("✅ Ollama service is running")
    
    # List existing models
    print("\nExisting models:")
    models = client.list_models()
    for model in models:
        print(f"  - {model['name']}")
    
    # Check if Mistral model exists
    mistral_model = "mistral:7b"
    model_exists = any(mistral_model in model['name'] for model in models)
    
    if model_exists:
        print(f"\n✅ {mistral_model} model already exists")
    else:
        print(f"\n📥 Pulling {mistral_model} model (this may take several minutes)...")
        print("This will download approximately 4-5GB of data")
        
        start_time = time.time()
        success = client.pull_model(mistral_model)
        end_time = time.time()
        
        if success:
            print(f"✅ Successfully downloaded {mistral_model}")
            print(f"Download time: {end_time - start_time:.2f} seconds")
        else:
            print(f"❌ Failed to download {mistral_model}")
            return False
    
    # Test the model
    print("\n🧪 Testing model with a simple prompt...")
    try:
        test_prompt = "Briefly explain what artificial intelligence is in one sentence."
        response = client.generate(test_prompt, max_tokens=50)
        print(f"Test response: {response.strip()}")
        print("✅ Model is working correctly")
        return True
    except Exception as e:
        print(f"❌ Model test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = setup_ollama()
    if success:
        print("\n🎉 Ollama setup completed successfully!")
        print("You can now use the RAG platform with local LLM inference.")
    else:
        print("\n💥 Ollama setup failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)