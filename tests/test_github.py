from git_branch_cleanup.github import parse_branch_prs, select_most_recent_pr


def test_select_most_recent_pr_uses_highest_number() -> None:
    prs = parse_branch_prs(
        [
            {
                "number": 12,
                "title": "Older",
                "state": "CLOSED",
                "mergedAt": None,
                "createdAt": "2026-01-01T00:00:00Z",
            },
            {
                "number": 55,
                "title": "Newest",
                "state": "OPEN",
                "mergedAt": None,
                "createdAt": "2026-03-01T00:00:00Z",
            },
            {
                "number": 42,
                "title": "Middle",
                "state": "CLOSED",
                "mergedAt": "2026-02-01T00:00:00Z",
                "createdAt": "2026-02-01T00:00:00Z",
            },
        ]
    )

    selected = select_most_recent_pr(prs)

    assert selected is not None
    assert selected.number == 55
    assert selected.title == "Newest"
