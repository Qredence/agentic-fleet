"""DSPy-powered Natural Language Understanding (NLU) module.

This module implements the DSPyNLU class, which uses DSPy signatures to perform
NLU tasks such as intent classification and entity extraction. It supports
lazy loading of compiled modules for performance.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import dspy

from ..utils.cfg import DEFAULT_NLU_CACHE_PATH
from .nlu_signatures import EntityExtraction, IntentClassification

logger = logging.getLogger(__name__)

# Module-level cache for DSPy module instances
_MODULE_CACHE: dict[str, dspy.Module] = {}


class DSPyNLU(dspy.Module):
    """NLU module that uses DSPy for intent classification and entity extraction."""

    def __init__(self) -> None:
        """Initialize the DSPy NLU module."""
        super().__init__()
        self._modules_initialized = False

        # Placeholders for lazy-initialized modules
        self._intent_classifier: dspy.Module | None = None
        self._entity_extractor: dspy.Module | None = None

    def _ensure_modules_initialized(self) -> None:
        """Lazily initialize DSPy modules on first use."""
        if self._modules_initialized:
            return

        global _MODULE_CACHE

        # Intent Classifier
        if self._intent_classifier is None:
            ic_key = "intent_classifier"
            if ic_key not in _MODULE_CACHE:
                _MODULE_CACHE[ic_key] = dspy.ChainOfThought(IntentClassification)
            self._intent_classifier = _MODULE_CACHE[ic_key]

        # Entity Extractor
        if self._entity_extractor is None:
            ee_key = "entity_extractor"
            if ee_key not in _MODULE_CACHE:
                _MODULE_CACHE[ee_key] = dspy.ChainOfThought(EntityExtraction)
            self._entity_extractor = _MODULE_CACHE[ee_key]

        self._modules_initialized = True
        logger.debug("DSPy NLU modules initialized (lazy)")

    @property
    def intent_classifier(self) -> dspy.Module:
        """Lazily initialized intent classifier."""
        self._ensure_modules_initialized()
        return self._intent_classifier  # type: ignore[return-value]

    @intent_classifier.setter
    def intent_classifier(self, value: dspy.Module) -> None:
        """Allow setting intent classifier (for compiled module loading)."""
        self._intent_classifier = value

    @property
    def entity_extractor(self) -> dspy.Module:
        """Lazily initialized entity extractor."""
        self._ensure_modules_initialized()
        return self._entity_extractor  # type: ignore[return-value]

    @entity_extractor.setter
    def entity_extractor(self, value: dspy.Module) -> None:
        """Allow setting entity extractor (for compiled module loading)."""
        self._entity_extractor = value

    def classify_intent(self, text: str, possible_intents: list[str]) -> dict[str, Any]:
        """Classify the intent of the input text.

        Args:
            text: User input text
            possible_intents: List of valid intent labels

        Returns:
            Dictionary with intent, confidence, and reasoning
        """
        if getattr(getattr(dspy, "settings", None), "lm", None) is None:
            return {"intent": "unknown", "confidence": 0.0, "reasoning": "no lm"}

        intents_str = ", ".join(possible_intents)
        prediction = self.intent_classifier(text=text, possible_intents=intents_str)

        return {
            "intent": getattr(prediction, "intent", "unknown"),
            "confidence": getattr(prediction, "confidence", 0.0),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def extract_entities(self, text: str, entity_types: list[str]) -> dict[str, Any]:
        """Extract entities from the input text.

        Args:
            text: User input text
            entity_types: List of entity types to extract

        Returns:
            Dictionary with entities list and reasoning
        """
        if getattr(getattr(dspy, "settings", None), "lm", None) is None:
            return {"entities": [], "reasoning": "no lm"}

        types_str = ", ".join(entity_types)
        prediction = self.entity_extractor(text=text, entity_types=types_str)

        return {
            "entities": getattr(prediction, "entities", []),
            "reasoning": getattr(prediction, "reasoning", ""),
        }

    def predictors(self) -> list[dspy.Module]:
        """Return list of predictors for optimization."""
        self._ensure_modules_initialized()
        return [
            self._get_predictor(self.intent_classifier),
            self._get_predictor(self.entity_extractor),
        ]

    def _get_predictor(self, module: dspy.Module) -> dspy.Module:
        """Extract the underlying Predict module from wrappers."""
        if hasattr(module, "predictors"):
            preds = module.predictors()
            if preds:
                return preds[0]
        return module


def get_nlu_module() -> DSPyNLU:
    """Get the DSPyNLU module, loading from cache if available.

    Returns:
        DSPyNLU instance (compiled or fresh)
    """
    # We don't cache the instance globally in _MODULE_CACHE like the individual predictors
    # because we want to load the *compiled* NLU module which might set those properties.

    # Check if a compiled pickle exists
    from ..utils.compiler import load_compiled_module

    cache_path = DEFAULT_NLU_CACHE_PATH
    if os.path.exists(cache_path):
        try:
            module = load_compiled_module(cache_path)
            if module is not None and isinstance(module, DSPyNLU):
                logger.info("Loaded compiled DSPyNLU from %s", cache_path)
                return module
        except Exception as e:
            logger.warning("Failed to load compiled DSPyNLU: %s", e)

    # Fallback to fresh instance
    return DSPyNLU()
