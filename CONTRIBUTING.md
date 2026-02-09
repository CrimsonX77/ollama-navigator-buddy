# Contributing to Ollama Navigator Buddy

Thank you for your interest in contributing to Ollama Navigator Buddy! We welcome contributions from the community and are excited to see what you'll bring to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## 🤝 Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences
- Accept responsibility for mistakes and learn from them

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ollama-navigator-buddy.git
   cd ollama-navigator-buddy
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/CrimsonX77/ollama-navigator-buddy.git
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 💡 How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check the existing issues to avoid duplicates
- Collect information about your environment
- Try to isolate the problem

When creating a bug report, include:
- **Clear title**: Descriptive and specific
- **Description**: What happened vs. what you expected
- **Steps to reproduce**: Detailed, numbered steps
- **Environment**: OS, versions, configuration
- **Logs/Screenshots**: Any relevant error messages or visuals

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been suggested
- Provide a clear use case
- Explain why this feature would be useful
- Consider possible implementations

### Contributing Code

We accept pull requests for:
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements
- Code refactoring

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+ or Node.js 16+
- Ollama installed and running
- Git

### Initial Setup

1. **Install dependencies**:
   ```bash
   # Python
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   
   # Node.js
   npm install
   ```

2. **Configure the application**:
   ```bash
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

3. **Install Ollama models**:
   ```bash
   ollama pull llama3
   ```

4. **Run tests** to ensure everything is working:
   ```bash
   # Python
   pytest
   
   # Node.js
   npm test
   ```

## 🔄 Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests** and ensure they pass:
   ```bash
   # Python
   pytest
   
   # Node.js
   npm test
   ```

3. **Run linters** to check code style:
   ```bash
   # Python
   flake8 .
   black .
   
   # Node.js
   npm run lint
   ```

4. **Update documentation** if needed

5. **Add tests** for new features

### Submitting

1. **Commit your changes** with clear messages:
   ```bash
   git add .
   git commit -m "feat: add natural language search feature"
   ```
   
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `style:` for formatting changes
   - `refactor:` for code refactoring
   - `test:` for adding tests
   - `chore:` for maintenance tasks

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Open a Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Describe what changes you made and why
   - Reference any related issues
   - Add screenshots for UI changes
   - Mark as draft if work is in progress

### Review Process

1. A maintainer will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged
4. Your contribution will be acknowledged

## 📝 Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function signatures
- Use docstrings for modules, classes, and functions
- Maximum line length: 88 characters (Black default)
- Use meaningful variable names

Example:
```python
def search_files(query: str, max_results: int = 10) -> list[dict]:
    """
    Search for files matching the given query.
    
    Args:
        query: Natural language search query
        max_results: Maximum number of results to return
        
    Returns:
        List of matching file information dictionaries
    """
    # Implementation
    pass
```

### JavaScript/TypeScript

- Follow ESLint recommended rules
- Use modern ES6+ syntax
- Prefer `const` over `let`, avoid `var`
- Use JSDoc comments for functions
- Maximum line length: 100 characters
- Use meaningful variable names

Example:
```javascript
/**
 * Search for files matching the given query
 * @param {string} query - Natural language search query
 * @param {number} maxResults - Maximum number of results
 * @returns {Promise<Array>} List of matching files
 */
async function searchFiles(query, maxResults = 10) {
  // Implementation
}
```

### General Principles

- Write self-documenting code
- Keep functions small and focused
- Avoid deep nesting (max 3-4 levels)
- Handle errors gracefully
- Log appropriately (debug, info, warning, error)
- Don't commit commented-out code
- Remove console.log/print statements before committing

## 🧪 Testing Guidelines

### Test Coverage

- Aim for >80% code coverage
- Write tests for all new features
- Update tests when modifying existing features
- Include edge cases and error conditions

### Test Structure

```python
# Python (pytest)
def test_search_files_basic():
    """Test basic file search functionality."""
    result = search_files("test query")
    assert isinstance(result, list)
    assert len(result) > 0
```

```javascript
// JavaScript (Jest)
describe('searchFiles', () => {
  it('should return an array of results', async () => {
    const results = await searchFiles('test query');
    expect(Array.isArray(results)).toBe(true);
    expect(results.length).toBeGreaterThan(0);
  });
});
```

### Running Tests

```bash
# Python
pytest                          # Run all tests
pytest tests/test_search.py     # Run specific test file
pytest -v                       # Verbose output
pytest --cov=.                  # With coverage

# Node.js
npm test                        # Run all tests
npm test -- --coverage          # With coverage
npm test -- --watch             # Watch mode
```

## 📚 Documentation

### Code Documentation

- Add docstrings/JSDoc to all public functions and classes
- Explain complex logic with inline comments
- Update API documentation when adding/changing endpoints

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update configuration documentation
- Create tutorials for complex features

### Commit Messages

Write clear commit messages:
```
feat: add natural language file search

- Implement LLM-based query parsing
- Add file content indexing
- Include relevance scoring algorithm

Closes #123
```

## 🌐 Community

### Getting Help

- 💬 Open a [GitHub Discussion](https://github.com/CrimsonX77/ollama-navigator-buddy/discussions)
- 📝 Check existing issues and documentation
- 🐛 Report bugs via GitHub Issues

### Communication Channels

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and general discussion
- Pull Requests: Code contributions and reviews

## 🎉 Recognition

Contributors will be:
- Listed in the project's contributors section
- Acknowledged in release notes
- Credited in documentation (if significant contribution)

## 📄 License

By contributing to Ollama Navigator Buddy, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Ollama Navigator Buddy! Your efforts help make this project better for everyone. 🚀
