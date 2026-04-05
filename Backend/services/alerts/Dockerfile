
# The shared package is NOT copied in during the build — it is bind-mounted
# at runtime via docker-compose.yml. The pip install -e step below installs
# it as an editable package from the mounted path so Python can find it with
# a plain `from shared import ...` import.

FROM python:3.10-slim

WORKDIR /app

# Install service dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the shared package from the volume mount path.
# At build time the volume is not yet mounted, so we create a placeholder
# directory. The real shared code is present at runtime via the volume.
# Using pip install -e means Python resolves imports from /app/shared
# directly
RUN mkdir -p /app/shared && \
    touch /app/shared/__init__.py

# The actual `pip install -e /app/shared` runs via an entrypoint script
# so it executes after the volume is mounted (i.e. at container start,
# not at image build time).
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Copy the service application code
COPY app/ ./app/

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]