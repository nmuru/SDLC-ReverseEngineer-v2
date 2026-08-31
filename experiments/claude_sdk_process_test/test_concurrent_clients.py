"""Concurrent Claude Agent SDK client experiment.

This is intentionally independent of the ReverseEngineer-SDLC application.
It answers the production-scaling question: when several application-like
workloads execute concurrently, does each independently constructed
ClaudeSDKClient create its own Claude Code subprocess?

Each simulated request creates its own ClaudeSDKClient, sends one query, and
then closes the client. The parent process snapshots the complete descendant
process tree before, during, and after the concurrent workload.
"""

import asyncio
import os
import sys
from collections.abc import Iterable

import psutil
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient


REQUEST_COUNT = int(os.environ.get("CLAUDE_TEST_REQUESTS", "3"))
MODEL = os.environ.get("OPENROUTER_MODEL")
API_KEY = os.environ.get("OPENROUTER_API_KEY")
ENDPOINT = os.environ.get("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")


def mb(value: int) -> float:
    return value / (1024 * 1024)


def cmdline(process: psutil.Process) -> str:
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
    print("\n" + "=" * 100)
    print(f"SNAPSHOT: {label}")
    print("=" * 100)
    print(
        f"ROOT pid={root.pid} name={root.name()} "
        f"rss={mb(root.memory_info().rss):.1f} MB"
    )

    children = list(descendants(root))
    if not children:
        print("DESCENDANTS: <none>")
        return

    total_rss = 0.0
    for child in children:
        try:
            rss = mb(child.memory_info().rss)
            total_rss += rss
            print(
                f"CHILD pid={child.pid} ppid={child.ppid()} "
                f"name={child.name()} rss={rss:.1f} MB "
                f"cmd={cmdline(child)}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"DESCENDANT RSS TOTAL={total_rss:.1f} MB")
    print(f"CLAUDE-EXE COUNT={sum(1 for p in children if _is_claude(p))}")


def _is_claude(process: psutil.Process) -> bool:
    try:
        name = process.name().lower()
        return name in {"claude.exe", "claude"}
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


async def run_one_request(number: int) -> str:
    request_prompt = (
        f"This is isolated concurrency test request {number}. "
        f"Reply with exactly: concurrent-{number}"
    )

    options = ClaudeAgentOptions(
        model=MODEL,
        permission_mode="bypassPermissions",
        allowed_tools=[],
        env={
            "ANTHROPIC_BASE_URL": ENDPOINT,
            "ANTHROPIC_AUTH_TOKEN": API_KEY,
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_MODEL": MODEL,
            "ANTHROPIC_SMALL_FAST_MODEL": MODEL,
        },
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(request_prompt)
        final_text = ""
        async for message in client.receive_response():
            text = getattr(message, "result", None)
            if text:
                final_text = text
        return final_text


async def main() -> None:
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    if not MODEL:
        raise RuntimeError("OPENROUTER_MODEL is not set")
    if REQUEST_COUNT < 1:
        raise RuntimeError("CLAUDE_TEST_REQUESTS must be at least 1")

    print("Claude Agent SDK concurrent-client process experiment")
    print(f"Python executable: {sys.executable}")
    print(f"Parent PID: {os.getpid()}")
    print(f"Concurrent application-like requests: {REQUEST_COUNT}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Requested model: {MODEL}")
    print("API key present: yes (value intentionally not printed)")

    snapshot("before concurrent clients")

    tasks = [asyncio.create_task(run_one_request(i)) for i in range(1, REQUEST_COUNT + 1)]

    # Give the SDK processes time to start while all requests are active.
    await asyncio.sleep(3)
    snapshot("during concurrent requests")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for index, result in enumerate(results, start=1):
        if isinstance(result, Exception):
            print(f"REQUEST {index}: ERROR {type(result).__name__}: {result}")
        else:
            print(f"REQUEST {index}: {result!r}")

    snapshot("immediately after concurrent clients complete")
    await asyncio.sleep(2)
    snapshot("two seconds after all clients complete")


if __name__ == "__main__":
    asyncio.run(main())
