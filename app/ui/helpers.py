"""Shared helpers for Gradio callbacks."""

import asyncio
import concurrent.futures


def run_async(coro):
    """Run an async coroutine from a sync context.

    Uses ``asyncio.run`` when no event loop is running. When called from
    inside a running loop (e.g. some Gradio/Notebook contexts), the coroutine
    is executed in a dedicated worker thread with its own fresh event loop.
    This avoids the brittle loop patching done by ``nest_asyncio`` and
    prevents deadlocking the current loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
