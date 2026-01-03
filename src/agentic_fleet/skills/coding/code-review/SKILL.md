---
# Agent Skills Specification v1.0
skill_id: code-review
name: Code Review
version: 1.0.0
description: Review code for quality, correctness, security, and best practices
team_id: coding
tags: [coding, review, quality, security, best-practices]

# Hierarchical Context (Agent Skills Specification)
type: operational
category: software_development
specialization: code-review

# Knowledge Organization
knowledge:
  domain: software
  subdomains: [code-quality, security, testing]
  knowledge_graph_relations:
    - relation: part_of
      target: software-development
    - relation: enables
      target: continuous-integration

# Relational Context
relational:
  depends_on: []
  composes_with: [testing, documentation]
  alternatives: [self-review, automated-linting]
  related_skills: [web-research, data-analysis]

# Memory System Integration
memory_keys: [code-review, review, quality, security, coding]
embedding_keywords: [code, review, quality, security, bug, vulnerability, best-practices]

# Activation Context
trigger_patterns:
  - "review"
  - "look at my code"
  - "check for bugs"
  - "security audit"
  - "code quality"
  - "pull request"

context_requirements:
  - code_access
  - diff_viewer
  - language_knowledge
---

# Purpose

Systematically review code changes to identify bugs, security vulnerabilities, style issues, and opportunities for improvement. This skill ensures code quality through thorough, constructive examination of code artifacts.

## When to Use

Use this skill when you need to:

- **Pre-merge quality gates** before accepting pull requests
- **Post-feature verification** after implementing new functionality
- **Refactoring validation** when modifying existing codebases
- **Security assessments** to identify vulnerabilities
- **Compliance checks** against coding standards
- **Knowledge transfer** through documented review feedback

## When NOT to Use

- When only minor style nitpicks are needed (use linters instead)
- When the code is clearly prototype/experimental code
- When rapid iteration is needed over thoroughness
- Without access to the full context of changes

---

# How to Apply

## Step-by-Step Process

1. **Understand Context**
   - Review PR/commit description and motivation
   - Identify the scope of changes
   - Note any related issues or PRs

2. **Structural Analysis**
   - Check file organization and module boundaries
   - Verify proper error handling patterns
   - Assess code complexity and readability

3. **Logic Verification**
   - Trace critical code paths
   - Identify edge cases and boundary conditions
   - Verify error handling completeness

4. **Security Review**
   - Check for injection vulnerabilities (SQL, XSS, command)
   - Verify authentication/authorization logic
   - Assess dependency security implications

5. **Quality Assessment**
   - Evaluate test coverage and quality
   - Check documentation completeness
   - Assess adherence to project conventions

6. **Provide Feedback**
   - Categorize issues by severity
   - Distinguish blocking issues from suggestions
   - Offer concrete improvement alternatives

## Best Practices

- **Be constructive**: Frame feedback as opportunities
- **Prioritize**: Focus on correctness > security > style
- **Be specific**: Point to exact lines, don't generalize
- **Explain why**: Help authors understand the reasoning
- **Consider context**: Balance ideals with project reality

---

# Example

## Input Example

```
Task: Review the implementation of the auth module
Context: This PR adds JWT-based authentication to the API
Files changed: auth.py, middleware.py, tests/test_auth.py
```

## Expected Output Structure

```markdown
# Code Review: Auth Module

## Summary
Overall assessment with severity rating

## Critical Issues (Blocking)
- [Issue description with line reference]
- [Fix recommendation]

## Major Issues (Important)
- [Issue description with line reference]
- [Fix recommendation]

## Minor Issues (Suggestions)
- [Issue description]
- [Optional improvement]

## Positive Observations
- What's done well in this code

## Testing Concerns
- Gaps in test coverage
- Recommended additional test cases

## Final Recommendation
Approve / Request Changes / Approve with Comments
```

---

# Constraints

## Review Scope Constraints

- Focus on code within the changed files
- Don't reinvent the wheel - respect existing patterns
- Consider the PR scope, not ideal architecture

## Feedback Constraints

- Be constructive and respectful in tone
- Focus on patterns, not nitpicking style
- Distinguish between required changes and suggestions
- Provide actionable recommendations, not just criticism

## Technical Constraints

- Check for compliance with project coding standards
- Verify security implications of dependencies
- Consider performance implications of changes
- Validate error handling completeness

## Ethical Constraints

- Maintain confidentiality of proprietary code
- Avoid making personal attacks or negative comments
- Recognize that code review is a collaborative process
- Consider the author's perspective and constraints

---

# Prerequisites

- Access to code diffs/changed files
- Knowledge of programming language(s) involved
- Understanding of project coding standards
- Security awareness for vulnerability identification

---

# Compatibility

- Works with standard diff formats (git, GitHub, GitLab)
- Compatible with all programming languages
- Integrates with CI/CD quality gates
- Functions with or without static analysis tools
