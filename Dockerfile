FROM python:3.14-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client ca-certificates && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home app
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY --chown=app:app . .
RUN mkdir -p /backups /app/staticfiles && chown -R app:app /backups /app/staticfiles
USER app
RUN SECRET_KEY=build-only-placeholder ACCESS_CODE=000000 LOCAL_TEST=1 DEBUG=1 python manage.py collectstatic --noinput --verbosity 0
ARG SOURCE_REVISION=development
ENV SOURCE_REVISION=$SOURCE_REVISION
EXPOSE 8000
CMD ["python", "scripts/start.py"]
