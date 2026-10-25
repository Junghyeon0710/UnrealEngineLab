"""Runs the same prompts in headless Claude Code with and without the Unreal Engine Skills plugin.

Read-only prompts only. Each run's stream-json goes to Saved/UnrealEngineSkills/runs/, and one summary
line per run is appended to Docs/UE/Evidence/UnrealEngineSkills/summary.jsonl.

    python Scripts/UnrealEngineSkills/run_ab.py --plugin-dir <checkout of the plugin> --plan Scripts/UnrealEngineSkills/plan.json --cwd <empty folder>
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = "unreal-mcp"
MCP_TOOLS = [f"mcp__{SERVER}__{name}" for name in ("list_toolsets", "describe_toolset", "call_tool")]


def claude_command(exe, prompt, plugin_dir, model, mcp_config, tools):
    cmd = [
        exe, "-p", prompt,
        "--output-format", "stream-json", "--verbose", "--include-hook-events",
        "--model", model,
        "--mcp-config", str(mcp_config), "--strict-mcp-config",
        # Read-only built-ins only; no Bash/Edit/Write.
        "--tools", ",".join(tools),
        "--allowedTools", ",".join(MCP_TOOLS + tools),
        "--settings", json.dumps({"autoMemoryEnabled": False}),
        "--no-session-persistence",
        "--max-budget-usd", "4",
    ]
    if plugin_dir:
        cmd += ["--plugin-dir", str(plugin_dir)]
    return cmd


def summarize(events, wall):
    tool_calls, tool_errors, skills, hooks = [], 0, [], []
    init, result = {}, {}
    for e in events:
        kind = e.get("type")
        if kind == "system" and e.get("subtype") == "init":
            init = e
        elif kind == "system" and "hook" in str(e.get("subtype", "")):
            hooks.append({k: e.get(k) for k in ("subtype", "hook_name", "output", "exit_code")})
        elif kind == "assistant":
            for block in e.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                name, args = block.get("name"), block.get("input", {})
                if name == "Skill":
                    skills.append(args.get("skill") or args.get("command"))
                short = name.replace(f"mcp__{SERVER}__", "")
                if short == "call_tool":
                    short += f":{args.get('toolset_name', '')}.{args.get('tool_name', '')}"
                elif short == "describe_toolset":
                    short += f":{args.get('toolset_name', '')}"
                tool_calls.append(short)
        elif kind == "user":
            content = e.get("message", {}).get("content", [])
            if isinstance(content, list):
                tool_errors += sum(1 for b in content if b.get("type") == "tool_result" and b.get("is_error"))
        elif kind == "result":
            result = e
    usage = result.get("usage", {})
    return {
        "wall_s": round(wall, 1),
        "num_turns": result.get("num_turns"),
        "cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"),
        "cache_creation": usage.get("cache_creation_input_tokens"),
        "cache_read": usage.get("cache_read_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "is_error": result.get("is_error"),
        "tool_calls": tool_calls,
        "mcp_calls": sum(1 for c in tool_calls if c.split(":")[0] in ("list_toolsets", "describe_toolset", "call_tool")),
        "tool_errors": tool_errors,
        "skills_invoked": skills,
        "hooks": hooks,
        "plugins": [p.get("name") for p in init.get("plugins", [])],
        "model": init.get("model"),
        "answer": result.get("result"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plugin-dir", required=True)
    parser.add_argument("--cwd", default=str(ROOT),
                        help="Folder Claude runs in. The doc used an empty folder holding only copies of the .uproject and .mcp.json.")
    parser.add_argument("--output", default="summary.jsonl")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--claude", default=shutil.which("claude.exe") or shutil.which("claude") or "claude")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    work = ROOT / "Saved/UnrealEngineSkills"
    (work / "runs").mkdir(parents=True, exist_ok=True)
    evidence = ROOT / "Docs/UE/Evidence/UnrealEngineSkills"
    evidence.mkdir(parents=True, exist_ok=True)
    mcp_config = work / "mcp.json"
    mcp_config.write_text(json.dumps({"mcpServers": {SERVER: {"type": "http", "url": args.endpoint}}}), encoding="utf-8")
    env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")

    for run in plan["runs"]:
        tag = f"{run['task']}_{'plugin' if run['plugin'] else 'base'}_{run['rep']}"
        start = time.time()
        proc = subprocess.run(
            claude_command(args.claude, plan["tasks"][run["task"]], args.plugin_dir if run["plugin"] else None,
                           plan.get("model", "sonnet"), mcp_config, plan["tools"]),
            cwd=args.cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
        )
        wall = time.time() - start
        (work / "runs" / f"{tag}.jsonl").write_text(proc.stdout, encoding="utf-8")
        events = []
        for line in proc.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        row = {"tag": tag, **run, **summarize(events, wall)}
        with open(evidence / args.output, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(tag, row["num_turns"], row["mcp_calls"], row["tool_errors"], row["wall_s"], flush=True)


if __name__ == "__main__":
    main()
