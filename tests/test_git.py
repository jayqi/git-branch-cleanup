from types import SimpleNamespace
from unittest.mock import Mock

from git.exc import GitCommandError

from git_branch_cleanup.git import (
    DeleteBranchStatus,
    delete_local_branch,
    filter_candidate_branches,
)


def test_filter_candidate_branches_excludes_default_and_current() -> None:
    branches = ["main", "feature/a", "feature/b", "bugfix/c"]

    result = filter_candidate_branches(
        branch_names=branches,
        default_branch="main",
        current_branch="feature/b",
    )

    assert result == ["feature/a", "bugfix/c"]


def test_delete_local_branch_returns_deleted_on_success() -> None:
    git = SimpleNamespace(branch=Mock())
    repo = SimpleNamespace(git=git)

    result = delete_local_branch(repo, "feature/a", dry_run=False)

    assert result.status is DeleteBranchStatus.DELETED
    assert result.branch_name == "feature/a"
    assert result.message is None
    git.branch.assert_called_once_with("-D", "feature/a")


def test_delete_local_branch_returns_dry_run_and_skips_git_delete() -> None:
    git = SimpleNamespace(branch=Mock())
    repo = SimpleNamespace(git=git)

    result = delete_local_branch(repo, "feature/a", dry_run=True)

    assert result.status is DeleteBranchStatus.DRY_RUN
    assert result.branch_name == "feature/a"
    git.branch.assert_not_called()


def test_delete_local_branch_returns_skipped_for_worktree_checked_out_error() -> None:
    git = SimpleNamespace(
        branch=Mock(
            side_effect=GitCommandError(
                "git branch -D feature/a",
                1,
                stderr="error: Cannot delete branch 'feature/a' checked out at '/tmp/repo-wt'",
            )
        )
    )
    repo = SimpleNamespace(git=git)

    result = delete_local_branch(repo, "feature/a", dry_run=False)

    assert result.status is DeleteBranchStatus.SKIPPED_WORKTREE
    assert result.branch_name == "feature/a"
    assert "checked out" in (result.message or "")


def test_delete_local_branch_returns_failed_for_other_git_errors() -> None:
    git = SimpleNamespace(
        branch=Mock(
            side_effect=GitCommandError(
                "git branch -D feature/a",
                1,
                stderr="error: branch 'feature/a' not found",
            )
        )
    )
    repo = SimpleNamespace(git=git)

    result = delete_local_branch(repo, "feature/a", dry_run=False)

    assert result.status is DeleteBranchStatus.FAILED
    assert result.branch_name == "feature/a"
    assert "not found" in (result.message or "")
