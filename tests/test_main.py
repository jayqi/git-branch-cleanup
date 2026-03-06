from git_branch_cleanup.git import DeleteBranchResult, DeleteBranchStatus
from git_branch_cleanup.main import delete_selected_branches


def test_delete_selected_branches_continues_after_delete_exception() -> None:
    calls: list[str] = []

    def fake_delete(repo, branch_name: str, *, dry_run: bool) -> DeleteBranchResult:
        calls.append(branch_name)
        if branch_name == "feature/bad":
            raise RuntimeError("boom")
        return DeleteBranchResult(branch_name=branch_name, status=DeleteBranchStatus.DELETED)

    results = delete_selected_branches(
        repo=object(),
        selected=["feature/bad", "feature/good"],
        dry_run=False,
        delete_fn=fake_delete,
    )

    assert calls == ["feature/bad", "feature/good"]
    assert [result.branch_name for result in results] == ["feature/bad", "feature/good"]
    assert [result.status for result in results] == [
        DeleteBranchStatus.FAILED,
        DeleteBranchStatus.DELETED,
    ]
    assert "boom" in (results[0].message or "")
