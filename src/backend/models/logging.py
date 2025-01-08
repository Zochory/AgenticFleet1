"""
Logging configuration and utilities for AutoGen agents.

This module provides structured logging capabilities for agent activities,
team coordination, and system events. All timestamps are in UTC.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S %z'
)

class LogEvent(BaseModel):
    """Structure for log events."""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the event"
    )
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, DEBUG)")
    event_type: str = Field(..., description="Type of event being logged")
    agent: Optional[str] = Field(default=None, description="Agent that generated the event")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional event details")

    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class AgentLogger:
    """Logger for agent activities and events."""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        """
        Initialize logger for an agent.
        
        Args:
            name: Name of the agent or component
            log_file: Path to log file. If None, logs to stdout
        """
        self.logger = logging.getLogger(name)
        self.name = name
        
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter(
                    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S %z'
                )
            )
            self.logger.addHandler(handler)
    
    def _create_event(
        self,
        level: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> LogEvent:
        """Create a structured log event."""
        return LogEvent(
            level=level,
            event_type=event_type,
            agent=self.name,
            message=message,
            details=details
        )
    
    def _log(self, level: int, event: LogEvent):
        """Log an event at specified level."""
        self.logger.log(level, json.dumps(event.model_dump(), indent=None, separators=(',', ':')))
    
    def info(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log an info level event."""
        event = self._create_event("INFO", event_type, message, details)
        self._log(logging.INFO, event)
    
    def warning(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a warning level event."""
        event = self._create_event("WARNING", event_type, message, details)
        self._log(logging.WARNING, event)
    
    def error(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log an error level event."""
        event = self._create_event("ERROR", event_type, message, details)
        self._log(logging.ERROR, event)
    
    def debug(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log a debug level event."""
        event = self._create_event("DEBUG", event_type, message, details)
        self._log(logging.DEBUG, event)

class TeamLogger(AgentLogger):
    """Logger for team-level events and coordination."""
    
    def log_task_start(self, task: str, agents: list[str]):
        """Log task initiation."""
        self.info(
            "task_start",
            f"Starting task execution: {task}",
            {
                "task": task,
                "agents": agents,
                "start_time": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_task_complete(self, task: str, success: bool, result: Optional[Dict[str, Any]] = None):
        """Log task completion."""
        self.info(
            "task_complete",
            f"Task completed: {task}",
            {
                "task": task,
                "success": success,
                "result": result,
                "end_time": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def log_agent_message(self, source: str, target: str, message: str):
        """Log inter-agent communication."""
        self.debug(
            "agent_message",
            f"Message from {source} to {target}",
            {
                "source": source,
                "target": target,
                "message": message,
                "time": datetime.now(timezone.utc).isoformat()
            }
        )

# Create default loggers
team_logger = TeamLogger("MagenticTeam")
system_logger = AgentLogger("System") 