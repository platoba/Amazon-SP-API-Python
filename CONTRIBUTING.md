# Contributing

Thanks for considering a contribution! Here's how to get started.

## Setup

```bash
git clone https://github.com/platoba/Amazon-SP-API-Python.git
cd Amazon-SP-API-Python
pip install -e ".[dev]"
```

## Development Workflow

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Write code + tests
3. Run checks: `make check` (lint + test)
4. Commit with conventional message: `feat: add X` / `fix: resolve Y`
5. Open a PR against `main`

## Code Style

- **Formatter**: `ruff format` (line length 100)
- **Linter**: `ruff check` (E, F, I, W rules)
- **Docstrings**: Google style with Args/Returns sections

## Testing

- All new features must include tests
- Tests use `pytest` with fixtures from `tests/conftest.py`
- Run: `make test` or `make test-cov` for coverage
- Target: ≥85% coverage

## Adding a New API Module

1. Create `sp_api/your_module.py` inheriting from `BaseAPI`
2. Add the mixin to `SPAPIClient` in `sp_api/client.py`
3. Create `tests/test_your_module.py`
4. Update `CHANGELOG.md`

## Project Structure

```
sp_api/
  __init__.py       # Public API
  client.py         # Main client (composes all modules)
  base.py           # BaseAPI mixin
  auth.py           # OAuth2 token management
  rate_limiter.py   # Rate limiting
  cache.py          # Response caching
  batch.py          # Batch operations
  export.py         # CSV/JSON/JSONL export
  orders.py         # Orders API
  catalog.py        # Catalog Items API
  ...               # Other API modules
tests/
  conftest.py       # Shared fixtures
  test_*.py         # Test files
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
