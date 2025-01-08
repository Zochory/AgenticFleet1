import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

def test_azure_connection():
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    if not all([api_key, api_version, azure_endpoint, deployment_name]):
        raise ValueError("Missing required Azure OpenAI environment variables")

    # Type assertions for mypy
    assert api_key is not None
    assert api_version is not None
    assert azure_endpoint is not None
    assert deployment_name is not None

    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )

    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print("Connection successful!")
        print(response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_azure_connection() 