# Claude Agent SDK process experiment

This experiment is independent of the ReverseEngineer-SDLC application. Its purpose is to determine the process and memory behaviour of `claude-agent-sdk`.

The experiment starts one long-lived `ClaudeSDKClient`, records the current process tree before and after the client starts, sends multiple sequential queries through the same client, and records the process tree after each query. It then exits the client context and records the process tree again.

On Windows, the script uses `psutil` to identify descendants of the Python process and reports PID, parent PID, executable name, RSS memory, and command line. This should reveal whether the SDK launches a Claude Code/Node process, whether that process is reused for multiple queries, and whether it exits when the SDK client closes.

## Install

From the repository root, create or activate a Python environment and install:

```powershell
pip install claude-agent-sdk psutil
```

Authentication should be configured using the normal Claude Agent SDK / Claude Code environment expected by the installed SDK.

## Run

```powershell
python experiments/claude_sdk_process_test/test_process_lifecycle.py
```

The script sends three simple prompts by default. Change `PROMPTS` in the script if desired.

The important comparison is the process snapshot labelled `after client start` versus the snapshots after query 1, 2, and 3. If the same child process PID remains present across all three queries, that is evidence that one SDK client reuses one subprocess rather than starting a new subprocess for every query. If additional processes appear for each query or remain after client shutdown, that will also be visible.
