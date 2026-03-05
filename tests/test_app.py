from pathlib import Path

import pytest
from textual.widgets import SelectionList, Static

from git_branch_cleanup.app import (
    BranchCleanupApp,
    ConfirmDeleteScreen,
    TuiResult,
)
from git_branch_cleanup.models import BranchInfo, BranchState, PullRequestInfo


def build_app(*, dry_run: bool = False) -> BranchCleanupApp:
    return BranchCleanupApp(
        repo_path=Path("/tmp/repo"),
        branches=[
            BranchInfo(
                name="feature/merged",
                state=BranchState.MERGED,
                pr=PullRequestInfo(
                    number=10,
                    title="Merged PR",
                    state="CLOSED",
                    merged_at="2026-03-01T00:00:00Z",
                    created_at="2026-02-20T00:00:00Z",
                ),
                is_contained=True,
            ),
            BranchInfo(
                name="feature/closed",
                state=BranchState.CLOSED,
                pr=PullRequestInfo(
                    number=11,
                    title="Closed PR",
                    state="CLOSED",
                    merged_at=None,
                    created_at="2026-02-21T00:00:00Z",
                ),
                is_contained=False,
            ),
            BranchInfo(
                name="feature/open",
                state=BranchState.OPEN,
                pr=PullRequestInfo(
                    number=12,
                    title="Open PR",
                    state="OPEN",
                    merged_at=None,
                    created_at="2026-02-22T00:00:00Z",
                ),
                is_contained=False,
            ),
            BranchInfo(
                name="feature/no-pr",
                state=BranchState.NO_PR,
                pr=None,
                is_contained=False,
            ),
        ],
        dry_run=dry_run,
    )


@pytest.mark.asyncio
async def test_selection_shortcuts_work_in_headless_mode() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.query_one("#branches", SelectionList)

        assert set(selection_list.selected) == {"feature/merged"}

        await pilot.press("a")
        assert set(selection_list.selected) == {
            "feature/merged",
            "feature/closed",
            "feature/open",
            "feature/no-pr",
        }

        await pilot.press("n")
        assert list(selection_list.selected) == []


@pytest.mark.asyncio
async def test_space_toggles_highlighted_row_selection() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.query_one("#branches", SelectionList)

        assert set(selection_list.selected) == {"feature/merged"}

        await pilot.press("down")
        await pilot.press("space")
        assert set(selection_list.selected) == {"feature/merged", "feature/closed"}

        await pilot.press("space")
        assert set(selection_list.selected) == {"feature/merged"}


@pytest.mark.asyncio
async def test_confirm_without_selection_does_not_open_modal() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("n")
        app.action_confirm()
        await pilot.pause()

        assert not isinstance(app.screen, ConfirmDeleteScreen)
        app.exit()


@pytest.mark.asyncio
async def test_confirm_modal_cancel_returns_to_main_screen() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_confirm()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmDeleteScreen)

        await pilot.click("#cancel")
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmDeleteScreen)

        app.exit()

    assert app.return_value is None


@pytest.mark.asyncio
async def test_confirm_modal_returns_selected_branches() -> None:
    app = build_app(dry_run=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_confirm()
        await pilot.pause()

        assert isinstance(app.screen, ConfirmDeleteScreen)
        assert app.screen.dry_run is True
        assert app.screen.branch_names == ["feature/merged"]

        await pilot.click("#confirm")
        await pilot.pause()

    assert app.return_value == TuiResult(selected_branches=["feature/merged"])


@pytest.mark.asyncio
async def test_confirm_modal_non_dry_run_content_and_flow() -> None:
    app = build_app(dry_run=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_confirm()
        await pilot.pause()

        assert isinstance(app.screen, ConfirmDeleteScreen)
        statics = list(app.screen.query(Static))
        assert len(statics) >= 2
        dialog_body = str(statics[1].render())
        assert "delete permanently with `git branch -D`" in dialog_body
        assert "- feature/merged" in dialog_body

        await pilot.click("#confirm")
        await pilot.pause()

    assert app.return_value == TuiResult(selected_branches=["feature/merged"])


@pytest.mark.asyncio
async def test_enter_key_opens_confirm_modal_from_list_focus() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, ConfirmDeleteScreen)
        app.exit()


@pytest.mark.asyncio
async def test_enter_key_confirms_from_modal() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmDeleteScreen)

        await pilot.press("enter")
        await pilot.pause()

    assert app.return_value == TuiResult(selected_branches=["feature/merged"])


@pytest.mark.asyncio
async def test_escape_key_cancels_from_modal() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmDeleteScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, ConfirmDeleteScreen)
        app.exit()

    assert app.return_value is None


@pytest.mark.asyncio
async def test_confirm_modal_has_scrollable_body_and_action_buttons() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_confirm()
        await pilot.pause()

        assert isinstance(app.screen, ConfirmDeleteScreen)
        app.screen.query_one("#confirm-body")
        app.screen.query_one("#cancel")
        app.screen.query_one("#confirm")
        app.exit()


@pytest.mark.asyncio
async def test_summary_shows_repo_path_and_state_counts() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        summary = str(app.query_one("#summary", Static).render())
        assert f"Repo: {Path('/tmp/repo')}" in summary
        assert "1 merged · 1 closed · 1 open · 1 no PR" in summary
        app.exit()


@pytest.mark.asyncio
async def test_branch_labels_include_pr_and_no_pr_text() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        selection_list = app.query_one("#branches", SelectionList)

        merged_prompt = str(selection_list.get_option_at_index(0).prompt)
        no_pr_prompt = str(selection_list.get_option_at_index(3).prompt)

        assert "feature/merged" in merged_prompt
        assert "MERGED" in merged_prompt
        assert "PR #10: Merged PR" in merged_prompt

        assert "feature/no-pr" in no_pr_prompt
        assert "NO_PR" in no_pr_prompt
        assert no_pr_prompt.endswith("  -")
        app.exit()


@pytest.mark.asyncio
async def test_confirm_multi_select_returns_exact_selected_set() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        app.action_confirm()
        await pilot.pause()
        assert isinstance(app.screen, ConfirmDeleteScreen)
        await pilot.click("#confirm")
        await pilot.pause()

    assert app.return_value is not None
    assert set(app.return_value.selected_branches) == {
        "feature/merged",
        "feature/closed",
        "feature/open",
        "feature/no-pr",
    }
    assert len(app.return_value.selected_branches) == 4


@pytest.mark.asyncio
async def test_quit_key_returns_cancelled_result() -> None:
    app = build_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()

    assert app.return_value == TuiResult(selected_branches=[], cancelled=True)
