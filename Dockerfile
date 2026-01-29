# Use an official lightweight Python image from AWS ECR Public
FROM public.ecr.aws/docker/library/python:3.11-slim

# Set environment variables
ENV POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

# Copy pyproject.toml and poetry.lock to extract dependencies
COPY pyproject.toml poetry.lock ./

# Export dependencies from Poetry to requirements.txt
RUN poetry export --without-hashes --format=requirements.txt > requirements.txt

# Remove Poetry to keep the image lightweight
RUN rm -rf /root/.local

RUN echo "Checking requirements.txt contents:" && cat /app/requirements.txt

# Install dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Note: .env file is not copied as environment variables should be provided at runtime
# For local development, mount .env as a volume: -v $(pwd)/.env:/app/.env
# For production, use container orchestration secrets or environment variables

# Expose the port FastAPI will run on
EXPOSE 8000

# Start FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


## Use an official Python image as a base
#FROM python:3.11-slim AS builder
#
## Set environment variables
#ENV POETRY_VERSION=1.8.4 \
#    POETRY_VIRTUALENVS_IN_PROJECT=false \
#    POETRY_NO_INTERACTION=1 \
#    PYTHONUNBUFFERED=1
#
#WORKDIR /app
#
## Install system dependencies
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    libpq-dev \
#    curl \
#    && rm -rf /var/lib/apt/lists/*
#
#RUN curl -sSL https://install.python-poetry.org | python3 -
#
## Add Poetry to PATH
#ENV PATH="/root/.local/bin:$PATH"
#
## Set the working directory
#
## Copy pyproject.toml and poetry.lock to extract dependencies
#COPY pyproject.toml poetry.lock ./
#
#RUN poetry export --without-hashes --format=requirements.txt > requirements.txt
#
## Remove Poetry to keep the image clean
#RUN rm -rf /root/.local
#
## Install dependencies using pip
#RUN pip install --no-cache-dir -r requirements.txt
#
## Copy the rest of the application code
#COPY . .
#
## Copy the .env file generated in buildspec.yml
#COPY .env /app/.env
#
## Use a separate lightweight runtime image
#FROM python:3.11-slim AS runtime
#
#WORKDIR /app
#
## Copy application files from builder
#COPY --from=builder /app /app
#
## ✅ Install dependencies inside the runtime container
#RUN pip install --no-cache-dir -r /app/requirements.txt
#
## Copy the .env file generated in buildspec.yml
#COPY .env /app/.env
#
## Ensure `uvicorn` is available in PATH
#RUN ln -s /usr/local/bin/uvicorn /bin/uvicorn
#
## Expose the port FastAPI will run on
#EXPOSE 8000
#
## Define the startup command
#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]



# Use an official Python image as a base
#FROM python:3.11-slim AS builder
#
## Set environment variables
#ENV POETRY_VERSION=1.8.4 \
#    POETRY_VIRTUALENVS_IN_PROJECT=false \
#    POETRY_NO_INTERACTION=1 \
#    PYTHONUNBUFFERED=1
#
## Install dependencies
##RUN apt-get update \
##    && apt-get install -y --no-install-recommends curl \
##    && curl -sSL https://install.python-poetry.org | python3 - \
##    && rm -rf /var/lib/apt/lists/*
#
#RUN apt-get update && apt-get install -y \
#    build-essential \
#    libpq-dev \
#    curl \
#    && rm -rf /var/lib/apt/lists/*
#
#RUN curl -sSL https://install.python-poetry.org | python3 -
#
## Add Poetry to PATH
#ENV PATH="/root/.local/bin:$PATH"
#
## Set the working directory
#WORKDIR /app
#
## Copy only the files needed to install dependencies
#COPY pyproject.toml poetry.lock ./
#
## Install project dependencies in the virtual environment created by Poetry
#RUN poetry install --no-root --only main --no-ansi
#
#
#RUN pip install --no-cache-dir -r requirements.txt
#
#COPY . .
#
#COPY .env /app/.env
#
#FROM python:3.11-slim AS runtime
#
#WORKDIR /app
#
## Copy Poetry environment from the builder stage
#COPY --from=builder /app /app
#
## Expose the port FastAPI will run on
#EXPOSE 8000
#
## Define the startup command
#CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
