# CI/CD Pipeline Documentation

## Overview
This project uses GitHub Actions for continuous integration and deployment. The CI pipeline runs automatically on every pull request and push to main/develop branches.

## Workflow File
Location: `.github/workflows/ci.yml`

## Pipeline Stages

### 1. Code Quality Checks (`code-quality`)
Ensures code follows project standards and best practices.

**Checks:**
- ✅ **Black** - Code formatting (PEP 8 compliant)
- ✅ **isort** - Import statement sorting
- ✅ **flake8** - Style guide enforcement and linting
- ✅ **mypy** - Static type checking

**Configuration Files:**
- `.flake8` - Flake8 rules and exclusions
- `pyproject.toml` - Black, isort, and mypy configurations

### 2. Security Scanning (`security`)
Identifies potential security vulnerabilities in code and dependencies.

**Checks:**
- 🔒 **Bandit** - Security issues in Python code
- 🔒 **Safety** - Known security vulnerabilities in dependencies

**Outputs:**
- `bandit-report.json` - Uploaded as artifact for review

### 3. Test Suite (`test`)
Runs all tests with code coverage reporting.

**Test Suite:**
- 32+ total tests
- Core tests: 8/8 passing (100%)
- Overall: 19/32 passing (59%)
- Coverage: Variable (depending on database/Redis availability)

**Test Categories:**
- Application core (health checks, CORS, rate limiting, 404s)
- Authentication (API key validation, protected endpoints)
- User management (CRUD operations)
- AI services (chat completion, RAG)
- OCR processing (image/PDF extraction, passport parsing)
- Cognito integration

**Features:**
- 🧪 **pytest** - Test execution
- 📊 **Coverage** - Code coverage reporting
- 🐘 **PostgreSQL** - Test database (Docker service)
- 🔴 **Redis** - Cache service (Docker service)
- ⚡ **pytest-asyncio** - Async test support
- 🌐 **httpx** - HTTP client for endpoint testing

**Environment Variables:**
```bash
DATABASE_URL=postgresql+asyncpg://testuser:testpass@localhost:5432/testdb
REDIS_URL=redis://localhost:6379
ENVIRONMENT=test
SECRET_KEY=test-secret-key-for-ci
JWT_SECRET_KEY=test-jwt-secret
API_KEYS=test-api-key-1,test-api-key-2
```

**Outputs:**
- Coverage XML report (uploaded to Codecov)
- HTML coverage report (uploaded as artifact)
- pytest JUnit XML report
- Test results summary

**See Also:** [TEST_RESULTS.md](../TEST_RESULTS.md) for detailed test report.

### 4. Docker Build (`docker-build`)
Validates that the Docker image builds successfully.

**Features:**
- 🐳 Builds Docker image
- ✅ Tests image validity
- 💾 Uses GitHub Actions cache for layer caching

### 5. Dependency Review (`dependency-review`)
Checks for security vulnerabilities in dependencies (PR only).

**Features:**
- Scans for known vulnerabilities
- Fails on moderate+ severity issues
- Provides detailed security reports

## Running Locally

### Install Development Dependencies
```bash
poetry install --with dev
```

### Run Individual Checks

**Code Formatting:**
```bash
# Check formatting
poetry run black --check .

# Auto-format code
poetry run black .
```

**Import Sorting:**
```bash
# Check imports
poetry run isort --check-only .

# Fix imports
poetry run isort .
```

**Linting:**
```bash
poetry run flake8 .
```

**Type Checking:**
```bash
poetry run mypy .
```

**Security Scan:**
```bash
# Bandit
poetry run bandit -r . -x ./tests,./alembic

# Safety
poetry run safety check
```

