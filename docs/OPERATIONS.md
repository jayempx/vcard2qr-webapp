# Deployment and operations

## Automatic updates

Push a new commit to `main`. GitHub Actions runs PostgreSQL tests, QR decode checks, lint/format, migration checks, a Docker production smoke test and backup/restore. Only a successful, still-current run pins its source revision in `compose.portainer.yml` and commits that manifest to main. The built-in Actions token prevents the promotion commit from recursively triggering another run.

Portainer uses this Git repository, `refs/heads/main`, and `compose.portainer.yml`, polling every minute. On Portainer 2.45 configure the source-level GitOps polling interval in addition to the stack setting. A green workflow is promotion, not proof of deployment: inspect the stack state and `/health/` revision.

The app is built on the server from the exact verified Git commit; no registry credentials or Portainer token are needed in GitHub. Source-built app/maintenance images use `pull_policy: never`. Runtime manifest changes are operator-controlled: review them before merging, since Portainer sees the manifest on main.

## Private configuration

Configure `SECRET_KEY`, `ACCESS_CODE`, `POSTGRES_PASSWORD`, `PUBLIC_BASE_URL`, `ALLOWED_HOSTS` and `PROXY_NETWORK` only in the stack's private environment. Use a randomly generated six-digit access code and stable secret key. The app automatically permits loopback hosts for container healthchecks.

The reverse proxy and app share the configured proxy network. Route HTTPS to the application network alias on port 8000; publish no app/database host ports. Overwrite X-Real-IP and X-Forwarded-Proto at the trusted proxy. Suppress access logs for this host; the app stores HMAC rate-limit buckets, not raw client IPs. Restrict the proxy network to trusted containers.

Do not put real deployment domains, addresses, private network names, contact data or tokens in source, commit messages, CI logs or examples. Before push run the history audit, also supplying a private denylist with `--denylist` when configured. Manually review repository metadata and workflow output too.

## Backup and migration

App startup backs up an existing PostgreSQL database before migrations. The maintenance service expires temporary imports, rate buckets and sessions hourly and makes a daily backup. Backups are custom-format PostgreSQL archives on the separate backup volume; retention is 14 daily and 14 predeployment backups. The app is non-root (UID 10001); named volumes must remain writable by that identity.

`python manage.py backup_data` writes a snapshot and checks archive readability. CI additionally restores into a fresh isolated database and asserts stable IDs/counters. Backup failure prevents the app from upgrading. Do not delete database/backup volumes during updates.

These are local backups on the same host. Off-host copies require a separate operator-configured destination and schedule; they are not implied by local backup success.

Backup archives exclude temporary import/output, throttle and session table data, retaining their schema only. Expiring static import content must not become a persistent archive through backup retention.

For recovery, stop writers, restore a selected archive into a NEW database, run the matching application revision, and verify identifiers/counts before switching the private database configuration. Preserve the original public base URL to keep printed links valid. Never run the isolated CI restore script against the production database.

## Operational checks

- `/health/`: database connectivity and source revision, no secrets.
- Verify the Portainer source sync and actual running image after each promotion.
- Verify code rotation, existing persistent links and volume retention after an update.
- Monitor failed backup/maintenance containers and disk usage. Keep trusted proxies and API ports private.
- Physical phone scanning and contact import must be tested on real target devices before a print run.
