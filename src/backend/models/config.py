"""
Model configurations and settings.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from os import getenv
load_dotenv()

class ModelConfig(BaseModel):
    """Base configuration for language models."""
    name: str
    family: str
    version: str
    api_version: str
    parameters: Dict[str, Any]

# Common model configurations
azure_gpt4_config = ModelConfig(
    name=getenv("AZURE_OPENAI_MODEL"),
    family=getenv("AZURE_OPENAI_MODEL"),
    version=getenv("AZURE_OPENAI_API_VERSION"),
    api_version=getenv("AZURE_OPENAI_API_VERSION"),
    parameters={
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 4096,
        "context_window": 128000
    }
)
