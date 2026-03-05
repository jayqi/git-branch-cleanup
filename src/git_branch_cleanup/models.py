from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BranchState(str, Enum):
    MERGED = "MERGED"
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    NO_PR = "NO_PR"


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    state: str
    merged_at: str | None
    created_at: str | None


@dataclass(frozen=True)
class BranchInfo:
    name: str
    state: BranchState
    pr: PullRequestInfo | None
    is_contained: bool


def classify_branch(*, pr: PullRequestInfo | None, is_contained: bool) -> BranchState:
    if is_contained:
        return BranchState.MERGED
    if pr is None:
        return BranchState.NO_PR
    if pr.merged_at is not None:
        return BranchState.MERGED
    if pr.state.upper() == "OPEN":
        return BranchState.OPEN
    return BranchState.CLOSED
