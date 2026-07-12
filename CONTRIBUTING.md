# Contributing

Thank you for considering contributing to eBay Sniper! This document outlines how to contribute.

## Getting Started

### Prerequisites
- Python 3.12+ or Docker
- eBay Developer Account (for testing)
- git

### Development Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ebay-sniper

# Copy environment template
cp .env.example .env.local
# Edit .env.local with your eBay credentials

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .[dev]

# Run tests
pytest tests/

# Run the service
python -m sniper.main
```

### Docker Development

```bash
# Build and start
docker compose up -d

# Run tests in container
docker compose exec sniper pytest tests/

# View logs
docker compose logs -f sniper
```

## Project Structure

```
ebay-sniper/
├── src/sniper/
│   ├── core/           # Core logic (db, sniper, auth, ebay_client, ntp)
│   ├── web/            # FastAPI app + templates
│   ├── scheduler.py    # APScheduler setup
│   ├── telegram_bot.py # Telegram bot
│   ├── cli.py          # CLI (Typer)
│   ├── mcp_server.py   # MCP server
│   └── main.py         # Entry point
├── tests/              # Unit tests
├── docs/               # Documentation
├── skill/              # Hermes skill
├── pyproject.toml      # Project dependencies
├── Dockerfile          # Container build
└── docker-compose.yml  # Orchestration
```

## Code Style

### Python
- Follow [PEP 8](https://peps8.org/)
- Use [Black](https://github.com/psf/black) for formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use type hints where appropriate
- Max line length: 100 characters

### Running Formatters
```bash
# Format code
black src/ tests/
isort src/ tests/

# Check formatting
black --check src/ tests/
isort --check-only src/ tests/
```

### Pre-commit Hooks (Recommended)
The project uses pre-commit hooks to enforce code quality. Install them before pushing changes:

```bash
# Install pre-commit framework
pip install pre-commit

# Install project hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

Hooks run automatically on `git commit`. CI also runs the same checks, so fix any failures before pushing.

### Testing
- Write tests for new features
- Use pytest for test framework
- Aim for >80% code coverage
- Test both success and error paths

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/sniper --cov-report=html

# Run specific test
pytest tests/test_sniper.py::test_add_watch
```

## Making Changes

### Branch Naming
Use descriptive branch names:
- `feature/feature-name`
- `fix/bug-description`
- `docs/documentation-update`

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

Examples:
```
feat(cli): add bulk watch command

Add support for adding multiple watches at once via CLI.

Closes #42
```

```
fix(auth): handle expired user token gracefully

Add retry logic when user token is expired and needs refresh.
```

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/update tests
5. Update documentation if needed
6. Ensure all tests pass
7. Submit a pull request

PR Description Template:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested your changes

## Checklist
- [ ] Code follows project style
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
```

## Development Workflow

### Adding a New Feature

1. **Create an issue** (if not already exists)
2. **Create branch** from `master`
3. **Implement feature** following code style
4. **Add tests** for the feature
5. **Update documentation** (README, ARCHITECTURE.md, etc.)
6. **Run tests** to ensure nothing breaks
7. **Submit PR** with clear description

### Fixing a Bug

1. **Create issue** describing the bug
2. **Create branch** for the fix
3. **Add test** that reproduces the bug
4. **Fix the bug**
5. **Verify test passes**
6. **Submit PR** referencing the issue

### Updating Dependencies

1. **Update pyproject.toml** with new versions
2. **Test locally** to ensure compatibility
3. **Run full test suite**
4. **Submit PR** with changelog notes

## Areas Needing Help

See [GitHub Issues](https://github.com/<your-username>/ebay-sniper/issues) for current needs.

Common areas:
- **Tests**: Improve test coverage
- **Documentation**: Clarify confusing sections
- **Bug fixes**: Address reported issues
- **Features**: Implement requested features

## Important Notes

### Bid Placement Stub
Remember that bid placement is stubbed until eBay grants the `buy.offer.auction` scope. When implementing bid-related features:
- Work with the stub in place
- Code should work with both stubbed and live modes
- Document any scope-related requirements

### Testing with Real eBay API
- Use sandbox credentials for testing when possible
- Rate limit your requests
- Don't add real watches for expensive items during testing
- Clean up test data

### Docker Changes
- Test Dockerfile changes locally
- Ensure docker-compose.yml works
- Update documentation if deployment changes

### Breaking Changes
- Document clearly in PR description
- Update migration guide if needed
- Consider backward compatibility

## Questions?

- Check existing [GitHub Issues](https://github.com/<your-username>/ebay-sniper/issues)
- Review [docs/](docs/) for detailed information
- Open a new issue if you can't find an answer

## License

By contributing, you agree that your contributions will be licensed under the MIT License.