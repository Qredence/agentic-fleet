"""Tests for message classification and fast-path routing."""

import pytest

from agentic_fleet.utils.message_classifier import MessageClassifier, should_use_fast_path


class TestMessageClassifier:
    """Test suite for MessageClassifier class."""

    def test_simple_acknowledgments(self):
        """Test that simple acknowledgments are classified for fast-path."""
        classifier = MessageClassifier(enabled=True)

        simple_messages = [
            "ok",
            "okay",
            "yes",
            "no",
            "thanks",
            "thank you",
            "got it",
            "understood",
            "sure",
            "alright",
            "fine",
        ]

        for message in simple_messages:
            assert classifier.classify(message), f"Failed for: {message}"
            # Test with punctuation
            assert classifier.classify(f"{message}!"), f"Failed for: {message}!"
            assert classifier.classify(f"{message}."), f"Failed for: {message}."

    def test_complexity_patterns(self):
        """Test that messages with complexity patterns are rejected."""
        classifier = MessageClassifier(enabled=True)

        complex_messages = [
            "implement a new feature",
            "write some code for me",
            "create a function",
            "analyze this data",
            "compare these two files",
            "build a web application",
            "generate test cases",
            "refactor the codebase",
            "optimize performance",
            "debug this error",
            "fix the issue",
            "explain the code",
        ]

        for message in complex_messages:
            assert not classifier.classify(message), f"Failed for: {message}"

    def test_length_threshold(self):
        """Test that long messages are rejected."""
        classifier = MessageClassifier(max_length=50, enabled=True)

        # Short message should pass
        short = "what time is it"
        assert classifier.classify(short)

        # Long message should fail
        long = "a" * 51
        assert not classifier.classify(long)

    def test_multiple_sentences(self):
        """Test that multi-sentence messages are rejected."""
        classifier = MessageClassifier(enabled=True)

        single_sentence = "what is the weather today"
        assert classifier.classify(single_sentence)

        multiple_sentences = "What is the weather? Can you tell me?"
        assert not classifier.classify(multiple_sentences)

    def test_disabled_classifier(self):
        """Test that disabled classifier always returns False."""
        classifier = MessageClassifier(enabled=False)

        assert not classifier.classify("ok")
        assert not classifier.classify("simple question")

    def test_custom_patterns(self):
        """Test that custom complexity patterns work."""
        custom = [r"\bfoobar\b"]
        classifier = MessageClassifier(enabled=True, custom_patterns=custom)

        assert not classifier.classify("this has foobar in it")
        assert classifier.classify("this is clean")

    def test_is_simple_acknowledgment(self):
        """Test simple acknowledgment detection."""
        classifier = MessageClassifier()

        assert classifier.is_simple_acknowledgment("ok")
        assert classifier.is_simple_acknowledgment("OK")
        assert classifier.is_simple_acknowledgment("ok.")
        assert classifier.is_simple_acknowledgment("ok!")
        assert not classifier.is_simple_acknowledgment("ok then let's continue")

    def test_has_complexity_indicators(self):
        """Test complexity indicator detection."""
        classifier = MessageClassifier()

        assert classifier.has_complexity_indicators("write code")
        assert classifier.has_complexity_indicators("implement feature")
        assert not classifier.has_complexity_indicators("hello there")


class TestShouldUseFastPath:
    """Test suite for should_use_fast_path function."""

    def test_environment_variable_enabled(self, monkeypatch):
        """Test that ENABLE_FAST_PATH env var controls behavior."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        # Reset global classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        assert should_use_fast_path("ok")

    def test_environment_variable_disabled(self, monkeypatch):
        """Test that ENABLE_FAST_PATH=0 disables fast-path."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "0")
        # Reset global classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        assert not should_use_fast_path("ok")

    def test_max_length_from_env(self, monkeypatch):
        """Test that FAST_PATH_MAX_LENGTH env var is respected."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        monkeypatch.setenv("FAST_PATH_MAX_LENGTH", "20")
        # Reset global classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        short = "short"
        assert should_use_fast_path(short)

        long = "this message is longer than twenty characters"
        assert not should_use_fast_path(long)

    def test_real_world_examples(self, monkeypatch):
        """Test classification on real-world message examples."""
        monkeypatch.setenv("ENABLE_FAST_PATH", "1")
        # Reset global classifier
        import agentic_fleet.utils.message_classifier as module

        module._classifier = None

        # Should use fast-path
        fast_path_messages = [
            "ok",
            "thanks",
            "what's the weather?",
            "hello",
            "how are you?",
        ]

        for msg in fast_path_messages:
            assert should_use_fast_path(msg), f"Should use fast-path: {msg}"

        # Should use full orchestration
        full_orchestration_messages = [
            "please implement a login feature with OAuth2",
            "write a Python script to analyze CSV data",
            "create a React component with TypeScript",
            "debug this error in the authentication module",
            "compare these two algorithms and explain the differences",
        ]

        for msg in full_orchestration_messages:
            assert not should_use_fast_path(msg), f"Should use full orchestration: {msg}"


@pytest.fixture(autouse=True)
def reset_classifier():
    """Reset the global classifier before each test."""
    import agentic_fleet.utils.message_classifier as module

    module._classifier = None
    yield
    module._classifier = None
