"""Event bus for pipeline lifecycle notifications."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class PipelineEvent:
    """An event emitted during pipeline execution."""
    
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[PipelineEvent], None]


class EventBus:
    """Simple in-memory event bus for pipeline events.
    
    Supports registering handlers for specific event types or wildcards.
    Handlers are called synchronously when events are emitted.
    
    State is held at the class level so any import of EventBus shares the
    same bus across the process. Call ``clear()`` in test teardown to avoid
    cross-test leakage.
    """
    
    _handlers: dict[str, list[EventHandler]] = {}
    _history: list[PipelineEvent] = []
    
    @classmethod
    def on(cls, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type.
        
        Args:
            event_type: Event type to handle, or "*" for all events
            handler: Callback function receiving PipelineEvent
        """
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    def emit(cls, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all registered handlers.
        
        Args:
            event_type: Event type being emitted
            data: Optional event data dict
        """
        event = PipelineEvent(event_type=event_type, data=data or {})
        cls._history.append(event)
        
        # Call specific handlers
        for handler in cls._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler failed for '{event_type}': {e}")
        
        # Call wildcard handlers
        for handler in cls._handlers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Wildcard handler failed: {e}")
    
    @classmethod
    def history(cls, limit: int = 50) -> list[PipelineEvent]:
        """Get recent event history.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent PipelineEvent objects
        """
        return cls._history[-limit:]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all handlers and history.
        
        Call in test teardown to prevent cross-test state leakage.
        """
        cls._handlers.clear()
        cls._history.clear()


def _log_handler(event: PipelineEvent) -> None:
    """Default handler: log all pipeline events."""
    logger.info(f"Pipeline event: {event.event_type} | {event.data}")


# Register default logging handler
EventBus.on("*", _log_handler)
