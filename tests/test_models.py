from git_branch_cleanup.models import BranchState, PullRequestInfo, classify_branch


def test_classify_branch_prefers_ancestry_signal_over_open_pr() -> None:
    pr = PullRequestInfo(
        number=101,
        title="Open change",
        state="OPEN",
        merged_at=None,
        created_at="2026-03-01T10:00:00Z",
    )

    result = classify_branch(pr=pr, is_contained=True)

    assert result is BranchState.MERGED


def test_classify_branch_with_no_pr() -> None:
    result = classify_branch(pr=None, is_contained=False)

    assert result is BranchState.NO_PR


def test_classify_branch_with_closed_pr() -> None:
    pr = PullRequestInfo(
        number=88,
        title="Old change",
        state="CLOSED",
        merged_at=None,
        created_at="2026-02-15T10:00:00Z",
    )

    result = classify_branch(pr=pr, is_contained=False)

    assert result is BranchState.CLOSED


def test_classify_branch_with_open_pr() -> None:
    pr = PullRequestInfo(
        number=77,
        title="Active change",
        state="OPEN",
        merged_at=None,
        created_at="2026-03-02T10:00:00Z",
    )

    result = classify_branch(pr=pr, is_contained=False)

    assert result is BranchState.OPEN
