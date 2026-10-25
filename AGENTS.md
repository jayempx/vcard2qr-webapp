# vcard2qr-webapp

- Independent implementation from scratch. Never reuse the retired project's code, tests, configuration or Git history.
- English product copy. No company references, Privacy pages or separate admin UI.
- Django, PostgreSQL, plain JavaScript. Keep secrets and actual deployment domains/networks only in private configuration.
- Before push run the public-data audit on history and inspect staged content and CI output. Use noreply Git identities.
- Run `python manage.py test` and `ruff check .` before release. Local test mode uses an isolated database; production requires PostgreSQL.
- Never use production data in tests. Keep changes consistent with docs/SPEC.md.
