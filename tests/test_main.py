from git_branch_cleanup.git import DeleteBranchResult, DeleteBranchStatus
from git_branch_cleanup.main import delete_selected_branches


def test_delete_selected_branches_processes_all_selected_branches() -> None:
    calls: list[str] = []

    def fake_delete(repo, branch_name: str, *, dry_run: bool) -> DeleteBranchResult:
        calls.append(branch_name)
        if branch_name == "feature/skipped":
            return DeleteBranchResult(
                branch_name=branch_name,
                status=DeleteBranchStatus.SKIPPED_WORKTREE,
                message="checked out at /tmp/repo-wt",
            )
        if branch_name == "feature/failed":
            return DeleteBranchResult(
                branch_name=branch_name,
                status=DeleteBranchStatus.FAILED,
                message="branch not found",
            )
        return DeleteBranchResult(branch_name=branch_name, status=DeleteBranchStatus.DELETED)

    selected = ["feature/deleted", "feature/skipped", "feature/failed"]
    results = delete_selected_branches(
        repo=object(),
        selected=selected,
        dry_run=False,
        delete_fn=fake_delete,
    )

    assert calls == selected
    assert [result.branch_name for result in results] == selected
    assert [result.status for result in results] == [
        DeleteBranchStatus.DELETED,
        DeleteBranchStatus.SKIPPED_WORKTREE,
        DeleteBranchStatus.FAILED,
    ]
