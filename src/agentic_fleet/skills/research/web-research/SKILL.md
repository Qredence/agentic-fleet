---
# Agent Skills Specification v1.0
skill_id: web-research
name: Web Research
version: 1.0.0
description: Perform comprehensive web research using browser and search tools
team_id: research
tags: [research, browser, search, information-retrieval]

# Hierarchical Context (Agent Skills Specification)
type: operational
category: research
specialization: web-research

# Knowledge Organization
knowledge:
  domain: web
  subdomains: [search, browsing, information-retrieval]
  knowledge_graph_relations:
    - relation: part_of
      target: information-gathering

# Relational Context
relational:
  depends_on: []
  composes_with: [data-extraction, document-processing]
  alternatives: [database-query, knowledge-base]
  related_skills: [code-review, data-analysis]

# Memory System Integration
memory_keys: [web-research, research, search, browser]
embedding_keywords: [web, research, search, browse, find, extract, information]

# Activation Context
trigger_patterns:
  - "research"
  - "look up"
  - "find information"
  - "search the web"
  - "browse"
  - "current information"

context_requirements:
  - browser_tool
  - search_tool
  - internet_access
---

# Purpose

Extract and synthesize information from web sources to answer user queries with current, accurate data. This skill enables agents to dynamically retrieve and incorporate external knowledge that may not be present in their training data.

## When to Use

Use this skill when you need to:

- **Obtain current information** not available in training data
- **Verify facts** and cross-reference claims
- **Explore topics** through discovery-based research
- **Find recent events** or developments
- **Gather competitive intelligence** or market information
- **Access primary sources** and authoritative documentation

## When NOT to Use

- When the answer is definitively known from training data
- When the task requires only internal/synthetic data
- When browsing would violate rate limits or access restrictions

---

# How to Apply

## Step-by-Step Process

1. **Formulate Search Strategy**
   - Identify key terms and concepts
   - Use specific queries for better results
   - Consider multiple search angles

2. **Execute Search**
   - Start with broad queries to identify relevant sources
   - Refine based on initial results
   - Use advanced search operators for precision

3. **Evaluate Sources**
   - Check domain credibility (edu, gov, established orgs)
   - Verify publication dates for currency
   - Cross-reference with other sources when possible

4. **Browse and Extract**
   - Focus on high-relevance pages
   - Extract key facts and supporting evidence
   - Note any conflicting information

5. **Synthesize and Document**
   - Organize findings logically
   - Provide citations with URLs
   - Distinguish facts from speculation
   - Highlight key takeaways

## Best Practices

- **Source credibility**: Prioritize authoritative sources
- **Verification**: Cross-reference important claims
- **Citation**: Always provide source links
- **Transparency**: Flag information uncertainty
- **Balance**: Present multiple perspectives when available

---

# Example

## Input Example

```
Task: Research quantum computing applications in medicine
Context: Need current applications, challenges, and future directions
```

## Expected Output Structure

```markdown
# Web Research Report: Quantum Computing in Medicine

## Executive Summary
[2-3 sentence overview of key findings]

## Current Applications
- Hospital/Institution Name: Application Description
- Research Center: Use Case
- [More applications...]

## Challenges
- Challenge 1: Description and impact
- Challenge 2: Description and impact

## Future Directions
- Emerging research areas
- Predicted developments

## Sources
1. [Title](URL) - Organization, Date
2. [Title](URL) - Organization, Date
```

---

# Constraints

## Technical Constraints

- Respect robots.txt and site terms of service
- Avoid excessive requests to any single domain
- Handle rate limiting gracefully
- Use appropriate timeouts for slow-loading pages

## Quality Constraints

- Verify source credibility before including information
- Distinguish between confirmed facts and speculation
- Provide direct links to primary sources when possible
- Flag any conflicting information from different sources
- Note information currency and potential staleness

## Ethical Constraints

- Do not bypass paywalls or access restrictions
- Respect copyright - quote reasonably, link to full sources
- Avoid scraping personal or private information
- Consider information provenance and potential biases

---

# Prerequisites

- `browser` tool with navigation capabilities
- `search` tool for web queries
- Internet connectivity
- Valid search API credentials if required

---

# Compatibility

- Works with standard web browsers
- Compatible with major search engines
- Requires no special server-side components
- Functions in restricted network environments with proxy configuration
