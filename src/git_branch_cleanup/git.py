from __future__ import annotations

from pathlib import Path

from git import InvalidGitRepositoryError, Repo


class GitRepoError(RuntimeError):
    pass


def open_repo(path: str | Path) -> Repo:
    try:
        return Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError as exc:
        raise GitRepoError(f"Not a git repository: {path}") from exc


def fetch_origin(repo: Repo) -> None:
    repo.git.fetch("--prune", "origin")


def detect_default_branch(repo: Repo) -> str:
    try:
        origin_head = repo.git.symbolic_ref("refs/remotes/origin/HEAD", "--short")
        if origin_head.startswith("origin/"):
            return origin_head.removeprefix("origin/")
    except Exception:
        pass

    local_names = {branch.name for branch in repo.branches}
    for candidate in ("main", "master"):
        if candidate in local_names:
            return candidate

    raise GitRepoError(
        "Could not determine default branch. Set origin/HEAD or create local main/master."
    )


def current_branch_name(repo: Repo) -> str:
    try:
        return repo.active_branch.name
    except TypeError as exc:
        raise GitRepoError("Repository is in detached HEAD state.") from exc


def filter_candidate_branches(
    *, branch_names: list[str], default_branch: str, current_branch: str
) -> list[str]:
    return [
        branch for branch in branch_names if branch != default_branch and branch != current_branch
    ]


def list_candidate_branches(repo: Repo, *, default_branch: str, current_branch: str) -> list[str]:
    branch_names = [branch.name for branch in repo.branches]
    return filter_candidate_branches(
        branch_names=branch_names,
        default_branch=default_branch,
        current_branch=current_branch,
    )


def is_branch_contained(repo: Repo, *, branch_name: str, default_branch: str) -> bool:
    # Exit code 0 means branch tip is reachable from default branch.
    try:
        repo.git.merge_base("--is-ancestor", branch_name, default_branch)
        return True
    except Exception:
        return False


def delete_local_branch(repo: Repo, branch_name: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    repo.git.branch("-D", branch_name)
