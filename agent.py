#!/usr/bin/env python3
"""agent.py

Fetch issues via the local Swytchcode GitHub provider and print a summary report.

Requirements:
- `npx swytchcode` must be available in PATH and the project should have the
  GitHub provider connected (we assume you already ran `swytchcode auth connect github`).

Usage examples:
  python agent.py --repo owner/repo
  python agent.py            # lists issues across visible repos

The script calls `npx swytchcode exec github.issue.list` and parses the
JSON output. It paginates until no more items are returned.
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import os
import textwrap
import urllib.request
import urllib.parse
import time
from typing import Any, Dict, List, Optional


# A small cached/sample report to use when network/REST is unavailable.
SAMPLE_ISSUES: List[Dict[str, Any]] = [
    {
        "title": "Bug: setState causes unexpected re-render",
        "number": 12345,
        "repository": {"full_name": "facebook/react"},
        "html_url": "https://github.com/facebook/react/issues/12345",
        "body": "When calling setState in componentDidMount, the component sometimes re-renders twice. Steps to reproduce...",
    },
    {
        "title": "RFC: Add new useAwesomeHook hook",
        "number": 12344,
        "repository": {"full_name": "facebook/react"},
        "html_url": "https://github.com/facebook/react/issues/12344",
        "body": "Proposal to add a new hook that simplifies async state handling across components.",
    },
]


def run_swytchcode_list(filter_value: str = "all", state: str = "open", per_page: int = 100, page: int = 1) -> Dict[str, Any]:
    base_cmd = [
        "swytchcode",
        "exec",
        "github.issue.list",
        "--param",
        f"filter={filter_value}",
        "--param",
        f"state={state}",
        "--param",
        f"per_page={per_page}",
        "--param",
        f"page={page}",
        "--json",
    ]

    # Try to resolve npx executable (Windows may have npx.cmd)
    npx_path = shutil.which("npx") or shutil.which("npx.cmd")
    env = os.environ.copy()

    if npx_path:
        cmd = [npx_path] + base_cmd
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env, encoding="utf-8", errors="replace")
        except FileNotFoundError as e:
            raise RuntimeError("`npx` or `swytchcode` not found in PATH") from e
    else:
        # Fall back to shell invocation (helps when npx is available via shell shims)
        cmd_str = " ".join(shlex.quote(c) for c in (["npx"] + base_cmd))
        proc = subprocess.run(cmd_str, capture_output=True, text=True, check=False, shell=True, env=env, encoding="utf-8", errors="replace")

    if proc.returncode != 0:
        # Include stderr for easier debugging
        # Show command as a string for clarity
        raise RuntimeError(f"swytchcode exec failed (code {proc.returncode}): {proc.stderr.strip()}\nCmd: {proc.args}")

    # The --json output writes a JSON object to stdout
    try:
        payload = json.loads(proc.stdout)
    except Exception as e:
        raise RuntimeError(f"failed to parse swytchcode JSON output: {e}\nOutput:\n{proc.stdout}") from e

    return payload


def summarize_issue(issue: Dict[str, Any], body_len: int = 300) -> str:
    title = issue.get("title", "(no title)")
    number = issue.get("number")
    repo = None
    repository = issue.get("repository") or {}
    repo = repository.get("full_name") or repository.get("fullName") or repository.get("name")
    url = issue.get("html_url") or issue.get("url")

    body = issue.get("body") or issue.get("body_text") or ""
    body = body.strip()
    if len(body) > body_len:
        body = body[: body_len - 1] + "…"

    header = f"[{repo}#{number}] {title}" if repo else f"[#{number}] {title}"
    wrapped = textwrap.fill(body or "(no description)", width=80)

    return f"{header}\n{wrapped}\nURL: {url}\n"


def fetch_all_issues(filter_value: str = "all", state: str = "open", per_page: int = 100, repo: Optional[str] = None, use_rest: bool = False) -> List[Dict[str, Any]]:
    if use_rest:
        return fetch_all_issues_rest(state=state, per_page=per_page, repo=repo)

    all_issues: List[Dict[str, Any]] = []
    page = 1
    while True:
        payload = run_swytchcode_list(filter_value=filter_value, state=state, per_page=per_page, page=page)
        data = payload.get("data")
        if data is None:
            # fallback: some versions return the array directly
            data = payload

        if not isinstance(data, list):
            raise RuntimeError(f"unexpected payload shape, 'data' is not a list: {type(data)}")

        if not data:
            break

        all_issues.extend(data)
        if len(data) < per_page:
            break
        page += 1

    return all_issues


def fetch_all_issues_rest(state: str = "open", per_page: int = 100, repo: Optional[str] = None) -> List[Dict[str, Any]]:
    # Require an authenticated token to avoid unauthenticated rate limits
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("REST fallback requires GITHUB_TOKEN in environment to avoid unauthenticated rate limits")
    if not repo:
        raise RuntimeError("REST fallback requires --repo owner/repo for REST fetch")
    owner_repo = repo
    issues: List[Dict[str, Any]] = []
    page = 1
    while True:
        qs = {
            "state": state,
            "per_page": str(per_page),
            "page": str(page),
        }
        url = f"https://api.github.com/repos/{owner_repo}/issues?" + urllib.parse.urlencode(qs)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "swytchcode-agent/1.0",
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                text = raw.decode("utf-8", errors="replace")
                data = json.loads(text)
        except Exception as e:
            raise RuntimeError(f"REST fetch failed: {e}")

        if not data:
            break
        issues.extend(data)
        if len(data) < per_page:
            break
        page += 1
        time.sleep(0.1)

    return issues


def filter_by_repo(issues: List[Dict[str, Any]], repo: Optional[str]) -> List[Dict[str, Any]]:
    if not repo:
        return issues
    repo_lower = repo.lower()
    out = []
    for it in issues:
        repository = it.get("repository") or {}
        full = (repository.get("full_name") or repository.get("fullName") or repository.get("name") or "").lower()
        if full == repo_lower:
            out.append(it)
    return out


def print_report(issues: List[Dict[str, Any]]):
    if not issues:
        print("No issues found.")
        return

    print(f"Found {len(issues)} issues:\n")
    for i, issue in enumerate(issues, start=1):
        summary = summarize_issue(issue)
        print(f"{i}. {summary}")


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Fetch GitHub issues via Swytchcode provider and print a summary report.")
    parser.add_argument("--repo", help="Optional owner/repo to filter results (e.g. octocat/Hello-World)")
    parser.add_argument("--state", help="Issue state: open, closed, all", default="open")
    parser.add_argument("--filter", help="Filter param for GitHub: assigned|created|mentioned|subscribed|repos|all", default="all")
    parser.add_argument("--per-page", help="Items per page (max 100)", type=int, default=100)
    parser.add_argument("--use-rest", action="store_true", help="Use direct GitHub REST API (public repos only)")
    parser.add_argument("--use-sample", action="store_true", help="Use embedded sample issues instead of network calls")

    args = parser.parse_args(argv)

    try:
        if args.use_sample:
            issues = SAMPLE_ISSUES
        else:
            issues = fetch_all_issues(filter_value=args.filter, state=args.state, per_page=args.per_page, repo=args.repo, use_rest=args.use_rest)
    except Exception as e:
        print(f"Error fetching issues: {e}", file=sys.stderr)
        print("Falling back to sample issues.")
        issues = SAMPLE_ISSUES

    issues = filter_by_repo(issues, args.repo)

    print_report(issues)


if __name__ == "__main__":
    main()
