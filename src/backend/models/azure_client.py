"""
Azure OpenAI model client configuration for AutoGen.
"""

import os
from typing import Optional
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from dotenv import load_dotenv
from .config import ModelConfig, AzureConfig, GPT4_CONFIG, AZURE_GPT4_CONFIG

load_dotenv()

def create_azure_client(
    model_config: ModelConfig = GPT4_CONFIG,
    azure_config: AzureConfig = AZURE_GPT4_CONFIG,
) -> AzureOpenAIChatCompletionClient:
    """
    Create an Azure OpenAI client with the specified configuration.

    Args:
        model_config (ModelConfig): The model configuration.
        azure_config (AzureConfig): The Azure deployment configuration.

    Returns:
        AzureOpenAIChatCompletionClient: Configured Azure OpenAI client.

    Raises:
        ValueError: If required environment variables are not set.
    """
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not azure_endpoint or not api_key:
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY environment variable is not set"
        )

    model_name = f"{model_config.name}-{model_config.version}"
    
    return AzureOpenAIChatCompletionClient(
        model=model_name,
        azure_deployment=azure_config.deployment,
        api_version=azure_config.api_version,
        azure_endpoint=azure_endpoint,  # type: ignore
        api_key=api_key,  # type: ignore
        **model_config.parameters
    ) 