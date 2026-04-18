"""
Demo Mode Logger
----------------
Provides formatted, color-coded console output for demo mode scenario tracking.
"""
import sys
from datetime import datetime


# ANSI color codes for terminal output
class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    DIM = "\033[2m"


# Scenario-specific styling
_SCENARIO_STYLES = {
    "SUCCESS":          (_Colors.GREEN,   "✅"),
    "API_ERROR":        (_Colors.RED,     "💥"),
    "TIMEOUT":          (_Colors.YELLOW,  "⏱️"),
    "VALIDATION_ERROR": (_Colors.MAGENTA, "⚠️"),
    "EMPTY_RESPONSE":   (_Colors.CYAN,    "📭"),
    "PARTIAL_DATA":     (_Colors.YELLOW,  "📋"),
}


def log_scenario(scenario: str, endpoint: str, delay_ms: int, details: str = ""):
    """
    Log a demo mode scenario to the console with color coding.
    
    Example output:
        🎭 Demo Mode | ✅ SUCCESS for /route (delay: 350ms)
        🎭 Demo Mode | 💥 API_ERROR for /stats (delay: 120ms) — Simulated 500 Internal Server Error
    """
    color, icon = _SCENARIO_STYLES.get(scenario, (_Colors.DIM, "❓"))
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    msg = (
        f"{_Colors.DIM}[{timestamp}]{_Colors.RESET} "
        f"🎭 {_Colors.BOLD}Demo Mode{_Colors.RESET} | "
        f"{color}{icon} {scenario}{_Colors.RESET} "
        f"for {_Colors.CYAN}{endpoint}{_Colors.RESET} "
        f"{_Colors.DIM}(delay: {delay_ms}ms){_Colors.RESET}"
    )
    
    if details:
        msg += f" — {_Colors.DIM}{details}{_Colors.RESET}"
    
    print(msg, file=sys.stderr)


def log_config_change(field: str, old_val, new_val):
    """Log when demo configuration is changed at runtime."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(
        f"{_Colors.DIM}[{timestamp}]{_Colors.RESET} "
        f"🎭 {_Colors.BOLD}Demo Config Changed{_Colors.RESET} | "
        f"{field}: {_Colors.RED}{old_val}{_Colors.RESET} → {_Colors.GREEN}{new_val}{_Colors.RESET}",
        file=sys.stderr
    )


def log_demo_startup(config):
    """Log when demo mode is activated on server startup."""
    print(
        f"\n{'='*60}\n"
        f"  🎭 AIRROUTE DEMO MODE ACTIVE\n"
        f"  Success Rate: {config.success_rate*100:.0f}%\n"
        f"  Force Scenario: {config.force_scenario or 'None (probabilistic)'}\n"  
        f"  Latency Range: {config.min_delay_ms}–{config.max_delay_ms}ms\n"
        f"{'='*60}\n",
        file=sys.stderr
    )
