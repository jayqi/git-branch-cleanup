from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, SelectionList, Static

from git_branch_cleanup.models import BranchInfo, BranchState


def state_color(state: BranchState) -> str:
    if state is BranchState.MERGED:
        return "green"
    if state is BranchState.CLOSED:
        return "yellow"
    if state is BranchState.OPEN:
        return "blue"
    return "grey70"


class ConfirmDeleteScreen(ModalScreen[bool]):
    def __init__(self, branch_names: list[str], *, dry_run: bool) -> None:
        super().__init__()
        self.branch_names = branch_names
        self.dry_run = dry_run

    def compose(self) -> ComposeResult:
        action = "review (dry-run)" if self.dry_run else "delete permanently with `git branch -D`"
        branch_lines = "\n".join(f"- {name}" for name in self.branch_names)
        yield Container(
            Vertical(
                Label("Confirm Selection"),
                Static(f"You are about to {action}:\n\n{branch_lines}"),
                Button("Cancel", id="cancel"),
                Button("Confirm", id="confirm", variant="error"),
            ),
            id="confirm-dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(True)


@dataclass
class TuiResult:
    selected_branches: list[str]
    cancelled: bool = False


class BranchCleanupApp(App[TuiResult]):
    CSS = """
    #summary {
        padding: 0 1;
    }

    #list-container {
        padding: 1;
        height: 1fr;
    }

    #confirm-dialog {
        width: 70;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("space", "toggle", "toggle"),
        Binding("a", "select_all", "all"),
        Binding("n", "select_none", "none"),
        Binding("enter", "confirm", "delete selected"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self, *, repo_path: Path, branches: list[BranchInfo], dry_run: bool) -> None:
        super().__init__()
        self.repo_path = repo_path
        self.branches = branches
        self.dry_run = dry_run

    def compose(self) -> ComposeResult:
        merged_count = sum(1 for branch in self.branches if branch.state is BranchState.MERGED)
        closed_count = sum(1 for branch in self.branches if branch.state is BranchState.CLOSED)
        open_count = sum(1 for branch in self.branches if branch.state is BranchState.OPEN)
        no_pr_count = sum(1 for branch in self.branches if branch.state is BranchState.NO_PR)

        summary = (
            f"Repo: {self.repo_path}  "
            f"{merged_count} merged · {closed_count} closed · "
            f"{open_count} open · {no_pr_count} no PR"
        )

        yield Header(show_clock=False)
        yield Static(summary, id="summary")

        options = []
        for branch in self.branches:
            pr_text = "-"
            if branch.pr is not None:
                pr_text = f"PR #{branch.pr.number}: {branch.pr.title}"
            color = state_color(branch.state)
            label = (
                f"[bold]{branch.name}[/bold] [{color}]{branch.state.value:>7}[/{color}]  {pr_text}"
            )
            options.append((label, branch.name, branch.state is BranchState.MERGED))

        yield Container(SelectionList[str](*options, id="branches"), id="list-container")
        yield Footer()

    def action_select_all(self) -> None:
        selection_list = self.query_one("#branches", SelectionList)
        selection_list.select_all()

    def action_select_none(self) -> None:
        selection_list = self.query_one("#branches", SelectionList)
        selection_list.deselect_all()

    def action_confirm(self) -> None:
        selection_list = self.query_one("#branches", SelectionList)
        selected = [str(value) for value in selection_list.selected]
        if not selected:
            self.notify("No branches selected", severity="warning")
            return

        def after_confirm(confirmed: bool) -> None:
            if confirmed:
                self.exit(TuiResult(selected_branches=selected))

        self.push_screen(ConfirmDeleteScreen(selected, dry_run=self.dry_run), after_confirm)

    def action_quit(self) -> None:
        self.exit(TuiResult(selected_branches=[], cancelled=True))
