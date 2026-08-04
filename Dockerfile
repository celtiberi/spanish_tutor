# ml_teacher — full-fidelity deploy (always-on FastAPI + WebSockets +
# durable disk). Vercel stays the HTTP-demo tier; this is the product.
FROM python:3.12-slim

WORKDIR /app

# Install the package (wheel force-include carries domain/, prompts/,
# PEDAGOGY.md — the runtime-read teaching data).
COPY pyproject.toml README.md ./
COPY tutor ./tutor
COPY domain ./domain
COPY prompts ./prompts
COPY PEDAGOGY.md ./PEDAGOGY.md
RUN pip install --no-cache-dir .

# Durable data (character sheet, session logs, grades) lives on the
# mounted volume via ML_TEACHER_DATA_DIR.
ENV HOST=0.0.0.0 \
    PORT=8080 \
    ML_TEACHER_DATA_DIR=/data

EXPOSE 8080
CMD ["python", "-m", "tutor.web_app"]
