import pytest

from agentic_fleet.utils.resilience import create_circuit_breaker


class MockService:
    def __init__(self):
        self.call_count = 0
        self.should_fail = True

    def operation(self):
        self.call_count += 1
        if self.should_fail:
            raise ValueError("Service failure")
        return "Success"


def test_circuit_breaker_retries():
    service = MockService()

    # Create a breaker that retries 3 times
    breaker = create_circuit_breaker(max_failures=3, reset_timeout=1, exceptions=(ValueError,))

    decorated_op = breaker(service.operation)

    # Should fail after 3 attempts
    with pytest.raises(ValueError, match="Service failure"):
        decorated_op()

    assert service.call_count == 3


def test_circuit_breaker_success():
    service = MockService()
    service.should_fail = False  # Succeed immediately

    breaker = create_circuit_breaker(max_failures=3, reset_timeout=1, exceptions=(ValueError,))
    decorated_op = breaker(service.operation)

    result = decorated_op()
    assert result == "Success"
    assert service.call_count == 1


def test_circuit_breaker_recovery():
    service = MockService()

    # Fail twice then succeed
    def flaky_operation():
        service.call_count += 1
        if service.call_count < 3:
            raise ValueError("Fail")
        return "Recovered"

    breaker = create_circuit_breaker(max_failures=5, reset_timeout=1, exceptions=(ValueError,))
    decorated_op = breaker(flaky_operation)

    result = decorated_op()
    assert result == "Recovered"
    assert service.call_count == 3
