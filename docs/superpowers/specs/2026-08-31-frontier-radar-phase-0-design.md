# Frontier Radar Phase 0 Design

## Scope

Phase 0 creates only the CLI foundation for Frontier Radar. It includes local
MySQL configuration and connectivity, Alembic migration infrastructure, two
Typer commands, tests, Ruff, and project documentation. It does not implement
collectors, Agent behavior, web APIs, a frontend, scheduled work, or database
domain tables.

## Project layout

The project uses a `src/` layout and a `frontier_radar` package. The Phase 0
modules are intentionally small and have these responsibilities:

- `core`: Pydantic settings that read and validate `MYSQL_*` environment
  variables.
- `db`: SQLAlchemy engine and session-factory construction, plus the Alembic
  metadata base.
- `repositories`: database-only operations. The initial health repository runs
  `SELECT 1`.
- `services`: application behavior. The health service combines the application
  and database checks into a result usable by the CLI.
- `cli`: Typer command definitions and presentation only. Commands do not
  contain SQL or business logic.

Future `models`, `schemas`, `collectors`, and `agents` areas are documented in
`AGENTS.md` but are not implemented or populated in Phase 0.

## Configuration and database

`.env.example` documents `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`,
`MYSQL_USER`, and `MYSQL_PASSWORD`, using `frontier_radar` as the example
database name. A real `.env` is neither created nor committed. The application
reads process environment variables; users may optionally load them with their
own local environment tooling.

The user creates the local MySQL database separately. SQLAlchemy uses the
MySQL PyMySQL driver and creates sessions through a dedicated session factory.
All later schema changes must be represented by Alembic revisions.

## Commands and behavior

`fradar health` calls `HealthService`, which calls the database health
repository. It prints an application status and a database status. Valid
configuration and a successful `SELECT 1` produce exit code 0. Missing
configuration or a connection/query error produces a concise diagnostic and a
non-zero exit code.

`fradar db-upgrade` invokes Alembic to upgrade the configured database to
`head`. The initial Alembic revision is a no-op baseline: it establishes
migration tracking without creating Phase 1+ tables.

## Errors and test strategy

Configuration errors and database connection errors are represented at the
service boundary so the CLI can render them consistently. The database health
repository contains the SQLAlchemy-specific exception handling.

Pytest tests the health command/service behavior with a replaceable repository
dependency, covering both successful and unavailable database states without
requiring a local MySQL server. Ruff runs against application and test code.

## Documentation and repository

The root `AGENTS.md` uses the user-supplied project rules unchanged.
`docs/PROJECT_PLAN.md` records the user-supplied Phase 0–7 roadmap.
`docs/PROJECT_STATUS.md` begins with exactly:

`Current phase: Phase 0 — CLI initialization`

The local repository is initialized with Git, then published as a public
GitHub repository named `frontier-radar` after GitHub authentication is
confirmed.
