# Security Policy

## Supported Versions

This project is currently in early development. Security updates will be provided for the latest version.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 🔒 Private Disclosure

**DO NOT** open a public issue for security vulnerabilities.

1. **Report via GitHub Security Advisories**
   - Navigate to the [Security tab](https://github.com/CrimsonX77/ollama-navigator-buddy/security)
   - Click "Report a vulnerability"
   - Provide detailed information about the vulnerability

2. **Email Report** (Alternative)
   - Contact the maintainer directly through GitHub
   - Include detailed steps to reproduce the issue
   - Provide any relevant proof-of-concept code

### 📋 What to Include

When reporting a vulnerability, please include:

- **Description**: Clear description of the vulnerability
- **Impact**: Potential impact and severity
- **Reproduction**: Step-by-step instructions to reproduce
- **Environment**: OS, version, configuration details
- **Proof of Concept**: Code or commands demonstrating the issue (if applicable)
- **Suggested Fix**: Any ideas for remediation (optional)

### ⏱️ Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Status Updates**: Every week until resolved
- **Fix Release**: Depends on severity (critical issues prioritized)

### 🎯 Scope

#### In Scope
- File system access vulnerabilities
- Path traversal issues
- Command injection vulnerabilities
- Prompt injection attacks affecting security
- Authentication/authorization bypasses
- Information disclosure
- Dependency vulnerabilities

#### Out of Scope
- Issues in third-party dependencies (report to upstream)
- Social engineering attacks
- Denial of service via resource exhaustion (expected behavior for local apps)
- Issues requiring physical access to the machine
- Issues in unsupported versions

## Security Best Practices for Users

### Installation
1. **Verify Downloads**: Always download from official sources
2. **Check Signatures**: Verify package signatures when available
3. **Review Permissions**: Understand what access the application needs

### Configuration
1. **Restrict File Access**: Only grant access to necessary directories
2. **Use Strong Paths**: Use absolute paths with no wildcards in critical configs
3. **Enable Confirmations**: Keep `require_confirmation` enabled for destructive operations
4. **Review Logs**: Periodically check logs for suspicious activity

### Operation
1. **Keep Updated**: Always use the latest version
2. **Monitor Ollama**: Ensure Ollama is also kept up to date
3. **Limit Scope**: Don't run with elevated privileges unless necessary
4. **Backup Data**: Maintain backups before using file operation features

## Security Features

### Current Implementation

- ✅ **Local Processing**: All AI operations happen locally via Ollama
- ✅ **No Telemetry**: No data is sent to external servers
- ✅ **MIT License**: Open source for transparency

### Planned Security Features

- 🔄 **Path Validation**: Prevent directory traversal attacks
- 🔄 **Operation Sandboxing**: Limit file system access
- 🔄 **Confirmation Prompts**: Require user confirmation for destructive actions
- 🔄 **Audit Logging**: Track all file operations
- 🔄 **Input Sanitization**: Validate all user inputs
- 🔄 **Command Allowlisting**: Only permit safe operations
- 🔄 **Secure Defaults**: Safe configuration out of the box

## Known Security Considerations

### LLM-Specific Risks

1. **Prompt Injection**: LLMs can be manipulated through crafted inputs
   - *Mitigation*: Input validation, output verification, confirmation prompts

2. **Path Confusion**: LLM might misinterpret file paths
   - *Mitigation*: Path canonicalization, allowlisted directories

3. **Unintended Actions**: AI might perform unexpected operations
   - *Mitigation*: Dry-run mode, confirmation prompts, operation logging

### File System Risks

1. **Privilege Escalation**: Risk of accessing unauthorized files
   - *Mitigation*: Respect system permissions, implement additional restrictions

2. **Data Loss**: Incorrect file operations could delete data
   - *Mitigation*: Confirmation prompts, trash/backup before delete, operation history

3. **Symbolic Links**: Symlinks could lead to unauthorized access
   - *Mitigation*: Resolve and validate canonical paths

## Security Roadmap

### Phase 1: Foundation (Current)
- [x] Security policy documentation
- [x] `.gitignore` for sensitive files
- [ ] Secure configuration system
- [ ] Input validation framework

### Phase 2: Core Security
- [ ] Path validation and sanitization
- [ ] Operation sandboxing
- [ ] Confirmation system
- [ ] Audit logging

### Phase 3: Advanced Security
- [ ] Privilege separation
- [ ] Security testing suite
- [ ] Penetration testing
- [ ] Third-party security audit

## Contact

For security concerns, please use the private disclosure methods above rather than public channels.

## Acknowledgments

We appreciate responsible disclosure and will acknowledge security researchers who help improve our security (with permission).

---

**Last Updated**: February 2026
