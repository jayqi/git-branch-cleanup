from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from git_branch_cleanup.app import BranchCleanupApp
from git_branch_cleanup.git import (
    GitRepoError,
    current_branch_name,
    delete_local_branch,
    detect_default_branch,
    fetch_origin,
    is_branch_contained,
    list_candidate_branches,
    open_repo,
)
from git_branch_cleanup.github import GitHubCliError, ensure_gh_cli, fetch_prs_for_branches
from git_branch_cleanup.models import BranchInfo, classify_branch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="git-branch-cleanup",
        description="Identify and clean stale local git branches.",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch --prune origin")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Path to repo")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not delete")
    return parser


def build_branch_infos(
    *,
    repo,
    default_branch: str,
    candidate_branches: list[str],
    prs_by_branch,
) -> list[BranchInfo]:
    infos: list[BranchInfo] = []
    for branch_name in candidate_branches:
        pr = prs_by_branch.get(branch_name)
        contained = is_branch_contained(
            repo,
            branch_name=branch_name,
            default_branch=default_branch,
        )
        state = classify_branch(pr=pr, is_contained=contained)
        infos.append(BranchInfo(name=branch_name, state=state, pr=pr, is_contained=contained))
    return infos


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        ensure_gh_cli()
        repo = open_repo(args.repo)
        repo_root = Path(repo.working_tree_dir or args.repo).resolve()

        if not args.no_fetch:
            fetch_origin(repo)

        default_branch = detect_default_branch(repo)
        current_branch = current_branch_name(repo)
        candidate_branches = list_candidate_branches(
            repo,
            default_branch=default_branch,
            current_branch=current_branch,
        )

        if not candidate_branches:
            print("No candidate branches found. Nothing to clean up.")
            return

        prs_by_branch = asyncio.run(
            fetch_prs_for_branches(branch_names=candidate_branches, repo_dir=repo_root)
        )

        branch_infos = build_branch_infos(
            repo=repo,
            default_branch=default_branch,
            candidate_branches=candidate_branches,
            prs_by_branch=prs_by_branch,
        )

        app = BranchCleanupApp(repo_path=repo_root, branches=branch_infos, dry_run=args.dry_run)
        tui_result = app.run()

        if tui_result is None or tui_result.cancelled:
            print("Aborted. No branches deleted.")
            return

        selected = tui_result.selected_branches
        if not selected:
            print("No branches selected.")
            return

        for branch_name in selected:
            delete_local_branch(repo, branch_name, dry_run=args.dry_run)

        if args.dry_run:
            print(f"Dry run complete. Would delete {len(selected)} branch(es).")
        else:
            print(f"Deleted {len(selected)} branch(es):")
            for name in selected:
                print(f"- {name}")

    except GitRepoError as exc:
        parser.exit(2, f"Error: {exc}\n")
    except GitHubCliError as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
