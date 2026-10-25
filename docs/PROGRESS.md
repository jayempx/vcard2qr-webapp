# Implementation ledger — docs/superpowers/plans/2026-10-25-webapp.md

User approved direct implementation and explicitly forbids any reuse of the previous project. All source/tests/deployment files are new.

- [x] 1. Payloads and renderer — 5 tests, PNG/SVG decoded with ZXing, all ten types.
- [x] 2. Backend and access — five web tests including CSRF, throttle, rotation and expiry.
- [x] 3. Public destinations — contact/download/type change/counters and escaped output verified locally; PostgreSQL concurrency remains in release verification.
- [x] 4. Frontend — browser generation/unlock/persistent create/toggle verified locally.
- [x] 5. Excel — templates, mixed rows, retry/cancel/expiry and cached ZIP tested. Browser downloaded template and imported its sample successfully.
- [x] 6. Publication and deployment — public-data audit passed, PostgreSQL CI/container/restore succeeded, automatic source promotion and a real Portainer redeployment verified.
- [ ] 7. Verification

Pre-flight: payload normalization feeds both static export and records; records feed public destination pages and imports; frontend consumes the same schema as backend. All names in the plan remain consistent.

Ruling: local Docker daemon is unavailable; run lightweight tests locally and PostgreSQL/container integration on CI and the authorized server. Do not claim SQLite tests prove PostgreSQL concurrency.

Review corrections: use database sessions so Lock revokes replayed cookies; preserve Wi-Fi credential whitespace; render batch output in cancellable chunks and retain binary exports for 24 hours with a 64 MiB batch cap; keep started import settings immutable and offer recovery/new import. Healthchecks always allow loopback. Audit historical paths, messages and account-only commit names as well as blob contents. Regression tests reproduced the first three failures before fixes.

Production verification found missing static manifest: collectstatic had used development storage. Reproduced the failed static lookup, switched the build to production storage and added root-page/hashed-static checks to container CI.

Production browser verification: no JavaScript errors, static generation, real Montserrat loaded, shared unlock, persistent contact creation/save/download, switch, destination type change, website template import and ZIP download. No page overflow at 390/1280 pixels in both themes. Final backup change excludes temporary imports/sessions from retention.
