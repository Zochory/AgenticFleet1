import asyncio
import logging
import os

from typing import Optional, AsyncGenerator, Dict, Any, List, Union, cast, TypeVar
from autogen_agentchat.ui import Console
from autogen_agentchat.agents import CodeExecutorAgent, AssistantAgent, BaseChatAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.messages import (
    BaseMessage,
    AgentEvent,
    ChatMessage,
    MultiModalMessage
)
from autogen_ext.agents.file_surfer import FileSurfer  # type: ignore
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent  # type: ignore
from autogen_ext.agents.web_surfer import MultimodalWebSurfer  # type: ignore
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor  # type: ignore
from autogen_ext.code_executors.azure import ACADynamicSessionsCodeExecutor  # type: ignore
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor  # type: ignore
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient  # type: ignore
from autogen_core import AgentId, AgentProxy, DefaultTopicId
from autogen_core import SingleThreadedAgentRuntime
from azure.identity import DefaultAzureCredential
import tempfile
from dotenv import load_dotenv
load_dotenv()

MessageType = Dict[str, Any]

class MagenticOneHelper:
    """
    A helper class to set up MagenticOne agents and manage interactions.
    It initializes a runtime, configures agents, and orchestrates tasks.
    """

    def __init__(
        self,
        logs_dir: Optional[str] = None,
        save_screenshots: bool = False,
        run_locally: bool = False
    ) -> None:
        """
        Args:
            logs_dir (optional): Directory to store logs and downloads.
            save_screenshots (optional): Whether to save screenshots of web pages.
            run_locally (optional): If True, agents run locally (e.g., Docker).
        """
        self.logs_dir = logs_dir or os.getcwd()
        self.runtime: Optional[SingleThreadedAgentRuntime] = None
        self.save_screenshots = save_screenshots
        self.run_locally = run_locally

        self.max_rounds: int = 50
        self.max_time: int = 25 * 60
        self.max_stalls_before_replan: int = 5
        self.return_final_answer: bool = True
        self.start_page: str = "https://www.bing.com"
        self.agents: List[BaseChatAgent] = []
        self.client: Optional[OpenAIChatCompletionClient] = None
        self.azure_credential: Optional[DefaultAzureCredential] = None

        # Prepare logs directory
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        # Initialize credential for remote execution scenarios
        try:
            cred = DefaultAzureCredential()
            self.azure_credential = cred
        except Exception as ex:
            logging.warning(f"Could not initialize Azure credentials: {ex}")

    async def initialize(self, agents: List[Dict[str, Any]]) -> None:
        """
        Initialize the MagenticOne system, setting up agents and runtime.

        Args:
            agents: A list of dictionaries defining agent configurations.
        """
        # Create the runtime
        self.runtime = SingleThreadedAgentRuntime()

        # Pull environment variables defined in .env
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        model = os.getenv("AZURE_OPENAI_MODEL")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        # Validate that all required environment variables are provided
        if not all([azure_endpoint, api_key, deployment, model, api_version]):
            raise ValueError("Missing required Azure OpenAI configuration in .env")

        self.client = AzureOpenAIChatCompletionClient(
            model=model,
            azure_deployment=deployment,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            azure_api_key=api_key,
            capabilities={
                "vision": True,
                "function_calling": True,
                "json_output": True
            },
            model_info={
                "name": model,
                "version": "2024-11-20",
                "context_window": 128000,
                "max_tokens": 4096,
                "supports": {
                    "vision": True,
                    "function_calling": True,
                    "json_output": True
                }
            }
        )

        # Set up agents
        self.agents = await self.setup_agents(agents, self.client, self.logs_dir)
        print("Agents setup complete!")

    async def setup_agents(
        self,
        agents: List[Dict[str, Any]],
        client: AzureOpenAIChatCompletionClient,
        logs_dir: str
    ) -> List[BaseChatAgent]:
        """
        Given a list of agent specifications, creates and returns the corresponding agents.

        Args:
            agents: A list of dictionaries describing each agent to be instantiated.
            client: The AzureOpenAIChatCompletionClient for text completions.
            logs_dir: The directory for logs and any downloaded artifacts.

        Returns:
            A list of initialized chat agents.
        """
        agent_list: List[BaseChatAgent] = []
        for agent in agents:
            try:
                agent_type = agent.get("type")
                agent_name = agent.get("name")

                # Example agent type / name checks
                if agent_type == "MagenticOne" and agent_name == "Coder":
                    coder = MagenticOneCoderAgent("Coder", model_client=client)
                    agent_list.append(coder)
                    print("Coder added!")

                elif agent_type == "MagenticOne" and agent_name == "Executor":
                    if self.run_locally:
                        code_executor = DockerCommandLineCodeExecutor(work_dir=logs_dir)
                        await code_executor.start()
                        executor = CodeExecutorAgent("Executor", code_executor=code_executor)
                    else:
                        pool_endpoint = os.getenv("POOL_MANAGEMENT_ENDPOINT")
                        if not pool_endpoint:
                            raise ValueError("POOL_MANAGEMENT_ENDPOINT environment variable is not set")
                        if not self.azure_credential:
                            raise ValueError("Azure credential not initialized properly")

                        # For remote (Azure ACA) execution
                        # Using a temporary directory for code artifacts
                        with tempfile.TemporaryDirectory() as temp_dir:
                            executor = CodeExecutorAgent(
                                "Executor",
                                code_executor=ACADynamicSessionsCodeExecutor(
                                    pool_management_endpoint=pool_endpoint,
                                    credential=self.azure_credential,
                                    work_dir=temp_dir
                                )
                            )
                    agent_list.append(executor)
                    print("Executor added!")

                elif agent_type == "MagenticOne" and agent_name == "WebSurfer":
                    web_surfer = MultimodalWebSurfer(
                        "WebSurfer", 
                        model_client=client,
                        vision=True
                    )
                    agent_list.append(web_surfer)
                    print("WebSurfer added!")

                elif agent_type == "MagenticOne" and agent_name == "FileSurfer":
                    file_surfer = FileSurfer("FileSurfer", model_client=client)
                    agent_list.append(file_surfer)
                    print("FileSurfer added!")

            except Exception as e:
                print(f"Failed to create agent {agent.get('name') or ''}: {e}")

        return agent_list

    async def main(self, task: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Orchestrates conversation between multiple agents to solve the specified task.

        Args:
            task: A non-empty string describing the objective or question.

        Returns:
            An async generator yielding conversation tokens or responses.
        """
        if not self.client:
            raise ValueError("Model client not initialized. Call initialize() first.")
        if not task or not isinstance(task, str):
            raise ValueError("Task must be a non-empty string")

        team = MagenticOneGroupChat(
            participants=self.agents,  # type: ignore
            model_client=self.client,
            max_turns=self.max_rounds,
            max_stalls=self.max_stalls_before_replan,
        )
        
        async for event in team.run_stream(task=task):
            try:
                # Handle different message types
                if isinstance(event, (BaseMessage, AgentEvent)):
                    source = getattr(event, 'source', 'system')
                    content = str(event.content) if hasattr(event, 'content') else str(event)
                    
                    # Create event output
                    output: Dict[str, Any] = {
                        "type": "message",
                        "source": source,
                        "content": content,
                    }
                    
                    # Add token usage if available
                    if hasattr(event, 'models_usage') and event.models_usage:
                        output["models_usage"] = event.models_usage._asdict()
                    
                    yield output
                else:
                    # Handle system messages and other events
                    yield {
                        "type": "message",
                        "source": "system",
                        "content": str(event)
                    }
            except Exception as e:
                logging.error(f"Error processing event: {str(e)}")
                yield {
                    "type": "error",
                    "source": "system",
                    "content": "An internal error has occurred."
                }