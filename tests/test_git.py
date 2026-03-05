from git_branch_cleanup.git import filter_candidate_branches


def test_filter_candidate_branches_excludes_default_and_current() -> None:
    branches = ["main", "feature/a", "feature/b", "bugfix/c"]

    result = filter_candidate_branches(
        branch_names=branches,
        default_branch="main",
        current_branch="feature/b",
    )

    assert result == ["feature/a", "bugfix/c"]
