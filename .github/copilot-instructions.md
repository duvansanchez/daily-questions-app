# AI Coding Agent Instructions for Daily Questions App

## Overview
- Flask web app managing goals ("objetivos"), daily questions, and personal development.
- SQL Server via `pyodbc` with Windows auth; connection created through `get_db_connection()` in `daily_questions_app/app.py` (tries ODBC 18 → 17 → SQL Server drivers).
- Session stored on filesystem (`flask_session/`), authentication with `flask_login`.
- HTML rendered via Jinja2 templates in `daily_questions_app/templates/`; many developer test views live as `test_*.html` files for manual debugging.

## Run & Develop
- Install dependencies: `pip install -r daily_questions_app/requirements.txt`.
- Start app: `python daily_questions_app/app.py` (default `http://localhost:5000`).
- Initialize/verify DB if needed using scripts in repo (e.g., `scripts/update_database.py`) and migration helpers under `daily_questions_app/` (e.g., `migrate_add_*`).
- Environment: Windows, SQL Server `DESKTOP-2MR0PJ6`, DB `DailyQuestions` (see `get_db_connection()` in app).

## Architecture & Key Patterns
- `daily_questions_app/app.py` is the monolith: routes, DB access, auth, email, i18n (`flask_babel`), scheduling (`apscheduler`).
- DB access is always through `with get_db_connection() as conn:`; commit on success, rollback on exception. Use this context manager for any DB work.
- Auth guard: API routes frequently use `@login_required`. When unauthenticated, JSON routes return 401; browser routes redirect to `login` (see `unauthorized()` handler in `app.py`).
- Recurrent vs non-recurrent objectives: endpoints differentiate normal completions vs entries in `objetivos_completados_log` for recurrent ones.
- Caching utilities in `daily_questions_app/cache_manager.py`: use `@cached(ttl=...)` and `SmartCacheInvalidator.invalidate_*()` after write operations.
- Email via `flask_mail` configured from `.env` (`MAIL_USERNAME`, `MAIL_PASSWORD`).

## Conventions
- Database date filtering uses SQL Server functions like `TRY_CAST(... AS DATE)` and `FORMAT(...)` for robust comparisons and display.
- Categories map to periods: diario, semanal, mensual, anual (see `/api/objetivos/stats_summary`).
- Files named `migrate_*` perform one-off schema/data updates; keep them idempotent.
- Many HTML files named `test_*.html` are dev tools to exercise endpoints and UI states; they are not production templates.
- Logging defaults to ERROR to reduce noise; prefer `logger.error(...)` for issues.

## Common Workflows
- Add new API route:
  - Implement in `app.py` with `@app.route(...)` and `@login_required` when needed.
  - Use `with get_db_connection() as conn:`; prefer parameterized queries.
  - For recurrent objectives, check `objetivos_completados_log` joins.
  - If results are reused often, decorate with `@cached()` and invalidate on writes.
- Update stats logic:
  - Reference `objetivos_stats_summary()` in `app.py` for expected calculations and categorization.
- Debug a specific day’s objectives:
  - `/api/objetivos/dia/<yyyy-mm-dd>` returns created, completed (normal vs recurrent), and pending recurrent objectives.
- Manual testing:
  - Use the `test_*.html` files in `daily_questions_app/` (e.g., `test_stats_modal.html`, `test_objetivos_programados_mañana.html`) to visualize and verify flows.

## Data & Tables
- Core tables: `objetivos`, `objetivos_completados_log`, `objetivos_saltados`. Some features check `estado != 'histórico'` for active recurrent objectives.
- Typical columns: `user_id`, `categoria`, `recurrente`, `fecha_creacion`, `completado`, `fecha_completado`, `parte_dia`, `horas_estimadas`.

## Integration & Settings
- Internationalization via `flask_babel` (`BABEL_DEFAULT_LOCALE = 'es'`) and `format_datetime` Jinja filter.
- Scheduler (`apscheduler`) may run background jobs; ensure thread-safe patterns and DB context usage.
- Sessions in `flask_session/`; ensure directory exists and is writable.

## Gotchas
- Always wrap DB operations in `get_db_connection()`; do not create direct `pyodbc.connect(...)` calls elsewhere.
- Use `request.is_json` and `/api/` path check patterns for unauthorized handling consistency.
- For date filters in SQL Server, prefer `TRY_CAST(... AS DATE)` for robust comparisons across `NULL`/invalid data.
- When caching endpoints, use sensible TTLs and invalidate on any write/side-effect to the same domain.

## Examples
- Stats summary pattern: see `objetivos_stats_summary()` in `daily_questions_app/app.py` for period range construction (hoy, semana, mes, año) and category mapping.
- Day detail pattern: see `objetivos_detalle_dia(fecha)` combining normal completions and recurrent log union.

## Where to Look
- Main logic: `daily_questions_app/app.py`
- Caching helpers: `daily_questions_app/cache_manager.py`
- Migrations/utilities: `daily_questions_app/migrate_*.py`, `scripts/`
- Dev test views: `daily_questions_app/test_*.html`

---
If any section is unclear or missing, tell me what parts you want detailed (e.g., email notifications, scheduled jobs, or specific DB schema), and I’ll refine this guide.