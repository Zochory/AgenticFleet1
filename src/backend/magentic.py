"""
MagenticOne team configuration and execution.
"""

import asyncio
import os
from dotenv import load_dotenv
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer

from models import (
    create_azure_client,
    GPT4_CONFIG,
    AZURE_GPT4_CONFIG
)
from models.logging import team_logger, system_logger

load_dotenv()

class MagenticTeam:
    """Team of agents for executing tasks."""
    
    def __init__(self):
        """Initialize the team with configured agents."""
        # Create model client using our configuration
        self.client = create_azure_client(
            model_config=GPT4_CONFIG,
            azure_config=AZURE_GPT4_CONFIG
        )
        
        # Initialize agents
        self.agents = []
        
        # File handling agent
        fs = FileSurfer(
            "FileSurfer",
            model_client=self.client
        )
        self.agents.append(fs)
        
        # Web browsing agent (optional)
        try:
            ws = MultimodalWebSurfer(
                "WebSurfer",
                model_client=self.client
            )
            self.agents.append(ws)
        except Exception as e:
            system_logger.warning(
                "agent_init",
                "WebSurfer agent not available",
                {"error": str(e)}
            )
        
        # Code generation agent
        coder = MagenticOneCoderAgent(
            "Coder",
            model_client=self.client
        )
        self.agents.append(coder)
        
        # Create team
        self.team = MagenticOneGroupChat(
            self.agents,
            model_client=self.client
        )
        
        team_logger.info(
            "team_init",
            "Team initialized successfully",
            {"agents": [agent.name for agent in self.agents]}
        )
    
    async def run(self, task: str):
        """Run a task with the team."""
        team_logger.log_task_start(task, [agent.name for agent in self.agents])
        
        try:
            async for event in self.team.run_stream(task=task):
                # Get source and content if available
                source = getattr(event, 'source', 'System')
                content = getattr(event, 'content', str(event))
                
                # Log the event
                if hasattr(event, 'source') and hasattr(event, 'content'):
                    team_logger.log_agent_message(source, "team", content)
                else:
                    team_logger.debug("event", str(event))
                
                # Print for console output
                print(f"{source}: {content}")
            
            team_logger.log_task_complete(task, True)
            
        except Exception as e:
            team_logger.error(
                "task_error",
                f"Error executing task: {task}",
                {"error": str(e)}
            )
            team_logger.log_task_complete(task, False, {"error": str(e)})
            raise

async def main():
    """Main entry point."""
    system_logger.info("startup", "Starting MagenticTeam application")
    
    try:
        team = MagenticTeam()
        
        while True:
            try:
                task = input("Enter your task: ")
                if not task:
                    continue
                    
                if task.lower() in ['exit', 'quit']:
                    system_logger.info("shutdown", "User requested exit")
                    break
                    
                await team.run(task)
                
            except KeyboardInterrupt:
                system_logger.info("shutdown", "User interrupted execution")
                break
            except Exception as e:
                system_logger.error(
                    "task_error",
                    "Error in task execution",
                    {"error": str(e)}
                )
                print(f"Error: {e}")
                continue
    
    except Exception as e:
        system_logger.error(
            "startup_error",
            "Failed to initialize application",
            {"error": str(e)}
        )
        raise

if __name__ == "__main__":
    asyncio.run(main())
