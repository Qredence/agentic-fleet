"""DSPy signatures for Natural Language Understanding (NLU) tasks.

This module defines signatures for common NLU operations like intent classification
and entity extraction.
"""

from __future__ import annotations

import dspy


class IntentClassification(dspy.Signature):
    """Classify the intent of a user's input."""

    text: str = dspy.InputField(desc="The user's input text")
    possible_intents: str = dspy.InputField(desc="Comma-separated list of possible intents")

    intent: str = dspy.OutputField(desc="The classified intent")
    confidence: float = dspy.OutputField(desc="Confidence score between 0.0 and 1.0")
    reasoning: str = dspy.OutputField(desc="Reasoning for the classification")


class EntityExtraction(dspy.Signature):
    """Extract named entities from text."""

    text: str = dspy.InputField(desc="The user's input text")
    entity_types: str = dspy.InputField(desc="Comma-separated list of entity types to extract")

    entities: list[dict[str, str]] = dspy.OutputField(
        desc="List of extracted entities with 'text', 'type', and 'confidence'"
    )
    reasoning: str = dspy.OutputField(desc="Reasoning for the extraction")
