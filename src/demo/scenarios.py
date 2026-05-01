"""
Scenario Selector
-----------------
Probabilistically selects which edge-case scenario to simulate,
or uses a forced override if configured.
"""
import random
from typing import Tuple, Dict, Optional, Any

from src.demo.config import DemoConfig
from src.demo import mock_data


# Scenario names (constants)
SUCCESS = "SUCCESS"
API_ERROR = "API_ERROR"
TIMEOUT = "TIMEOUT"
VALIDATION_ERROR = "VALIDATION_ERROR"
EMPTY_RESPONSE = "EMPTY_RESPONSE"
PARTIAL_DATA = "PARTIAL_DATA"

# Map force_scenario strings to internal names
_FORCE_MAP = {
    "success": SUCCESS,
    "error": API_ERROR,
    "timeout": TIMEOUT,
    "validation_error": VALIDATION_ERROR,
    "empty": EMPTY_RESPONSE,
    "partial": PARTIAL_DATA,
}

# Failure scenario weights (relative, used when a failure is selected)
# These define the distribution among failure types
_FAILURE_WEIGHTS = {
    API_ERROR: 35,        # Most common failure
    TIMEOUT: 25,          # Second most common
    EMPTY_RESPONSE: 20,   # Fairly common in real APIs
    PARTIAL_DATA: 15,     # Occasional
    VALIDATION_ERROR: 5,  # Rare
}


class ScenarioSelector:
    """
    Selects which demo scenario to apply to a request.
    
    Logic:
    1. If config.force_scenario is set → use that scenario always
    2. Otherwise:
       - Roll against config.success_rate → SUCCESS or FAILURE
       - If FAILURE, pick from failure types based on weighted distribution
    """
    
    def __init__(self, config: DemoConfig):
        self.config = config
    
    def select(self, endpoint: str, query_force: Optional[str] = None) -> str:
        """
        Select a scenario for the current request.
        
        Args:
            endpoint: The request path (e.g., "/route", "/stats")
            query_force: Optional per-request override via ?demo_force= query param
            
        Returns:
            Scenario name string
        """
        # Priority 1: Per-request query parameter override
        if query_force and query_force in _FORCE_MAP:
            return _FORCE_MAP[query_force]
        
        # Priority 2: Global force_scenario config
        if self.config.force_scenario and self.config.force_scenario in _FORCE_MAP:
            return _FORCE_MAP[self.config.force_scenario]
        
        # Priority 3: Probabilistic selection
        if random.random() < self.config.success_rate:
            return SUCCESS
        
        # Select a failure type using weighted random
        failure_types = list(_FAILURE_WEIGHTS.keys())
        weights = list(_FAILURE_WEIGHTS.values())
        return random.choices(failure_types, weights=weights, k=1)[0]
    
    def get_response_data(self, scenario: str, endpoint: str, 
                          mode: str = "car", city: str = "bengaluru",
                          coords: Optional[Dict] = None) -> Tuple[int, Any]:
        """
        Generate the appropriate response data for the selected scenario.
        
        Returns:
            Tuple of (http_status_code, response_body)
            For error scenarios, response_body is a dict with "detail" key.
        """
        if endpoint == "/route":
            return self._get_route_response(scenario, mode, city, coords)
        elif endpoint == "/stats":
            return self._get_stats_response(scenario, city)
        elif endpoint == "/health":
            return (200, {"status": "ok", "mode": "demo", "demo_scenario": scenario})
        else:
            # Unknown endpoint — pass through
            return (200, None)
    
    def _get_route_response(self, scenario: str, mode: str, city: str, 
                            coords: Optional[Dict] = None) -> Tuple[int, Any]:
        """Generate route endpoint response for a given scenario."""
        if scenario == SUCCESS:
            return (200, mock_data.generate_route_success(mode, city, coords))
        
        elif scenario == API_ERROR:
            detail = mock_data.generate_error_detail()
            return (500, {"detail": detail})
        
        elif scenario == TIMEOUT:
            # The middleware will handle the actual delay.
            # After the delay, return either success or a timeout error.
            if random.random() > 0.5:
                # Sometimes timeouts still return data (slow response)
                return (200, mock_data.generate_route_success(mode, city, coords))
            else:
                return (504, {"detail": "Demo Mode: Simulated Gateway Timeout — upstream routing engine did not respond within deadline"})
        
        elif scenario == VALIDATION_ERROR:
            error = mock_data.generate_validation_error_detail()
            return (422, {"detail": f"Validation error on '{error['field']}': {error['message']} (received: {error['value']})"})
        
        elif scenario == EMPTY_RESPONSE:
            return (200, mock_data.generate_empty_route_response(mode))
        
        elif scenario == PARTIAL_DATA:
            return (200, mock_data.generate_partial_route_response(mode, city, coords))
        
        # Fallback
        return (200, mock_data.generate_route_success(mode, city))
    
    def _get_stats_response(self, scenario: str, city: str) -> Tuple[int, Any]:
        """Generate stats endpoint response for a given scenario."""
        if scenario == SUCCESS:
            return (200, mock_data.generate_stats_success(city))
        
        elif scenario == API_ERROR:
            return (500, {"detail": mock_data.generate_error_detail()})
        
        elif scenario == TIMEOUT:
            if random.random() > 0.5:
                return (200, mock_data.generate_stats_success(city))
            else:
                return (504, {"detail": "Demo Mode: Simulated Gateway Timeout"})
        
        elif scenario == VALIDATION_ERROR:
            error = mock_data.generate_validation_error_detail()
            return (422, {"detail": f"Validation error: {error['message']}"})
        
        elif scenario == EMPTY_RESPONSE:
            return (200, mock_data.generate_empty_stats_response(city))
        
        elif scenario == PARTIAL_DATA:
            return (200, mock_data.generate_partial_stats_response(city))
        
        return (200, mock_data.generate_stats_success(city))


def get_scenario_description(scenario: str) -> str:
    """Human-readable description of each scenario for logging."""
    descriptions = {
        SUCCESS: "Normal successful response with realistic data",
        API_ERROR: "Simulated 500/503 server error (API pipeline failure)",
        TIMEOUT: "Simulated network timeout with delayed response",
        VALIDATION_ERROR: "Simulated 422 validation error (bad input)",
        EMPTY_RESPONSE: "Valid schema but with empty/zero data (no results)",
        PARTIAL_DATA: "Response with some optional fields missing or null",
    }
    return descriptions.get(scenario, "Unknown scenario")
