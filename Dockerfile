# syntax=docker/dockerfile:1.7

FROM python:3.14-slim AS deps

WORKDIR /tmp/apmatia-deps

COPY requirements.txt requirements-dev.txt ./

# Keep downloaded wheels in the Docker build cache so repeated builds do not
# fetch the same dependencies again.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt -r requirements-dev.txt

FROM python:3.14-slim

ARG MODE=core

WORKDIR /app

COPY --from=deps /usr/local /usr/local

# Copy only the app sources and runtime files.
COPY .pytest.ini ./
COPY Dockerfile ./
COPY .streamlit/ .streamlit/
COPY assets/ assets/
COPY docs/VERSION ./VERSION
COPY start.sh ./
COPY scripts/ scripts/
COPY src/ src/
COPY tests/ tests/

# Make the entrypoint executable
RUN chmod +x scripts/entrypoint.sh && mkdir -p /home/apmatia && chmod 0777 /home/apmatia

# Set PYTHONPATH so 'src' module is discoverable
ENV PYTHONPATH="/app"

# Pass MODE to the container
ENV MODE="$MODE"

# Expose port
EXPOSE 8501

# Run the entrypoint script
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
