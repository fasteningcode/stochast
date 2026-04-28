from __future__ import annotations


class ThresholdNotMet(AssertionError):
    def __init__(self, test_name: str, pass_rate: float, threshold: float) -> None:
        super().__init__(
            f"{test_name}: pass rate {pass_rate:.1%} below threshold {threshold:.1%}"
        )
        self.test_name = test_name
        self.pass_rate = pass_rate
        self.threshold = threshold


class ConfigurationError(Exception):
    pass


class ProviderError(Exception):
    pass
