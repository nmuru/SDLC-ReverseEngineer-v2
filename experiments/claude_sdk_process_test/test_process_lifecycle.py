"""Independent Claude Agent SDK process-lifecycle experiment.

This script intentionally contains no ReverseEngineer-SDLC application code.
It measures whether one ClaudeSDKClient starts child processes and whether
those processes are reused across several sequential queries.
"""

import asyncio
import os
import sys
from typing import Iterable

import psutil
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient


PROMPTS = [
    "Reply with exactly: query-one",
    "Reply with exactly: query-two",
    "Reply with exactly: query-three",
]


def _mb(value: int) -> float:
    return value / (1024 * 1024)


def _safe_cmdline(process: psutil.Process) -> str:
    try:
        return " ".join(process.cmdline())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "<unavailable>"


def descendants(root: psutil.Process) -> Iterable[psutil.Process]:
    try:
        return sorted(root.children(recursive=True), key=lambda p: p.pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def snapshot(label: str) -> None:
    root = psutil.Process(os.getpid())
    print("\n" + "=" * 88)
    print(f"SNAPSHOT: {label}")
    print("=" * 88)
    print(
        f"ROOT  pid={root.pid} name={root.name()} "
        f"rss={_mb(root.memory_info().rss):.1f} MB "
        f"cmd={_safe_cmdline(root)}"
    )

    children = list(descendants(root))
    if not children:
        print("CHILDREN: <none>")
        return

    for child in children:
        try:
            memory = _mb(child.memory_info().rss)
            print(
                f"CHILD pid={child.pid} ppid={child.ppid()} "
                f"name={child.name()} rss={memory:.1f} MB "
                f"cmd={_safe_cmdline(child)}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"CHILD pid={child.pid} <process disappeared or inaccessible>")


async def run_query(client: ClaudeSDKClient, prompt: str, number: int) -> None:
    print(f"\n--- QUERY {number}: {prompt!r} ---")
    await client.query(prompt)

    response_count = 0
    async for message in client.receive_response():
        response_count += 1
        # Avoid dumping full SDK objects; we only need enough evidence that
        # the request completed and the client remained usable.
        text = getattr(message, "result", None)
        if text:
            print(f"RESULT: {text}")

    print(f"QUERY {number} completed; received {response_count} SDK messages")


async def main() -> None:
    print("Claude Agent SDK process-lifecycle experiment")
    print(f"Python executable: {sys.executable}")
    print(f"Python PID: {os.getpid()}")
    print("This process remains alive while all queries execute.")

    snapshot("before client construction")

    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        allowed_tools=[],
    )

    async with ClaudeSDKClient(options=options) as client:
        snapshot("after client start, before first query")

        for number, prompt in enumerate(PROMPTS, start=1):
            await run_query(client, prompt, number)
            snapshot(f"after query {number}")

        print("\nKeeping the same client open for 10 seconds for inspection...")
        await asyncio.sleep(10)
        snapshot("same client after 10-second idle period")

    print("\nClaudeSDKClient context has exited.")
    await asyncio.sleep(2)
    snapshot("after client shutdown")


if __name__ == "__main__":
    asyncio.run(main())
