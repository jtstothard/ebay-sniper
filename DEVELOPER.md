# Developer Guide

This guide helps you reproduce the same quality checks that run in CI before you push code.

## Quick Reproduction Checklist

Before pushing a PR, run these commands locally:

```bash
# 1. Install development dependencies
pip install -e '.[dev]'
pip install pre-commit

# 2. Install pre-commit hooks (runs automatically on commit)
pre-commit install

# 3. Run all pre-commit checks manually
pre-commit run --all-files

# 4. Run tests
pytest tests/ -v

# 5. Run tests with coverage (optional, but recommended)
pytest tests/ --cov=src/sniper --cov-report=term
```

If all the above pass, your PR should clear CI checks.

## CI Workflow

GitHub Actions runs on every push to `master` and on all pull requests. The CI workflow:

1. **Sets up Python 3.13** - Matches the project's minimum version
2. **Installs dependencies** - Uses `[dev]` extras to get testing tools
3. **Runs pytest** - Executes all tests in `tests/` with verbose output
4. **Checks test coverage** - Generates coverage report and uploads to Codecov (optional)

## Pre-commit Hooks

The project uses pre-commit to enforce code quality automatically. Hooks run on every `git commit`:

| Hook | Purpose | What It Checks |
|------|---------|----------------|
| black | Code formatting | Ensures consistent formatting (100 char line length) |
| isort | Import sorting | Organizes imports alphabetically and by section |
| trailing-whitespace | Cleanliness | Removes trailing whitespace from lines |
| end-of-file-fixer | Cleanliness | Ensures files end with a newline |
| check-yaml | YAML syntax | Validates YAML files (docker-compose.yml) |
| check-toml | TOML syntax | Validates TOML files (pyproject.toml) |
| check-merge-conflict | Git hygiene | Detects leftover merge conflict markers |
| check-added-large-files | File size | Rejects files >1MB |
| pytest | Tests | Runs the full test suite |

### Skipping Hooks (Not Recommended)

If you absolutely need to skip hooks during commit:

```bash
git commit --no-verify -m "message"
```

CI will still run the same checks and fail if you push code that doesn't meet quality standards.

## Running Tests

### Basic Test Run

```bash
pytest tests/
```

### Verbose Output

```bash
pytest tests/ -v
```

### Specific Test File

```bash
pytest tests/test_sniper.py
```

### Specific Test Function

```bash
pytest tests/test_sniper.py::test_add_watch
```

### With Coverage Report

```bash
# Terminal report
pytest tests/ --cov=src/sniper --cov-report=term

# HTML report (opens in browser)
pytest tests/ --cov=src/sniper --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

### Stop on First Failure

```bash
pytest tests/ -x
```

### Run Only Tests Matching a Pattern

```bash
pytest tests/ -k "telegram"
```

## Formatting Code

### Format with Black

```bash
# Format all Python files
black src/ tests/

# Check format without changing files
black --check src/ tests/
```

### Sort Imports with isort

```bash
# Sort all imports
isort src/ tests/

# Check without changing files
isort --check-only src/ tests/
```

### Format Both Together

```bash
black src/ tests/ && isort src/ tests/
```

## Debugging Test Failures

### See Full Output on Failure

```bash
pytest tests/ -vv -s
```

### Enter Debugger on Failure

```bash
pytest tests/ --pdb
```

### Show Local Variables on Failure

```bash
pytest tests/ -l
```

## Common CI Issues and Fixes

### Issue: `black --check` fails in CI

**Fix locally:**
```bash
black src/ tests/
git commit -am "format: apply black formatting"
```

### Issue: `isort --check-only` fails in CI

**Fix locally:**
```bash
isort src/ tests/
git commit -am "style: sort imports"
```

### Issue: Tests pass locally but fail in CI

**Possible causes:**
- Python version mismatch (CI uses 3.13)
- Environment differences (missing dependencies)
- Race conditions in async tests

**Debugging:**
```bash
# Ensure you're on the right Python version
python --version  # Should be 3.13.x

# Clean install
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest tests/ -v
```

### Issue: Coverage is low

**Fix:**
- Add tests for uncovered code paths
- Ensure tests exercise both success and error cases
- Run `pytest tests/ --cov=src/sniper --cov-report=term-missing` to see which lines aren't covered

## Test Coverage Goals

- **Overall target:** 80%+ coverage
- **Priority areas:**
  - Core business logic (`src/sniper/core/sniper.py`, `src/sniper/core/ebay_client.py`)
  - Database operations (`src/sniper/core/db.py`)
  - Scheduler integration (`src/sniper/scheduler.py`)
  - Telegram bot commands (`src/sniper/telegram_bot.py`)

## CI Performance Notes

- CI typically completes in 30-60 seconds
- Caching is enabled for pip packages to speed up runs
- Tests run in parallel where possible (pytest-xdist could be added for larger suites)

## Getting Help

If you're stuck with CI or local testing:

1. Check existing GitHub Issues for similar problems
2. Review the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide
3. Open a new issue with:
   - Error message from CI logs
   - What you tried locally
   - Expected vs actual behavior