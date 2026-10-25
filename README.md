# vcard2qr-webapp

A public static QR generator with a shared, code-protected workspace for editable links. Built from scratch with Django, PostgreSQL and a lightweight browser interface.

## Features

- vCard, websites, text, Wi-Fi, email, phone, SMS, location, calendar events and WhatsApp.
- PNG/SVG export, clipboard images, colors, transparency and rounded modules.
- Six-digit unlock, 24-hour revocable sessions, shared searchable library, editable destinations and on/off switches.
- Stable random links, total opens and last-opened timestamps; no visitor profiles.
- Excel templates, worksheet preview and column mapping, validation, cancellable batch processing and ZIP exports.
- Responsive UI, system light/dark theme and Montserrat typography.

## Run locally

Install Docker Compose. Copy `.env.example` into your private environment configuration and replace the placeholder secrets. Use `http://localhost:8098` for `PUBLIC_BASE_URL` in local development.

```sh
docker compose up --build
```

Open the app at `http://localhost:8098`. No administrator panel or separate accounts are required. Production access codes have no default and are never sent to the frontend. Changing `ACCESS_CODE` and redeploying revokes existing unlocked sessions. Changing database credentials requires updating the database user as well as deployment configuration.

## Development and checks

Python 3.14. Install `requirements.lock` and `requirements-test.txt` in an isolated environment. Provide a random `SECRET_KEY`, a test-only six-digit `ACCESS_CODE`, `DEBUG=1`, and PostgreSQL connection variables. `LOCAL_TEST=1` enables isolated SQLite for lightweight development, not production/concurrency validation.

```sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py test
ruff check .
ruff format --check .
python scripts/check_public_data.py --history
```

PostgreSQL CI also exercises concurrent opens, a production container and an isolated backup restore. QR tests decode PNG and rasterized SVG with ZXing.

## Behavior and limits

Static content is processed in memory and is not added to the library. Persistent content is accessible to anyone with its link. Wi-Fi details are therefore public to people holding a persistent Wi-Fi link. Direct static vCards are handled by the scanning device; persistent vCards show a contact page and Save contact action.

An open means a GET request to the stable link, not a unique person or confirmed physical scan. HEAD requests and secondary contact/calendar downloads are not counted. Editing a destination never changes its link; deleting it permanently breaks printed copies.

Excel supports vCard and websites, with 500 data rows per worksheet, 100 columns, 20 worksheets, 50,000 total cells, 5 MiB upload and 40 MiB expanded archive. Formulas are rejected. Temporary imports and rendered outputs expire after 24 hours; batches are capped at 64 MiB of rendered output. Completed rows remain downloadable after cancellation. Reimporting intentionally creates new codes.

Clipboard availability and contact/calendar import behavior depend on browser/device support. Scan-test exported codes before printing; transparent images need a light final surface.

See [operations](docs/OPERATIONS.md) for deployment, backups and automatic updates. Dependencies retain their respective licenses; no project license has been assigned.
