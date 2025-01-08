"""
Model configurations and settings.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

class ModelConfig(BaseModel):
    """Base configuration for language models."""
    name: str
    family: str
    version: str
    api_version: str
    parameters: Dict[str, Any]

# Common model configurations
GPT4_CONFIG = ModelConfig(
    name="gpt-4o",
    family="gpt-4o",
    version="2024-08-06",
    api_version="2024-02-15-preview",
    parameters={
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 4096,
        "context_window": 128000
    }
)

class AzureConfig(BaseModel):
    """Azure-specific configuration."""
    deployment: str
    api_version: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None

# Default Azure configurations
AZURE_GPT4_CONFIG = AzureConfig(
    deployment="gpt-4o",
    api_version="2024-02-15-preview"
) 