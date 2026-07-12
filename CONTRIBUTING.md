# Contributing to eBay Sniper

Thanks for your interest in contributing! This is a self-hosted project maintained by a single developer, so contributions are welcome but may take time to review.

## Setting Up Development

1. **Fork and clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ebay-sniper.git
   cd ebay-sniper
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your eBay credentials (needed for integration tests)
   ```

## Development Workflow

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write tests for new functionality
   - Ensure existing tests pass
   - Follow the existing code style

3. **Run tests**:
   ```bash
   pytest tests/
   ```

4. **Commit**:
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings for public functions

## Testing

- Write unit tests for new functionality
- Ensure `pytest tests/` passes before submitting
- For changes affecting eBay API interactions, document expected behavior with stub responses

## What We're Looking For

- Bug fixes
- Documentation improvements
- Feature additions that align with the project scope
- Performance improvements

## Scope and Support Boundaries

This project is designed for self-hosted use with the following scope:

**In Scope**:
- eBay UK auction monitoring
- Bid placement via eBay Offer API (currently stubbed pending scope grant)
- Multiple interfaces: web, CLI, Telegram, MCP
- Docker deployment

**Out of Scope**:
- Multi-user SaaS features
- Other eBay regional sites (UK only)
- Commercial auction platforms
- Analytics/dashboard features beyond basic watch management

## Security

If you find a security vulnerability, please follow the process in [SECURITY.md](SECURITY.md) rather than opening a public issue.

## Communication

- For bugs: Open an issue with reproduction steps
- For questions: Use GitHub Discussions (if enabled) or issues tagged `question`
- For PRs: Provide context on what problem your change solves

## License

By contributing, you agree that your contributions will be licensed under the MIT License.