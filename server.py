#!/usr/bin/env python3
"""Compare texts, generate diffs, and create/apply patches. — MEOK AI Labs."""

import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import json, difflib, hashlib
from datetime import datetime, timezone
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

FREE_DAILY_LIMIT = 30
_usage = defaultdict(list)
def _rl(c="anon"):
    now = datetime.now(timezone.utc)
    _usage[c] = [t for t in _usage[c] if (now - t).total_seconds() < 86400]
    if len(_usage[c]) >= FREE_DAILY_LIMIT:
        return json.dumps({"error": f"Limit {FREE_DAILY_LIMIT}/day. Upgrade: meok.ai"})
    _usage[c].append(now)
    return None

mcp = FastMCP("diff-ai", instructions="Compare texts, generate unified/context diffs, and create/apply patches. By MEOK AI Labs.")


@mcp.tool()
def diff_texts(text_a: str, text_b: str, context_lines: int = 3, label_a: str = "original", label_b: str = "modified", api_key: str = "") -> str:
    """Generate a unified diff between two text inputs."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl():
        return err

    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)
    context_lines = max(0, min(context_lines, 20))

    unified = list(difflib.unified_diff(lines_a, lines_b, fromfile=label_a, tofile=label_b, n=context_lines))
    unified_str = ''.join(unified)

    additions = sum(1 for line in unified if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in unified if line.startswith('-') and not line.startswith('---'))

    ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()

    return json.dumps({
        "diff": unified_str,
        "additions": additions,
        "deletions": deletions,
        "total_changes": additions + deletions,
        "similarity": round(ratio, 4),
        "lines_a": len(lines_a),
        "lines_b": len(lines_b),
        "identical": text_a == text_b,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def diff_files(content_a: str, content_b: str, filename_a: str = "file_a", filename_b: str = "file_b", output_format: str = "unified", api_key: str = "") -> str:
    """Generate a diff between two file contents in unified, context, or ndiff format."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl():
        return err

    lines_a = content_a.splitlines(keepends=True)
    lines_b = content_b.splitlines(keepends=True)
    output_format = output_format.lower().strip()

    if output_format == "context":
        diff_lines = list(difflib.context_diff(lines_a, lines_b, fromfile=filename_a, tofile=filename_b))
    elif output_format == "ndiff":
        diff_lines = list(difflib.ndiff(lines_a, lines_b))
    elif output_format == "html":
        differ = difflib.HtmlDiff()
        html_table = differ.make_table(
            lines_a, lines_b,
            fromdesc=filename_a, todesc=filename_b,
            context=True, numlines=3
        )
        return json.dumps({
            "format": "html",
            "html": html_table,
            "lines_a": len(lines_a),
            "lines_b": len(lines_b),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        diff_lines = list(difflib.unified_diff(lines_a, lines_b, fromfile=filename_a, tofile=filename_b))

    diff_str = ''.join(diff_lines)
    hash_a = hashlib.sha256(content_a.encode()).hexdigest()[:16]
    hash_b = hashlib.sha256(content_b.encode()).hexdigest()[:16]

    hunks = 0
    for line in diff_lines:
        if line.startswith('@@') or line.startswith('***'):
            hunks += 1

    return json.dumps({
        "format": output_format,
        "diff": diff_str,
        "hunks": hunks,
        "lines_a": len(lines_a),
        "lines_b": len(lines_b),
        "hash_a": hash_a,
        "hash_b": hash_b,
        "identical": content_a == content_b,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def generate_patch(original: str, modified: str, filename: str = "file.txt", api_key: str = "") -> str:
    """Generate a patch file from original and modified text that can be applied with the apply_patch tool."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl():
        return err

    lines_orig = original.splitlines(keepends=True)
    lines_mod = modified.splitlines(keepends=True)

    if not lines_orig or not lines_orig[-1].endswith('\n'):
        lines_orig = [l if l.endswith('\n') else l + '\n' for l in original.splitlines()]
    if not lines_mod or not lines_mod[-1].endswith('\n'):
        lines_mod = [l if l.endswith('\n') else l + '\n' for l in modified.splitlines()]

    patch_lines = list(difflib.unified_diff(
        lines_orig, lines_mod,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        n=3
    ))
    patch_str = ''.join(patch_lines)

    additions = sum(1 for l in patch_lines if l.startswith('+') and not l.startswith('+++'))
    deletions = sum(1 for l in patch_lines if l.startswith('-') and not l.startswith('---'))
    hunks = sum(1 for l in patch_lines if l.startswith('@@'))

    return json.dumps({
        "patch": patch_str,
        "filename": filename,
        "hunks": hunks,
        "additions": additions,
        "deletions": deletions,
        "original_lines": len(lines_orig),
        "modified_lines": len(lines_mod),
        "patch_size_bytes": len(patch_str.encode()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@mcp.tool()
def apply_patch(original: str, patch_text: str, api_key: str = "") -> str:
    """Apply a unified diff patch to the original text and return the result."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return json.dumps({"error": msg, "upgrade_url": "https://meok.ai/pricing"})
    if err := _rl():
        return err

    original_lines = original.splitlines(keepends=True)
    if original_lines and not original_lines[-1].endswith('\n'):
        original_lines[-1] += '\n'

    patch_lines = patch_text.splitlines(keepends=True)

    result_lines = list(original_lines)
    hunks = []
    current_hunk = None

    for line in patch_lines:
        if line.startswith('@@'):
            import re
            match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = {
                    "orig_start": int(match.group(1)) - 1,
                    "orig_count": int(match.group(2) or 1),
                    "new_start": int(match.group(3)) - 1,
                    "new_count": int(match.group(4) or 1),
                    "removals": [],
                    "additions": [],
                }
        elif current_hunk is not None:
            if line.startswith('-') and not line.startswith('---'):
                current_hunk["removals"].append(line[1:])
            elif line.startswith('+') and not line.startswith('+++'):
                current_hunk["additions"].append(line[1:])

    if current_hunk:
        hunks.append(current_hunk)

    offset = 0
    applied_hunks = 0
    failed_hunks = 0

    for hunk in hunks:
        start = hunk["orig_start"] + offset
        removals = hunk["removals"]
        additions = hunk["additions"]

        can_apply = True
        for i, rem_line in enumerate(removals):
            idx = start + i
            if idx >= len(result_lines):
                can_apply = False
                break
            if result_lines[idx].rstrip('\n') != rem_line.rstrip('\n'):
                can_apply = False
                break

        if can_apply:
            result_lines[start:start + len(removals)] = additions
            offset += len(additions) - len(removals)
            applied_hunks += 1
        else:
            failed_hunks += 1

    result_text = ''.join(result_lines)

    return json.dumps({
        "result": result_text,
        "applied_hunks": applied_hunks,
        "failed_hunks": failed_hunks,
        "total_hunks": len(hunks),
        "success": failed_hunks == 0,
        "original_lines": len(original_lines),
        "result_lines": len(result_lines),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    mcp.run()
