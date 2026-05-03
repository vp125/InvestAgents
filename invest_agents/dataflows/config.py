"""Global config holder for dataflow routing.  Thread-safe set/get so agent
modules can discover the active vendor configuration without import cycles."""

from threading import local
from typing import Dict, Any

from invest_agents.default_config import DEFAULT_CONFIG

_thread_local = local()


def set_config(config: Dict[str, Any]) -> None:
    """Set the active configuration (called once at graph init)."""
    _thread_local.config = config


def get_config() -> Dict[str, Any]:
    """Return the current config, falling back to defaults."""
    if not hasattr(_thread_local, "config") or _thread_local.config is None:
        _thread_local.config = DEFAULT_CONFIG.copy()
    return _thread_local.config
