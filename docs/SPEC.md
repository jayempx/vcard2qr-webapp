# vcard2qr-webapp specification

## Product

A public QR application, opening directly on its generator. No landing page, separate admin UI, accounts, company references, logo insertion or Privacy section. UI copy is English. Responsive on desktop and mobile; light/dark mode follows the system.

The accepted visual direction uses cyan-to-blue gradient pill buttons, rounded inputs/cards, cool shadows, an 8-pixel spacing scale and Montserrat 300/400/600/800. Load the font in the actual application, with Arial as fallback. Keep the interface focused on generating and managing QR codes.

## Public generator

- Content type dropdown: vCard, website, text, Wi-Fi, email, phone, SMS, location, event, WhatsApp.
- Typed fields with server-side validation. vCard includes name, organization, title, email, phone numbers, address, website, notes and multiple custom name/value fields.
- Static codes embed the content directly. vCard behavior is controlled by the scanning device; it cannot be forced to show our contact page.
- Preview; foreground/background color, output size, transparent background and rounded modules. Preserve QR quiet zone, contrast and integer module sizes.
- PNG and SVG download and PNG clipboard copy, with supported-browser errors handled explicitly.
- No database history or persistent content storage for static codes. Server processing in memory is acceptable; avoid content in query strings, logs and caches.
- Editing content or appearance invalidates stale preview/export controls.

## Shared workspace

- Unlock button in the top-right opens a six-digit numeric password field. Entering the sixth digit automatically submits once; wrong code shows an error and permits retry/paste.
- ACCESS_CODE is a deployment secret, never shipped to the client. No demo code in production. Validate it as exactly six ASCII digits, preserving leading zeros.
- Signed HttpOnly session, 24-hour absolute lifetime; Lock ends access. Changing ACCESS_CODE invalidates all existing unlocked sessions. Verify authorization and CSRF for every private operation.
- Throttle code attempts server-side without storing raw client IPs. Production proxy must overwrite trusted address headers; do not trust arbitrary forwarded chains.
- Everyone unlocked shares the same full permissions. No separate Django admin login.
- Library: internal name, destination summary, type, total opens, last opened timestamp, on/off switch, edit, export and delete with explicit confirmation. Search and pagination; mobile layout must remain usable.
- Create QR opens a foreground modal. Edit uses the same modal with all fields, destination type dropdown and appearance. Changing any type preserves the public identifier, URL and counts.
- Public IDs are cryptographically random, never names/emails, and never deliberately recycled.
- Disabling is reversible. Disabled/deleted/unknown destinations do not expose content. Permanent deletion breaks the old QR link and removes its content.
- Appearance changes only affect future downloads, not existing printed copies.

## Persistent destinations and counters

- Website: temporary HTTP redirect to a validated HTTP(S) URL, no cached permanent redirect.
- vCard: public contact page showing all populated fields, including notes/custom fields, with Save contact delivering a valid .vcf file. Never auto-save to a device.
- Other types: a public content/action page appropriate to the type. Use user-activated links for phone/SMS/email/WhatsApp/location, copy controls for text/network details and an .ics download for events. Do not assume a webpage can configure Wi-Fi automatically.
- Count successful GET opens at the stable entry URL only. HEAD, preview, QR export and secondary vCard/calendar downloads do not add opens. Count using an atomic database increment and retain last-opened time. No visitor identity, raw IP, event timeline or chart storage.
- No authentication is required to open an active persistent destination; anyone with its URL can see its data.

## Excel

- Unlocked users only; vCard and website imports, static or persistent output.
- .xlsx upload, worksheet selection, sample preview, editable column mapping, per-row validation, explicit confirmation and ZIP output plus report.
- Proposed technical limits: 5 MiB compressed workbook, 40 MiB expanded content, 500 data rows, 100 columns, 20 worksheets. Reject oversized input before processing. Reject formulas/error cells; preserve text phone numbers and warn about numeric phone cells.
- Duplicate names never overwrite exports. Duplicate column mapping fails validation.
- Work in bounded batches with progress and cancellation. Preserve completed results and make retries idempotent. Persistent valid rows also enter the shared library. Intentional reimport creates new codes, never updates existing ones silently.
- Temporary staging/export artifacts expire after 24 hours; every access checks authorization and expiry. Static batch results are temporary, not a QR history.

## Architecture and release

- New independent repository and clean history, Python/Django templates plus CSS and small JavaScript modules, PostgreSQL, Docker Compose. No Qt runtime and no separate frontend build required.
- Implement all code and tests from scratch. Do not reuse any previous project source, tests, history, data or deployment configuration.
- Public repository contains only generic example configuration and synthetic fixtures. No actual deployment domain, infrastructure identifiers, personal contact data, credentials, absolute workstation paths or production URLs in source, history or CI logs. Commit with GitHub noreply metadata.
- Secrets and deployment values live in Portainer/private configuration. Generate a fresh production code; never use the preview code.
- App and database use internal Docker networking; only the reverse proxy exposes HTTPS. Stable public base URL is configured privately.
- CI on main runs tests/lint, builds and smoke-tests Docker, then promotes the tested source commit into the Portainer manifest. Portainer polls the source and rebuilds the exact tested commit. Failed or stale CI cannot promote an older release.
- Database migrations run before serving. Backup before migrations and daily backups with bounded retention; check an isolated restore. Off-host backup is a separate operational choice, not assumed configured.
- Prove one real automatic update by committing a new release after the first deployment, checking deployed revision, health and preservation of a synthetic persistent link. CI success alone is not deployment success.

## Acceptance evidence

Automated payload/QR decode/security/import/counter tests; real browser flows on desktop/mobile light/dark; production HTTPS and code gate; stable link after destination change and restart/update; backup restore; public repository and workflow-output audit. Report physical iPhone/Android scan tests as unverified unless actually performed.
