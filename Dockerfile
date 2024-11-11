# Use an official Python image as a base
FROM python:3.9-slim AS builder

# Set environment variables
ENV POETRY_VERSION=1.6.1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Install dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && rm -rf /var/lib/apt/lists/*

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set the working directory
WORKDIR /app

# Copy only the files needed to install dependencies
COPY pyproject.toml poetry.lock ./

# Install project dependencies in the virtual environment created by Poetry
RUN poetry install --no-root --only main

# Use a smaller image for the final build
FROM python:3.9-slim AS runtime

# Copy Poetry environment from the builder stage
COPY --from=builder /app /app

# Copy FastAPI app code
COPY . /app

# Set the working directory
WORKDIR /app

# Expose the port FastAPI will run on
EXPOSE 8000

# Define the startup command
CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
