# Git Branch Cleanup TUI — Implementation Plan

## Overview

A Python CLI tool that identifies stale local git branches (accounting for squash merges) by querying the GitHub API, then presents an interactive TUI for reviewing and deleting them.

## Dependencies

- **`textual`** — TUI framework
- **`gitpython`** — enumerate local branches and run git operations
- **`gh` CLI** — GitHub API access (handles auth; must be installed and authenticated by user)

## Project Structure

```
git-branch-cleanup/
├── pyproject.toml
├── README.md
└── src/
    └── git_branch_cleanup/
        ├── __init__.py
        ├── main.py          # Entry point, CLI arg parsing
        ├── git.py           # Git operations (list branches, delete, fetch)
        ├── github.py        # GitHub API calls via gh CLI
        └── app.py           # Textual TUI app
```

## Core Logic

### Branch States

Each local branch should resolve to one of these states:

| State | Meaning | Default selected? |
|---|---|---|
| `MERGED` | PR found, was squash/merged | ✅ Yes |
| `CLOSED` | PR found, was closed without merging | ⚠️ User decides |
| `OPEN` | PR is still open | ❌ No |
| `NO_PR` | No PR found (may be local-only WIP) | ❌ No |
| `DEFAULT` | Is the repo's default branch | 🚫 Never shown |
| `CURRENT` | Currently checked-out branch | 🚫 Never shown |

### Step-by-Step Flow

1. **Startup** — Detect the git repo root from `cwd`. Abort with a helpful message if not in a repo.
2. **Fetch** — Run `git fetch --prune origin` to sync remote state (can be skipped with `--no-fetch` flag).
3. **Enumerate branches** — Get all local branches except the current branch and the default branch (`main`/`master`, auto-detected).
4. **Query GitHub** — For each branch, shell out to:
   ```
   gh pr list --head <branch> --state all --json state,mergedAt,number,title --limit 1
   ```
   Run these concurrently (e.g. `asyncio` + `asyncio.subprocess`) to keep startup time reasonable.
5. **Classify** — Map the API response to a branch state (see table above).
6. **Launch TUI** — Pass the classified branch list to the Textual app.

## TUI Design

```
┌─ Git Branch Cleanup ─────────────────────────────────────────────────────┐
│ Repo: ~/projects/my-app          2 merged · 1 closed · 1 no PR           │
├──────────────────────────────────────────────────────────────────────────┤
│  [x] feature/user-auth            MERGED    PR #42: Add user auth         │
│  [x] fix/login-redirect           MERGED    PR #51: Fix login redirect    │
│  [ ] chore/update-deps            CLOSED    PR #38: Bump dependencies     │
│  [ ] spike/new-architecture       NO PR     —                             │
├──────────────────────────────────────────────────────────────────────────┤
│  [space] toggle  [a] all  [n] none  [enter] delete selected  [q] quit    │
└──────────────────────────────────────────────────────────────────────────┘
```

- Rows are color-coded by state: green for `MERGED`, yellow for `CLOSED`, gray for `NO_PR`, blue for `OPEN`.
- Before deleting, show a confirmation dialog listing the branches to be deleted.
- After deletion, show a summary.

## CLI Interface

```
git-branch-cleanup [options]

Options:
  --no-fetch        Skip git fetch --prune step
  --repo PATH       Path to git repo (default: current directory)
```

## Implementation Notes

- Use `asyncio.gather` with a semaphore (e.g. concurrency limit of 5) for the `gh` API calls to avoid hammering the API.
- Handle the edge case where `gh` is not installed or not authenticated — fail early with a clear error message.
- `git branch -D` (force delete) is appropriate here since the whole point is cleaning up merged work. Make this clear in the confirmation dialog.
- Consider adding a `--dry-run` flag that runs everything but skips the actual deletion.

## Out of Scope (for now)

- Support for non-GitHub remotes (GitLab, Bitbucket)
- Deleting remote branches
- Config file for persistent preferences
