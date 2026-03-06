from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from git import InvalidGitRepositoryError, Repo
from git.exc import GitCommandError, NoSuchPathError


class GitRepoError(RuntimeError):
    pass


class DeleteBranchStatus(Enum):
    DELETED = "deleted"
    SKIPPED_WORKTREE = "skipped_worktree"
    FAILED = "failed"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class DeleteBranchResult:
    branch_name: str
    status: DeleteBranchStatus
    message: str | None = None


def open_repo(path: str | Path) -> Repo:
    try:
        return Repo(path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
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
    except GitCommandError:
        return False


def delete_local_branch(repo: Repo, branch_name: str, *, dry_run: bool) -> DeleteBranchResult:
    if dry_run:
        return DeleteBranchResult(branch_name=branch_name, status=DeleteBranchStatus.DRY_RUN)

    try:
        repo.git.branch("-D", branch_name)
    except GitCommandError as exc:
        message = str(exc.stderr or exc.stdout or exc).strip()
        if "checked out at" in message.lower():
            return DeleteBranchResult(
                branch_name=branch_name,
                status=DeleteBranchStatus.SKIPPED_WORKTREE,
                message=message,
            )
        return DeleteBranchResult(
            branch_name=branch_name,
            status=DeleteBranchStatus.FAILED,
            message=message,
        )

    return DeleteBranchResult(branch_name=branch_name, status=DeleteBranchStatus.DELETED)
