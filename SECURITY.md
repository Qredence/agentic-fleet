# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| < 0.5.0 | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via GitHub's Security Advisory feature:

1. Go to the [Security Advisories](https://github.com/Qredence/agentic-fleet/security/advisories) page
2. Click "New draft security advisory"
3. Provide a detailed description of the vulnerability
4. Include steps to reproduce if applicable
5. Suggest a fix if you have one

Alternatively, you can email security concerns to: <contact@qredence.ai>

### What to Include

Please include the following information:

- Type of vulnerability
- Full paths of affected source files
- Location of the affected code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

### Response Timeline

- We will acknowledge your report within **48 hours**
- We will provide a detailed response within **7 days**
- We will keep you updated on our progress
- Once the vulnerability is fixed, we will notify you and credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices

When using AgenticFleet:

1. **API Keys**: Never commit API keys or secrets to version control

   - Use `.env` files (which are .gitignored)
   - Use environment variables in production
   - Rotate keys regularly

2. **Dependencies**: Keep dependencies up to date

   - Enable Dependabot alerts
   - Review and merge security updates promptly
   - Run `uv sync` regularly to update lockfile

3. **Code Execution**: Automated interpreter tooling is disabled by default

   - If you re-enable execution, review generated code before running it
   - Prefer isolated environments (containers, sandboxes) for any execution
   - Set conservative timeout and resource limits to contain misbehaving code

4. **Input Validation**: Validate all user inputs
   - Sanitize inputs before passing to LLMs
   - Implement rate limiting
   - Monitor for malicious patterns

## Known Security Considerations

### LLM Security

- **Prompt Injection**: The system uses LLMs which may be susceptible to prompt injection attacks
- **Data Exposure**: Be careful about sensitive data in prompts and responses
- **Code Generation**: Generated code should be reviewed before execution

### External Dependencies

- **API Keys**: OpenAI and Azure API keys must be kept secure
- **Network Requests**: The Researcher agent makes external web requests
- **Data Storage**: Mem0 context provider stores conversation history

## Security Updates

Security updates will be released as:

- **Critical**: Immediate patch release (0.5.x)
- **High**: Next minor version (0.x.0)
- **Medium/Low**: Next regular release

## Disclosure Policy

We follow responsible disclosure:

1. Security issues are fixed in private
2. CVEs are requested when appropriate
3. Public disclosure happens after patch release
4. Credit is given to reporters (with permission)

## Compliance

This project aims to follow:

- OWASP Top 10 security practices
- Python security best practices
- Secure development lifecycle principles

## Contact

For security concerns, contact:

- Email: <contact@qredence.ai>
- GitHub Security Advisory: [Create Advisory](https://github.com/Qredence/agentic-fleet/security/advisories/new)

---

Thank you for helping keep AgenticFleet and its users safe!
