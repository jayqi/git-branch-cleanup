# AGENTS instructions

This project is Python CLI tool that identifies stale local git branches (accounting for squash merges) by querying the GitHub API, then presents an interactive TUI for reviewing and deleting them.

## Development environment

This project uses uv for Python environment management and Just as a task runner.

- Use `uv run` for anything that needs to be run in the project's Python environment.
- Common actions are defined as recipes in the [`justfile`](/justfile).
    - Prefer using `just` recipes for actions when relevant.
    - Several commands are variadic and pass through arguments. This can be useful for running recipes on specific files.
    - Run `just` by itself to see documentation.

## Code quality

- Linting: `just lint` (variadic)
- Auto-formatting: `just format` (variadic)

## Development and testing

- Use red/green test-driven development: write failing tests first before implementing changes that make them pass
- Testing uses pytest and goes in [`tests/`](/tests/)
- Run the test suite with `just test` (variadic)
