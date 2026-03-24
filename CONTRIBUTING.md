# Contributing to Clipder

Thank you for your interest in contributing!

## Development Setup

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/ClipApp.git
cd ClipApp
```

3. Install dependencies:
```bash
uv sync
cd frontend && npm install
```

4. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Run `ruff check .` before committing

### JavaScript/TypeScript
- Use ESLint + Prettier
- Run `npm run lint` before committing

## Commit Messages

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## Pull Request Process

1. Update documentation if needed
2. Ensure all tests pass
3. Request review from maintainers
4. Squash commits before merging

## Running Tests

```bash
# Backend tests
pytest

# Frontend build
cd frontend && npm run build
```

## Questions?

Open an issue for discussion before starting major changes.
