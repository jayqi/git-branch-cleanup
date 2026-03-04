# AGENTS instructions

This project is Python CLI tool that identifies stale local git branches (accounting for squash merges) by querying the GitHub API, then presents an interactive TUI for reviewing and deleting them.

## Development environment

This project uses uv for Python environment management and Just as a task runner.

- Use `uv run` for anything that needs to be run in the project's Python environment.
- Common actions are defined as recipes in the [`justfile`](/justfile). Run `just` by itself to see documentation. Several commands are variadic and pass through arguments. This can be useful for running the recipe on specific files.

## Code quality

- Linting: `just lint` (variadic)
- Auto-formatting: `just format` (variadic)

## Development and testing

- Use red/green test-driven development
- Testing uses pytest and goes in [`tests/`](/tests/)
- Run the test suite with `just test` (variadic)
