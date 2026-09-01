FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
EXPOSE 8000
# Alembic is the single source of truth for the schema (see docs/phase-2.md) --
# apply migrations before serving so a fresh or upgraded database is always
# ready by the time the app answers its first request.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]