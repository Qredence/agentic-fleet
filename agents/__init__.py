"""
AgenticFleet Agents Package
===========================

This package contains all specialized agents for the AgenticFleet multi-agent system.

Agents:
    - orchestrator_agent: Main coordinator for task delegation and planning
    - researcher_agent: Information gathering and web search specialist
    - coder_agent: Code writing, execution, and validation specialist
    - analyst_agent: Data analysis and insight generation specialist

Usage:
    from agents.orchestrator_agent.agent import create_orchestrator_agent
    from agents.researcher_agent.agent import create_researcher_agent
    from agents.coder_agent.agent import create_coder_agent
    from agents.analyst_agent.agent import create_analyst_agent

    orchestrator = create_orchestrator_agent()
    researcher = create_researcher_agent()
    coder = create_coder_agent()
    analyst = create_analyst_agent()
"""

from agents.analyst_agent.agent import create_analyst_agent
from agents.coder_agent.agent import create_coder_agent
from agents.orchestrator_agent.agent import create_orchestrator_agent
from agents.researcher_agent.agent import create_researcher_agent

__all__ = [
    "create_orchestrator_agent",
    "create_researcher_agent",
    "create_coder_agent",
    "create_analyst_agent",
]
