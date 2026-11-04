# Optimization history

`20261104_optimization_history.sql` adds an empty `optimization_runs` table and indexes. It does not rewrite timetable data. Deploy backend before relying on the history UI. Model registration also supports the application's existing `create_all` bootstrap.

Every successful `/optimization/apply` saves exact before/after assignments for changed entries and the preview metrics in the same transaction. A failure to write history rolls back the timetable update. Existing applications before this release cannot be reconstructed retroactively.

- `GET /optimization/history?week_type=odd&teacher_id=13&offset=0&limit=10`: paginated runs. A teacher filter shows only operations executed with that exact scope, not a subset of an all-teacher operation.
- `GET /optimization/history/{id}/restore-preview`: checks the stored after-state against current assignments and validates the full proposed week without writing.
- `POST /optimization/history/{id}/restore`: repeats checks under the same PostgreSQL table locks as apply, restores only changed room/time fields, and marks the run restored atomically. Both restore routes require `week_type` and accept `teacher_id`.

Missing or edited entries, changed teacher ownership, wrong scope/week, repeated restores, and violations of current room/equipment/participant/transition/teacher conditions prevent restoration. Unrelated entries and the other week remain intact. Changes to teacher conditions are never undone. In particular, an optimization that repaired an invalid schedule cannot be undone until the prior assignments pass current validation. This is not an unrestricted demo reset or a database backup.

The current local profile is not authentication. This feature does not introduce auth or claim to record a verified operator identity. `teacher_id` describes optimization scope only. History contains personal and schedule data subject to the application's existing access model.

Tests: `DATABASE_URL=sqlite:// python -m unittest discover -s tests -v`. SQLite tests bypass PostgreSQL lock syntax; apply the additive migration on an isolated Neon branch to verify PostgreSQL schema compatibility.
