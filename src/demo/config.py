"""
Demo Mode Configuration
-----------------------
Central configuration for the AirRoute demo mode system.
Controls probability of edge-case scenarios, forced overrides, and latency simulation.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DemoConfig:
    """
    Master configuration object for demo mode behavior.
    
    Attributes:
        enabled: Master toggle. When False, middleware is a complete no-op.
        success_rate: Probability of returning a successful response (0.0 to 1.0).
                      Default 0.8 = 80% success, 20% failure/edge-case.
        force_scenario: Force a specific scenario for every request.
                        Options: "success", "error", "timeout", "empty", "partial", "validation_error"
                        Set to None for probabilistic behavior.
        min_delay_ms: Minimum simulated network latency in milliseconds.
        max_delay_ms: Maximum simulated network latency in milliseconds.
        log_scenarios: Whether to print scenario details to the console.
        timeout_duration_s: How long a simulated timeout should take (seconds).
    """
    enabled: bool = False
    success_rate: float = 1.0
    force_scenario: Optional[str] = None
    min_delay_ms: int = 20
    max_delay_ms: int = 150
    log_scenarios: bool = True
    timeout_duration_s: float = 1.0

    # Track scenario execution counts for the current session
    _scenario_counts: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        # Allow environment variable to enable demo mode on startup
        if os.environ.get("AIRROUTE_DEMO_MODE", "").lower() in ("true", "1", "yes"):
            self.enabled = True

    def reset_counts(self):
        """Reset scenario execution counters."""
        self._scenario_counts.clear()

    def record_scenario(self, scenario_name: str):
        """Increment the counter for a scenario."""
        self._scenario_counts[scenario_name] = self._scenario_counts.get(scenario_name, 0) + 1

    def get_stats(self) -> dict:
        """Return execution statistics."""
        total = sum(self._scenario_counts.values())
        return {
            "total_requests": total,
            "scenario_breakdown": dict(self._scenario_counts),
            "config": {
                "enabled": self.enabled,
                "success_rate": self.success_rate,
                "force_scenario": self.force_scenario,
                "delay_range_ms": [self.min_delay_ms, self.max_delay_ms],
            }
        }

    def to_dict(self) -> dict:
        """Serialize config for API responses."""
        return {
            "enabled": self.enabled,
            "success_rate": self.success_rate,
            "force_scenario": self.force_scenario,
            "min_delay_ms": self.min_delay_ms,
            "max_delay_ms": self.max_delay_ms,
            "log_scenarios": self.log_scenarios,
            "timeout_duration_s": self.timeout_duration_s,
        }


# Singleton instance used throughout the application
demo_config = DemoConfig()
