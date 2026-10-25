# Implementation ledger — docs/superpowers/plans/2026-10-25-webapp.md

User approved direct implementation and explicitly forbids any reuse of the previous project. All source/tests/deployment files are new.

- [x] 1. Payloads and renderer — 5 tests, PNG/SVG decoded with ZXing, all ten types.
- [x] 2. Backend and access — five web tests including CSRF, throttle, rotation and expiry.
- [x] 3. Public destinations — contact/download/type change/counters and escaped output verified locally; PostgreSQL concurrency remains in release verification.
- [ ] 4. Frontend
- [ ] 5. Excel
- [ ] 6. Publication and deployment
- [ ] 7. Verification

Pre-flight: payload normalization feeds both static export and records; records feed public destination pages and imports; frontend consumes the same schema as backend. All names in the plan remain consistent.

Ruling: local Docker daemon is unavailable; run lightweight tests locally and PostgreSQL/container integration on CI and the authorized server. Do not claim SQLite tests prove PostgreSQL concurrency.