**Run Tests:**
```bash
# Run all tests
poetry run pytest

# With coverage
poetry run pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Pre-commit Hooks

### Setup
```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files
```

### What it does
Pre-commit hooks run automatically before each commit:
1. Removes trailing whitespace
2. Fixes end-of-file
3. Validates YAML, JSON, TOML
4. Checks for large files
5. Runs Black
6. Runs isort
7. Runs flake8
8. Runs mypy
9. Runs Bandit

### Skip hooks (not recommended)
```bash
git commit --no-verify -m "message"
```

## CI/CD Best Practices

### Branch Protection Rules
Recommended settings for `main` branch:
- ✅ Require pull request reviews
- ✅ Require status checks to pass (all CI jobs)
- ✅ Require branches to be up to date
- ✅ Require linear history
- ❌ Allow force pushes

### Pull Request Workflow
1. Create feature branch from `develop`
2. Make changes
3. Commit with descriptive messages
4. Push to GitHub
5. Create PR to `develop`
6. CI runs automatically
7. Address any failures
8. Request review
9. Merge after approval and passing checks

### Fixing CI Failures

#### Black Formatting Failure
```bash
poetry run black .
git add .
git commit -m "Fix code formatting"
```

#### isort Failure
```bash
poetry run isort .
git add .
git commit -m "Fix import sorting"
```

#### flake8 Linting Failure
Review the errors and fix manually:
```bash
poetry run flake8 .
# Fix issues in code
git add .
git commit -m "Fix linting issues"
```

#### Test Failures
```bash
# Run tests locally to debug
poetry run pytest -v

# Run specific test
poetry run pytest tests/test_file.py::test_function -v

# Run with debugging
poetry run pytest --pdb
```

#### Security Issues
Review Bandit report and fix:
```bash
poetry run bandit -r . -x ./tests,./alembic
# Fix security issues
```

## Environment Variables for CI

The CI pipeline requires certain environment variables. These are set in the workflow file for testing purposes.

**Production secrets should be stored in:**
- GitHub Secrets (for GitHub Actions)
- AWS Secrets Manager (for production)

### Adding Secrets to GitHub
1. Go to repository Settings
2. Navigate to Secrets and variables → Actions
3. Click "New repository secret"
4. Add secrets:
   - `CODECOV_TOKEN` (if using Codecov)
   - Other production secrets as needed

## Artifacts

CI generates artifacts that can be downloaded:

### Test Results
- `pytest-report.xml` - JUnit format test results
- `htmlcov/` - HTML coverage report

### Security Reports
- `bandit-report.json` - Security scan results

**Download artifacts:**
1. Go to Actions tab
2. Click on workflow run
3. Scroll to "Artifacts" section
4. Click to download

## Coverage Reporting

### Codecov Integration
The pipeline uploads coverage to Codecov automatically.

**Setup:**
1. Sign up at [codecov.io](https://codecov.io)
2. Add repository
3. Add `CODECOV_TOKEN` to GitHub secrets
4. Coverage badge available in Codecov dashboard

### Coverage Badge
Add to README.md:
```markdown
[![codecov](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repo)
```

## Troubleshooting

### Common Issues

**Issue: Poetry cache not working**
```yaml
# Clear cache by changing key in workflow
key: venv-${{ runner.os }}-${{ env.PYTHON_VERSION }}-v2-${{ hashFiles('**/poetry.lock') }}
```

**Issue: Tests failing on CI but passing locally**
- Check environment variables
- Verify database/Redis are running
- Check Python version matches

**Issue: Docker build fails**
- Test locally: `docker build -t test .`
- Check Dockerfile syntax
- Verify build context

**Issue: Workflow not triggering**
- Check branch names in workflow file
- Verify workflow file is in `.github/workflows/`
- Check YAML syntax

## Performance Optimization

### Cache Strategy
The workflow caches:
1. Poetry installation
2. Python dependencies (`.venv`)
3. Docker layers

### Parallel Execution
Jobs run in parallel:
- Code quality checks
- Security scans
- Tests
- Docker build

### Skip CI (when needed)
Add to commit message:
```bash
git commit -m "docs: update README [skip ci]"
```

## Extending the Pipeline

### Adding New Checks
Edit `.github/workflows/ci.yml`:

```yaml
new-check:
  name: New Check
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run new check
      run: echo "New check"
```

### Adding Deployment
Create new workflow file `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      # Deployment steps
```

## Monitoring

### GitHub Actions Dashboard
- View all workflow runs
- Check execution times
- Monitor success rates

### Notifications
Configure notifications in GitHub settings:
- Email notifications for failed runs
- Slack/Discord webhooks
- Custom integrations

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [pre-commit Documentation](https://pre-commit.com/)
