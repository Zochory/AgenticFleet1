import asyncio
from dataclasses import dataclass
import os

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from dotenv import load_dotenv
load_dotenv()


#Creatte token provider for Azure OpenAI    
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

#Create Azure OpenAI client
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="gpt-4o-mini",
    model="gpt-4o-mini",
    api_version="2024-05-01-preview",
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('AZURE_OPENAI_API_KEY')
)
#Create CogCache client
cogcache_client = OpenAIChatCompletionClient(
    base_url = "https://proxy-api.cogcache.com/v1/",
    api_key = os.getenv('COGCACHE_API_KEY'),
    model = "gpt-4o-mini-2024-07-18",
    # this is not needed here, if it's already set via environment variables
    default_headers = { 
        "Authorization": f"Bearer {os.getenv('COGCACHE_API_KEY')}",
    },
)

#Create message class
@dataclass
class Message:
    content: str

#Create simple agent class
class SimpleAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A simple agent")
        self._system_messages = [SystemMessage(content="You are a helpful AI assistant.")]
        self._model_client = cogcache_client

    @message_handler
    async def handle_user_message(self, message: Message, ctx: MessageContext) -> Message:
        # Prepare input to the chat completion model.
        user_message = UserMessage(content=message.content, source="user")
        response = await self._model_client.create(
            self._system_messages + [user_message], cancellation_token=ctx.cancellation_token
        )
        # Return with the model's response.
        assert isinstance(response.content, str)
        return Message(content=response.content)
    
    

async def main():
    runtime = SingleThreadedAgentRuntime()
    await SimpleAgent.register(
        runtime,
        "simple_agent",
        lambda: SimpleAgent()
    )
    runtime.start()
    message = Message("Hello, what are some fun things to do in Seattle?")
    response = await runtime.send_message(message, AgentId("simple_agent", "default"))
    print(response.content)
    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())