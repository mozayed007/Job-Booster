"""Shared helpers for Gradio callbacks."""

import asyncio


def run_async(coro):
    """Run an async coroutine from a sync Gradio callback."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)