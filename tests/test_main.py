from argparse import Namespace
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from git_branch_cleanup.git import DeleteBranchResult, DeleteBranchStatus
from git_branch_cleanup.main import delete_selected_branches

main_mod = importlib.import_module("git_branch_cleanup.main")


def test_delete_selected_branches_propagates_unexpected_exception() -> None:
    calls: list[str] = []

    def fake_delete(repo, branch_name: str, *, dry_run: bool) -> DeleteBranchResult:
        calls.append(branch_name)
        if branch_name == "feature/bad":
            raise RuntimeError("boom")
        return DeleteBranchResult(branch_name=branch_name, status=DeleteBranchStatus.DELETED)

    with pytest.raises(RuntimeError, match="boom"):
        delete_selected_branches(
            repo=object(),
            selected=["feature/bad", "feature/good"],
            dry_run=False,
            delete_fn=fake_delete,
        )

    assert calls == ["feature/bad"]


def test_main_exits_with_code_1_when_any_delete_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubParser:
        def parse_args(self) -> Namespace:
            return Namespace(no_fetch=True, repo=Path("/tmp/repo"), dry_run=False)

        def exit(self, status: int = 0, message: str | None = None) -> None:
            raise SystemExit(status)

    class StubApp:
        def __init__(self, *, repo_path: Path, branches: list, dry_run: bool) -> None:
            self.repo_path = repo_path
            self.branches = branches
            self.dry_run = dry_run

        def run(self):
            return SimpleNamespace(cancelled=False, selected_branches=["feature/a"])

    async def fake_fetch_prs_for_branches(*, branch_names: list[str], repo_dir: Path) -> dict:
        return {}

    repo = SimpleNamespace(working_tree_dir="/tmp/repo")

    monkeypatch.setattr(main_mod, "build_parser", lambda: StubParser())
    monkeypatch.setattr(main_mod, "ensure_gh_cli", lambda: None)
    monkeypatch.setattr(main_mod, "open_repo", lambda path: repo)
    monkeypatch.setattr(main_mod, "detect_default_branch", lambda _: "main")
    monkeypatch.setattr(main_mod, "current_branch_name", lambda _: "dev")
    monkeypatch.setattr(main_mod, "list_candidate_branches", lambda _repo, **_: ["feature/a"])
    monkeypatch.setattr(main_mod, "fetch_prs_for_branches", fake_fetch_prs_for_branches)
    monkeypatch.setattr(main_mod, "build_branch_infos", lambda **_: [])
    monkeypatch.setattr(main_mod, "BranchCleanupApp", StubApp)
    monkeypatch.setattr(
        main_mod,
        "delete_selected_branches",
        lambda **_: [
            DeleteBranchResult(branch_name="feature/a", status=DeleteBranchStatus.FAILED),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        main_mod.main()

    assert exc_info.value.code == 1


def test_main_returns_success_when_only_deleted_or_worktree_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubParser:
        def parse_args(self) -> Namespace:
            return Namespace(no_fetch=True, repo=Path("/tmp/repo"), dry_run=False)

        def exit(self, status: int = 0, message: str | None = None) -> None:
            raise SystemExit(status)

    class StubApp:
        def __init__(self, *, repo_path: Path, branches: list, dry_run: bool) -> None:
            self.repo_path = repo_path
            self.branches = branches
            self.dry_run = dry_run

        def run(self):
            return SimpleNamespace(
                cancelled=False, selected_branches=["feature/a", "feature/b", "feature/c"]
            )

    async def fake_fetch_prs_for_branches(*, branch_names: list[str], repo_dir: Path) -> dict:
        return {}

    repo = SimpleNamespace(working_tree_dir="/tmp/repo")

    monkeypatch.setattr(main_mod, "build_parser", lambda: StubParser())
    monkeypatch.setattr(main_mod, "ensure_gh_cli", lambda: None)
    monkeypatch.setattr(main_mod, "open_repo", lambda path: repo)
    monkeypatch.setattr(main_mod, "detect_default_branch", lambda _: "main")
    monkeypatch.setattr(main_mod, "current_branch_name", lambda _: "dev")
    monkeypatch.setattr(
        main_mod,
        "list_candidate_branches",
        lambda _repo, **_: ["feature/a", "feature/b", "feature/c"],
    )
    monkeypatch.setattr(main_mod, "fetch_prs_for_branches", fake_fetch_prs_for_branches)
    monkeypatch.setattr(main_mod, "build_branch_infos", lambda **_: [])
    monkeypatch.setattr(main_mod, "BranchCleanupApp", StubApp)
    monkeypatch.setattr(
        main_mod,
        "delete_selected_branches",
        lambda **_: [
            DeleteBranchResult(branch_name="feature/a", status=DeleteBranchStatus.DELETED),
            DeleteBranchResult(
                branch_name="feature/b",
                status=DeleteBranchStatus.SKIPPED_WORKTREE,
                message="checked out at /tmp/repo-wt",
            ),
            DeleteBranchResult(branch_name="feature/c", status=DeleteBranchStatus.DELETED),
        ],
    )

    main_mod.main()
