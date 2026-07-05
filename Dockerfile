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

# The AI host management module uses SSH for remote host inspection.
# Install the client in the runtime image so resource probes can run.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

# The runtime should have a real passwd entry for the user that owns the
# application process. SSH and a few OS-level calls rely on it.
RUN groupadd --gid 1000 apmatia \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/apmatia --shell /bin/bash apmatia

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
RUN chmod +x scripts/entrypoint.sh && mkdir -p /home/apmatia && chown -R apmatia:apmatia /home/apmatia

# Set PYTHONPATH so both the legacy `src.*` imports and the new `apmatia.*`
# package layout are discoverable.
ENV PYTHONPATH="/app:/app/src"

# Pass MODE to the container
ENV MODE="$MODE"

# Expose port
EXPOSE 8501

# Run the entrypoint script
USER apmatia
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
