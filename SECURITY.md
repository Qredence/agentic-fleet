# Security Policy

## Supported Versions

| Version | Supported              |
| ------- | ---------------------- |
| 0.6.x   | ✅ Current release     |
| 0.5.x   | ⚠️ Security fixes only |
| < 0.5   | ❌ Unsupported         |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in AgenticFleet, please report it responsibly.

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities.
2. **GitHub Security Advisories**: Use [GitHub's private vulnerability reporting](https://github.com/Qredence/agentic-fleet/security/advisories/new) (preferred).
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 5 business days
- **Status Updates**: Every 7 days until resolution
- **Resolution Timeline**: Typically 30-90 days depending on severity

### Severity Classification

| Severity | Description                                 | Target Resolution |
| -------- | ------------------------------------------- | ----------------- |
| Critical | Remote code execution, data breach          | 7 days            |
| High     | Authentication bypass, privilege escalation | 14 days           |
| Medium   | Information disclosure, denial of service   | 30 days           |
| Low      | Minor issues, hardening recommendations     | 90 days           |

### Safe Harbor

We consider security research conducted in good faith to be authorized. We will not pursue legal action against researchers who:

- Make a good faith effort to avoid privacy violations and data destruction
- Only interact with accounts they own or have explicit permission to test
- Do not exploit vulnerabilities beyond demonstrating the issue
- Report findings promptly and provide reasonable time for remediation

## Security Best Practices for Users

### API Keys & Secrets

- Store `OPENAI_API_KEY`, `TAVILY_API_KEY`, and other secrets in environment variables
- Never commit `.env` files or secrets to version control
- Use separate API keys for development and production
- Rotate keys periodically and immediately if compromised

### Deployment

- Run behind a reverse proxy (nginx, Caddy) with TLS termination
- Enable CORS restrictions for production (`CORS_ALLOWED_ORIGINS`)
- Use network segmentation to limit API exposure
- Monitor logs for suspicious activity

### WebSocket Security

- The `/api/ws/chat` endpoint validates connection origins against `CORS_ALLOWED_ORIGINS`
- Localhost connections are allowed by default for development (`WS_ALLOW_LOCALHOST=true`)
- For production, set `CORS_ALLOWED_ORIGINS` explicitly and consider setting `WS_ALLOW_LOCALHOST=false`
- Set appropriate rate limits to prevent abuse (`MAX_CONCURRENT_WORKFLOWS`)

## Dependency Security

We use automated tools to monitor dependencies:

- **Bandit**: Static analysis for Python security issues (CI pipeline)
- **npm audit**: JavaScript dependency scanning

To check locally:

```bash
# Python
uv run bandit -r src/agentic_fleet

# JavaScript
cd src/frontend && npm audit
```

## Security Updates

Security patches are released as soon as possible after a vulnerability is confirmed. Subscribe to [GitHub releases](https://github.com/Qredence/agentic-fleet/releases) to be notified of security updates.
