"""Ollaborate: small, typed multi-agent orchestration for Ollama."""

from .agent import Agent
from .events import Event, EventHandler
from .team import RunResult, Team

__all__ = ["Agent", "Event", "EventHandler", "RunResult", "Team"]
__version__ = "0.1.0"
