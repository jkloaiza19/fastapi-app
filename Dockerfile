# Use an official Python image as a base
FROM python:3.11-slim AS builder

# Set environment variables
ENV POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
#RUN apt-get update \
#    && apt-get install -y --no-install-recommends curl \
#    && curl -sSL https://install.python-poetry.org | python3 - \
#    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -
# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy only the files needed to install dependencies
COPY pyproject.toml poetry.lock ./

# Install project dependencies in the virtual environment created by Poetry
RUN poetry install --no-root --only main --no-ansi

FROM python:3.11-slim AS runtime

# Copy Poetry environment from the builder stage
COPY --from=builder /app /app

WORKDIR /app

COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Set the entrypoint script to handle Alembic migrations
#COPY scripts/db_init.sh /scripts/db_init.sh
RUN chmod +x /scripts/db_init.sh

RUN sh -c "./scripts/db_init.sh"

# Set the entrypoint to run the entrypoint.sh script
#ENTRYPOINT ["/app/scripts/db_init.sh"]

# Define the startup command
CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]