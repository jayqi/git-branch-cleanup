from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from git_branch_cleanup.models import PullRequestInfo


class GitHubCliError(RuntimeError):
    pass


def ensure_gh_cli() -> None:
    if shutil.which("gh") is None:
        raise GitHubCliError("GitHub CLI ('gh') is not installed.")

    result = subprocess.run(
        ["gh", "auth", "status"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitHubCliError("GitHub CLI is not authenticated. Run 'gh auth login' and try again.")


def parse_branch_prs(raw_prs: list[dict[str, Any]]) -> list[PullRequestInfo]:
    parsed: list[PullRequestInfo] = []
    for item in raw_prs:
        parsed.append(
            PullRequestInfo(
                number=int(item["number"]),
                title=str(item.get("title", "")),
                state=str(item.get("state", "")),
                merged_at=item.get("mergedAt"),
                created_at=item.get("createdAt"),
            )
        )
    return parsed


def select_most_recent_pr(prs: list[PullRequestInfo]) -> PullRequestInfo | None:
    if not prs:
        return None
    return max(prs, key=lambda pr: pr.number)


async def fetch_pr_for_branch(
    *,
    branch_name: str,
    repo_dir: Path,
    semaphore: asyncio.Semaphore,
) -> PullRequestInfo | None:
    async with semaphore:
        process = await asyncio.create_subprocess_exec(
            "gh",
            "pr",
            "list",
            "--head",
            branch_name,
            "--state",
            "all",
            "--json",
            "state,mergedAt,number,title,createdAt",
            "--limit",
            "20",
            cwd=str(repo_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

    if process.returncode != 0:
        message = stderr.decode().strip() or "Unknown gh error"
        raise GitHubCliError(f"Failed to query PRs for branch '{branch_name}': {message}")

    try:
        raw_prs = json.loads(stdout.decode())
    except json.JSONDecodeError as exc:
        raise GitHubCliError(
            f"GitHub CLI returned invalid JSON for branch '{branch_name}'."
        ) from exc

    prs = parse_branch_prs(raw_prs)
    return select_most_recent_pr(prs)


async def fetch_prs_for_branches(
    *,
    branch_names: list[str],
    repo_dir: Path,
    concurrency_limit: int = 5,
) -> dict[str, PullRequestInfo | None]:
    semaphore = asyncio.Semaphore(concurrency_limit)
    tasks = [
        fetch_pr_for_branch(branch_name=name, repo_dir=repo_dir, semaphore=semaphore)
        for name in branch_names
    ]
    results = await asyncio.gather(*tasks)
    return {name: pr for name, pr in zip(branch_names, results, strict=True)}
