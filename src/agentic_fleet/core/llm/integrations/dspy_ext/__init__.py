"""
DSPy Extension for AgenticFleet

This module provides DSPy integration with Azure OpenAI mini models (o3-mini and gpt-4o-mini)
for enhanced reasoning capabilities within the Autogen framework.
"""

from .compiler import AzureMiniCompiler
from .modules import ChainOfThoughtModule, ReflectionModule
from .reasoning import DSPyReasoningAgent

__all__ = [
    "AzureMiniCompiler",
    "ChainOfThoughtModule",
    "ReflectionModule",
    "DSPyReasoningAgent",
]
