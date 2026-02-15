# 🧭 Ollama Navigator Buddy

***RECOMMENDED AGENT: https://ollama.com/CrimsonDragonX7/Luna

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

A reasoning-first, agentic desktop file navigator powered by local Ollama LLMs. Navigate your files intelligently using natural language with the power of local AI models.

## 🌟 Overview

Ollama Navigator Buddy is an intelligent file navigation system that leverages Large Language Models (LLMs) running locally via [Ollama](https://ollama.ai/) to help you interact with your filesystem using natural language. Instead of remembering complex file paths or using traditional file browsers, simply describe what you're looking for in plain English.

### Key Benefits

- 🔒 **Privacy-First**: All AI processing happens locally on your machine - no data leaves your computer
- 🧠 **Intelligent Understanding**: Understands context and intent, not just keywords
- 💬 **Natural Language**: Interact with your files using conversational commands
- ⚡ **Fast & Efficient**: Powered by local Ollama models for quick responses
- 🎯 **Agentic Behavior**: The AI reasons about your requests and takes appropriate actions

## ✨ Features

### Planned Features

- 📁 **Smart File Search**: Find files by description, not just name
- 🔍 **Contextual Navigation**: "Show me the documents I worked on last week"
- 📊 **File Analysis**: Get summaries and insights about file contents
- 🤖 **Task Automation**: "Organize my downloads folder by file type"
- 🗂️ **Intelligent Grouping**: Automatically categorize and tag files
- 💾 **History & Context**: Remember your navigation patterns and preferences
- 🎨 **Customizable Interface**: Adapt the UI to your workflow

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **[Ollama](https://ollama.ai/)** (v0.1.0 or higher)
  ```bash
  # macOS/Linux
  curl -fsSL https://ollama.ai/install.sh | sh
  
  # Or download from https://ollama.ai/download
  ```

- **Python 3.8+** (for Python implementation) or **Node.js 16+** (for JavaScript implementation)
  ```bash
  # Check your versions
  python --version
  node --version
  ```

- **Git**
  ```bash
  git --version
  ```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/CrimsonX77/ollama-navigator-buddy.git
   cd ollama-navigator-buddy
   ```

2. **Install dependencies**
   
   *Note: Installation instructions will be added once the codebase is developed*
   
   ```bash
   # For Python
   pip install -r requirements.txt
   
   # For Node.js
   npm install
   ```

3. **Pull required Ollama models**
   ```bash
   # Download a recommended model (e.g., Llama 3 or Mistral)
   ollama pull llama3
   # or
   ollama pull mistral
   ```

4. **Configure the application**
   
   Create a configuration file (details to be added):
   ```bash
   cp config.example.json config.json
   ```

### Quick Start

*Usage examples will be provided once the application is developed*

```bash
# Start the navigator
python main.py
# or
npm start
```

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────┐
│                  User Interface                      │
│            (CLI / GUI / Web Interface)               │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              Agent Controller                        │
│         (Reasoning & Decision Making)                │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│               Ollama Interface                       │
│          (Local LLM Communication)                   │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│            File System Layer                         │
│      (Navigation, Search, Operations)                │
└──────────────────────────────────────────────────────┘
```

### Components

- **Agent Controller**: Interprets user intent and coordinates actions
- **Ollama Interface**: Manages communication with local LLM
- **File System Layer**: Handles all file operations safely
- **Context Manager**: Maintains conversation and navigation history
- **Security Module**: Ensures safe file operations and prevents unauthorized access

## 🔧 Configuration

Configuration options will include:

- **Model Selection**: Choose your preferred Ollama model
- **Search Scope**: Define which directories to index
- **Response Style**: Adjust verbosity and formatting
- **Safety Settings**: Configure allowed operations
- **Performance**: Tune cache and indexing settings

Example configuration structure:
```json
{
  "ollama": {
    "model": "llama3",
    "host": "http://localhost:11434",
    "temperature": 0.7
  },
  "filesystem": {
    "allowed_paths": ["/home/user/Documents", "/home/user/Projects"],
    "excluded_patterns": ["node_modules", ".git", "__pycache__"],
    "max_depth": 10
  },
  "security": {
    "enable_file_operations": true,
    "require_confirmation": true,
    "restricted_operations": ["delete", "execute"]
  }
}
```

## 🔒 Security Considerations

### Current Security Status

✅ **No vulnerabilities detected** in the current codebase (repository is in initial state)

### Security Best Practices for Development

When developing this project, follow these security guidelines:

1. **Input Validation**
   - Sanitize all file paths to prevent directory traversal attacks
   - Validate user inputs before passing to LLM or filesystem
   - Implement allowlist for permitted operations

2. **File System Access**
   - Implement sandboxing for file operations
   - Use principle of least privilege
   - Never execute files without explicit user confirmation
   - Implement path canonicalization to prevent symlink attacks

3. **LLM Security**
   - Validate LLM outputs before executing commands
   - Implement command confirmation for destructive operations
   - Rate limit API calls to prevent resource exhaustion
   - Monitor for prompt injection attempts

4. **Configuration Security**
   - Never commit API keys or sensitive data to version control
   - Use environment variables for configuration
   - Implement secure default settings
   - Add `.env` and config files to `.gitignore`

5. **Dependencies**
   - Regularly audit dependencies for vulnerabilities
   - Use dependency scanning tools (e.g., npm audit, pip audit)
   - Keep Ollama and other dependencies up to date
   - Pin dependency versions for reproducibility

6. **Data Privacy**
   - Keep all processing local (no telemetry without consent)
   - Don't log sensitive file contents
   - Implement secure deletion for temporary files
   - Respect system file permissions

### Recommended `.gitignore` Entries

```
# Environment variables
.env
.env.local

# Configuration
config.json
config.local.json

# Dependencies
node_modules/
venv/
__pycache__/

# Build outputs
dist/
build/
*.pyc

# IDE
.vscode/
.idea/
*.swp

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db
```

## 🛠️ Development

### Setting Up Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ollama-navigator-buddy.git
   cd ollama-navigator-buddy
   ```

2. **Create a development branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Install development dependencies**
   ```bash
   # Python
   pip install -r requirements-dev.txt
   
   # Node.js
   npm install --include=dev
   ```

4. **Run tests**
   ```bash
   # Python
   pytest
   
   # Node.js
   npm test
   ```

### Code Style

- Follow PEP 8 for Python code
- Follow ESLint/Prettier for JavaScript/TypeScript code
- Write meaningful commit messages
- Add comments for complex logic
- Update documentation for API changes

### Testing

- Write unit tests for all new features
- Maintain test coverage above 80%
- Test edge cases and error conditions
- Include integration tests for critical paths

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report Bugs**: Open an issue with a clear description and reproduction steps
2. **Suggest Features**: Propose new features via GitHub issues
3. **Submit Pull Requests**: Fix bugs or implement features
4. **Improve Documentation**: Help make our docs better
5. **Share Feedback**: Tell us about your experience

### Pull Request Process

1. Ensure your code passes all tests and linting
2. Update documentation to reflect changes
3. Add tests for new functionality
4. Follow the existing code style
5. Write a clear PR description explaining your changes
6. Link related issues in your PR

## 📝 Roadmap

### Phase 1: Foundation (Current)
- [x] Project initialization
- [x] README and documentation
- [ ] Basic project structure
- [ ] Ollama integration
- [ ] Simple CLI interface

### Phase 2: Core Features
- [ ] Natural language file search
- [ ] Basic file operations
- [ ] Context-aware navigation
- [ ] Configuration system
- [ ] Error handling

### Phase 3: Advanced Features
- [ ] File content analysis
- [ ] Task automation
- [ ] GUI interface
- [ ] Plugin system
- [ ] Multi-model support

### Phase 4: Polish
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Extended documentation
- [ ] User tutorials
- [ ] Package distribution

## 📚 Resources

- [Ollama Documentation](https://github.com/ollama/ollama/tree/main/docs)
- [LangChain](https://python.langchain.com/) - Framework for LLM applications
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Crimson Valentine**

- GitHub: [@CrimsonX77](https://github.com/CrimsonX77)

## 🙏 Acknowledgments

- [Ollama](https://ollama.ai/) - For providing an excellent local LLM platform
- The open-source AI community
- All contributors to this project

## 💬 Support

If you need help or have questions:

- 📫 Open an issue on GitHub
- 💡 Check existing issues and discussions
- 📖 Read the documentation

## 🗺️ Project Status

**Status**: 🚧 In Development

This project is in its initial stages. The foundation is being laid, and core features are being planned. Contributions and feedback are welcome!

---

<div align="center">
Made with ❤️ and 🤖 by the Ollama Navigator Buddy team
</div>
