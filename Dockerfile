# Use a slim Debian image as our base
# (we don't use a Python image because Python will be installed with uv)
FROM debian:bookworm-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed by our app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the fast Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy only the dependency definitions first to leverage Docker's layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install Python dependencies for production (exclude dev group)
RUN uv sync --no-group dev

# Copy the rest of the application code into the container
COPY . .

# Collect the static files
RUN uv run --no-sync python manage.py collectstatic --noinput

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run with gunicorn using auto-calculated workers (2*CPU+1)
# Use shell form to allow command substitution for dynamic worker calculation
CMD uv run --no-sync gunicorn \
    --bind 0.0.0.0:8000 \
    --workers $((2 * $(nproc) + 1)) \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    config.wsgi:application
