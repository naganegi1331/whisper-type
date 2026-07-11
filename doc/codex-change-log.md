# Codex Change Log

## 2026-07-12

- Improved recognition lifecycle reliability by loading models asynchronously, handling worker stop timeouts, and deferring engine reloads safely.
- Made hotkey updates transactional and added validation for persisted configuration values.
- Added regression tests and resolved PR #2 conflicts with `main`; all 34 tests pass.
