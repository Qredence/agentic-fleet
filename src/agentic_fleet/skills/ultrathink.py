"""
Ultrathink: Skill Hierarchical Context Organization & Skill Creator

This document synthesizes the Anthropic skill-creator pattern with a comprehensive
hierarchical context organization designed for memory systems, knowledge management,
and tooling integration.

================================================================================
PART 1: HIERARCHICAL CONTEXT ORGANIZATION
================================================================================

The hierarchical context is organized across five dimensions:

    ┌─────────────────────────────────────────────────────────────────┐
    │                    HIERARCHICAL PATH                            │
    │  type / category / specialization / [sub-specialization]        │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    KNOWLEDGE DOMAIN                             │
    │  domain / subdomains / knowledge_graph_relations                │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   RELATIONAL CONTEXT                            │
    │  depends_on / composes_with / alternatives / supersedes         │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   MEMORY SYSTEM INTEGRATION                     │
    │  memory_keys / embedding_keywords / trigger_patterns            │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    TOOLING & RESOURCES                          │
    │  scripts / references / assets / context_requirements           │
    └─────────────────────────────────────────────────────────────────┘

================================================================================
SKILL TYPE TAXONOMY (4 Primary Types)
================================================================================

┌─────────────────────────────────────────────────────────────────────────────┐
│ OPERATIONAL: Skills that perform actions (data, tools, automation)          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   DATA_PROCESSING                                                           │
│   ├── EXTRACTION  (web-scraping, api-extraction, database-query)            │
│   ├── TRANSFORMATION (format-conversion, data-cleaning, normalization)      │
│   ├── LOADING (database-write, file-storage, api-publish)                   │
│   └── VALIDATION (schema-validation, data-quality, verification)            │
│                                                                              │
│   RESEARCH                                                                 │
│   ├── WEB_RESEARCH (search, browse, fact-check)                             │
│   ├── DOCUMENT_RESEARCH (pdf-analysis, literature-review)                   │
│   └── MARKET_RESEARCH (competitor-analysis, trend-analysis)                 │
│                                                                              │
│   SOFTWARE_DEVELOPMENT                                                      │
│   ├── CODE_GENERATION (scaffolding, boilerplate, refactoring)               │
│   ├── CODE_REVIEW (security-audit, quality-check, bug-finding)              │
│   ├── TEST_GENERATION (unit-tests, integration-tests, e2e-tests)            │
│   └── DEPLOYMENT (containerization, ci-cd, infrastructure)                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ COGNITIVE: Skills that plan and reason                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PLANNING                                                                  │
│   ├── TASK_DECOMPOSITION (breakdown, sequencing, prioritization)            │
│   ├── RESOURCE_ALLOCATION (budgeting, scheduling, capacity-planning)        │
│   └── RISK_ASSESSMENT (threat-modeling, mitigation-planning)                │
│                                                                              │
│   REASONING                                                                 │
│   ├── CAUSAL_ANALYSIS (root-cause, impact-analysis, correlation)            │
│   ├── ANALOGICAL_REASONING (pattern-matching, case-based)                   │
│   └── ABDUCTIVE_REASONING (hypothesis-generation, inference)                │
│                                                                              │
│   DECISION_MAKING                                                           │
│   ├── COST_BENEFIT_ANALYSIS (roi-calculation, trade-off-analysis)           │
│   ├── MULTI_CRITERIA_DECISION (pareto-optimal, weighted-scoring)            │
│   └── STRATEGIC_PLANNING (roadmapping, goal-setting, alignment)             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ COMMUNICATION: Skills that generate and synthesize                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   GENERATION                                                                │
│   ├── TEXT_GENERATION (summarization, content-creation, drafting)           │
│   ├── CODE_GENERATION (programming, scripting, query-writing)               │
│   └── VISUAL_GENERATION (diagrams, charts, presentations)                   │
│                                                                              │
│   SYNTHESIS                                                                 │
│   ├── SUMMARIZATION (abstractive, extractive, structured)                   │
│   ├── TRANSLATION (natural-languages, formats, protocols)                   │
│   └── AGGREGATION (meta-analysis, consolidation, fusion)                    │
│                                                                              │
│   COMMUNICATION_MANAGEMENT                                                  │
│   ├── DOCUMENTATION (technical-docs, api-docs, user-guides)                 │
│   ├── CORRESPONDENCE (email, messaging, reporting)                          │
│   └── PRESENTATION (storytelling, visualization, persuasion)                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ DOMAIN: Skills with domain-specific expertise                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   TECHNOLOGY                                                                │
│   ├── CLOUD_ARCHITECTURE (aws, azure, gcp, kubernetes)                      │
│   ├── SECURITY (iam, encryption, compliance, audit)                         │
│   └── DATA_ENGINEERING (etl, pipelines, warehouses, lakes)                  │
│                                                                              │
│   BUSINESS                                                                  │
│   ├── FINANCE (accounting, fp&a, treasury, tax)                             │
│   ├── MARKETING (seo, campaigns, analytics, conversion)                     │
│   └── OPERATIONS (logistics, supply-chain, manufacturing)                   │
│                                                                              │
│   SCIENCE                                                                   │
│   ├── LIFE_SCIENCES (bioinformatics, genomics, pharma)                      │
│   ├── PHYSICAL_SCIENCES (physics, chemistry, materials)                     │
│   └── SOCIAL_SCIENCES (psychology, sociology, economics)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

================================================================================
KNOWLEDGE ORGANIZATION MODEL
================================================================================

The knowledge dimension captures what domains and subdomains a skill operates in:

    SkillKnowledge {
        domain: str,              // Primary domain (e.g., "software", "finance")
        subdomains: list[str],    // Hierarchy: ["data", "extraction", "web"]
        knowledge_graph_relations: list[{
            relation: str,        // "part_of", "enables", "depends_on", "produces"
            target: str,          // Target entity in knowledge graph
            weight: float,        // Relationship strength (0.0-1.0)
        }]
    }

Example:
{
    "domain": "software",
    "subdomains": ["development", "testing", "security"],
    "knowledge_graph_relations": [
        {"relation": "part_of", "target": "software-development-lifecycle", "weight": 1.0},
        {"relation": "enables", "target": "continuous-integration", "weight": 0.8},
        {"relation": "depends_on", "target": "code-analysis", "weight": 0.6}
    ]
}

================================================================================
RELATIONAL CONTEXT MODEL
================================================================================

The relational dimension captures how skills relate to each other:

    SkillRelationalContext {
        depends_on: list[str],       // Skills this skill requires
        composes_with: list[str],    // Skills this can combine with
        alternatives: list[str],     // Skills that serve similar purposes
        supersedes: list[str],       // Skills this replaces
        related_skills: list[str],   // Contextually related skills
    }

RELATIONSHIP TYPES:
┌──────────────────┬──────────────────────────────────────────────────────────┐
│ Relationship     │ Description                                              │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ depends_on       │ Required prerequisite skills                            │
│ composes_with    │ Skills that enhance this skill when combined            │
│ alternatives     │ Different approaches to similar problems                │
│ supersedes       │ Skills this skill renders obsolete                      │
│ related_skills   │ Skills in same domain/context but not dependent         │
└──────────────────┴──────────────────────────────────────────────────────────┘

================================================================================
PROGRESSIVE DISCLOSURE (Anthropic Pattern Integration)
================================================================================

The skill system uses a three-level loading system optimized for context efficiency:

┌─────────────────────────────────────────────────────────────────────────────┐
│ LEVEL 1: METADATA (~100 tokens)                                            │
│ ────────────────────────────────                                           │
│ Always loaded with skill metadata:                                          │
│ • skill_id, name, version, description                                     │
│ • hierarchical_path (type/category/specialization)                          │
│ • trigger_patterns (when to invoke)                                         │
│ • memory_keys (for retrieval)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ LEVEL 2: SKILL.md BODY (~5k tokens)                                        │
│ ────────────────────────────────                                           │
│ Loaded when skill triggers:                                                 │
│ • Purpose and when to use                                                   │
│ • How to apply (step-by-step)                                              │
│ • Constraints and prerequisites                                             │
│ • Examples and patterns                                                     │
│ • References to bundled resources                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ LEVEL 3: BUNDLED RESOURCES (unlimited)                                     │
│ ────────────────────────────────                                           │
│ Loaded on-demand:                                                           │
│ • scripts/ (executable code: Python, Bash, etc.)                           │
│ • references/ (documentation: schemas, APIs, policies)                     │
│ • assets/ (templates, configs, static files)                                │
└─────────────────────────────────────────────────────────────────────────────┘

================================================================================
DEGREES OF FREEDOM (Anthropic Pattern)
================================================================================

Skills should specify appropriate levels of autonomy:

┌──────────────────┬──────────────────────────────────────────────────────────┐
│ Freedom Level    │ When to Use                                              │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ HIGH FREEDOM     │ Multiple valid approaches, context-dependent decisions   │
│ Text-based       │ "Search for relevant sources using your best judgment"   │
│ ──────────────── │ ──────────────────────────────────────────────────────── │
│ MEDIUM FREEDOM   │ Preferred pattern exists, some variation acceptable      │
│ Pseudocode/Param │ "Extract text using pdfplumber.open(path).extract_text()"│
│ ──────────────── │ ──────────────────────────────────────────────────────── │
│ LOW FREEDOM      │ Fragile operations, consistency critical                 │
│ Specific Script  │ scripts/rotate_pdf.py --input=INPUT --degrees=90        │
└──────────────────┴──────────────────────────────────────────────────────────┘

================================================================================
SKILL CREATOR WORKFLOW (6 Steps - Anthropic Pattern)
================================================================================

STEP 1: UNDERSTAND
──────────────────
Input: Raw user request for a new skill
Output: task_summary, trigger_patterns, example_patterns, required_capabilities

Key questions:
• "What functionality should this skill support?"
• "Can you give examples of how this skill would be used?"
• "What would a user say that should trigger this skill?"

DSPy Signature: SkillUnderstandSignature

STEP 2: PLAN
────────────
Input: Task summary, required capabilities, existing skills
Output: skill_taxonomy, scripts_needed, references_needed, assets_needed

Key activities:
• Map to hierarchical taxonomy (type/category/specialization)
• Identify reusable resources across examples
• Avoid duplication with existing skills

DSPy Signature: SkillPlanSignature

STEP 3: INITIALIZE
──────────────────
Input: skill_name, skill_taxonomy, task_summary
Output: skill_directory, skill_yaml, script_templates, reference_templates

Creates:
• Skill directory structure
• SKILL.md template with frontmatter
• scripts/, references/, assets/ directories
• Example files

DSPy Signature: SkillInitializeSignature

STEP 4: EDIT
────────────
Input: skill_name, task_summary, example_patterns, capabilities
Output: skill_purpose, when_to_use, how_to_apply, example, constraints

Key activities:
• Generate full SKILL.md content
• Apply progressive disclosure
• Define degrees of freedom

DSPy Signature: SkillEditSignature

STEP 5: PACKAGE
───────────────
Input: skill_path, skill_content, skill_yaml
Output: validation_results, quality_score, improvement_suggestions, package_status

Validation checks:
• YAML frontmatter format and required fields
• Skill naming conventions and directory structure
• Description completeness and quality
• File organization and resource references

DSPy Signature: SkillPackageSignature

STEP 6: ITERATE (HITL Approval)
───────────────────────────────
Input: approval_request, human_feedback
Output: approval_status, approved_skill, revision_notes

Human-in-the-loop workflow:
• Submit for review
• Human evaluates: approve / reject / revision_requested
• Implement feedback
• Repeat until approved

================================================================================
MEMORY SYSTEM INTEGRATION
================================================================================

The hierarchical context is designed for efficient memory retrieval:

┌─────────────────────────────────────────────────────────────────────────────┐
│ SKILL MEMORY INDEX STRUCTURE                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ SkillMemoryIndex {                                                          │
│     skill_id: str,                                                          │
│     hierarchical_path: str,           // "operational/research/web-search"  │
│     embedding_vector: list[float],    // Semantic embedding                  │
│     keywords: list[str],              // Search keywords                     │
│     capability_tags: list[str],       // What the skill can do              │
│     domain_tags: list[str],           // Knowledge domains                   │
│     last_accessed: datetime,          // For recency weighting              │
│     usage_count: int,                 // For popularity weighting           │
│     success_rate: float               // For quality weighting              │
│ }                                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

RETRIEVAL STRATEGIES:
┌─────────────────────┬────────────────────────────────────────────────────────┐
│ Strategy            │ Description                                            │
├─────────────────────┼────────────────────────────────────────────────────────┤
│ By Hierarchy        │ Query by type/category/specialization                  │
│ By Keywords         │ Text match on memory_keys, embedding_keywords          │
│ By Capability       │ Filter by capability_tags                              │
│ By Domain           │ Filter by domain_tags                                  │
│ By Embedding        │ Vector similarity search                               │
│ Hybrid              │ Combine multiple strategies with scoring               │
└─────────────────────┴────────────────────────────────────────────────────────┘

================================================================================
TOOLING & RESOURCES
================================================================================

The skill structure supports tooling integration:

┌─────────────────────────────────────────────────────────────────────────────┐
│ DIRECTORY STRUCTURE                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ skills/                                                                      │
│ └── {type}/                                                                  │
│     └── {category}/                                                          │
│         └── {specialization}/                                                │
│             ├── SKILL.md                                                     │
│             ├── scripts/                                                     │
│             │   ├── init_skill.py                                            │
│             │   └── *.sh, *.py, *.js                                        │
│             ├── references/                                                  │
│             │   ├── SCHEMAS.md                                               │
│             │   ├── API.md                                                   │
│             │   └── PATTERNS.md                                              │
│             └── assets/                                                      │
│                 ├── templates/                                               │
│                 └── config/                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

TOOL REQUIREMENTS:
┌───────────────────────────┬─────────────────────────────────────────────────┐
│ Context Requirement       │ Description                                     │
├───────────────────────────┼─────────────────────────────────────────────────┤
│ code_access               │ Read/write file system                          │
│ browser_tool              │ Web browsing capabilities                       │
│ search_tool               │ Search engine access                            │
│ shell_tool                │ Execute shell commands                          │
│ api_tool                  │ HTTP API access                                 │
│ database_tool             │ Database query access                           │
└───────────────────────────┴─────────────────────────────────────────────────┘

================================================================================
SKILL TRIGGERING & ACTIVATION
================================================================================

Skills are triggered through multiple mechanisms:

1. EXPLICIT TRIGGER: User explicitly mentions skill
   → "Use the web-research skill to find..."

2. CONTEXTUAL TRIGGER: Task matches trigger_patterns
   → "Research the latest AI developments" → web-research

3. MOUNTED TRIGGER: Skill mounted by ContextModulator
   → Skills in mounted_skills are always available

4. AUTOMATIC TRIGGER: DSPy signature selects skill
   → PlannerSignature recommends required_skills

TRIGGER PATTERN MATCHING:
{
    "skill_id": "web-research",
    "trigger_patterns": [
        "research",
        "look up",
        "find information",
        "search the web",
        "current information"
    ],
    "context_requirements": ["browser_tool", "search_tool"],
    "confidence_threshold": 0.7
}

================================================================================
EXAMPLE: WEB-RESEARCH SKILL HIERARCHICAL CONTEXT
================================================================================

{
    "skill_id": "web-research",
    "hierarchical_path": "operational/research/web-research",

    "knowledge": {
        "domain": "web",
        "subdomains": ["search", "browsing", "information-retrieval"],
        "knowledge_graph_relations": [
            {"relation": "part_of", "target": "information-gathering", "weight": 1.0},
            {"relation": "enables", "target": "fact-checking", "weight": 0.8}
        ]
    },

    "relational": {
        "depends_on": [],
        "composes_with": ["data-extraction", "document-processing"],
        "alternatives": ["database-query", "knowledge-base"],
        "supersedes": [],
        "related_skills": ["code-review", "data-analysis"]
    },

    "memory_keys": ["web-research", "research", "search", "browser"],
    "embedding_keywords": ["web", "research", "search", "browse", "find", "extract"],

    "trigger_patterns": [
        "research", "look up", "find information",
        "search the web", "browse", "current information"
    ],
    "context_requirements": ["browser_tool", "search_tool", "internet_access"],

    "progressive_disclosure": {
        "metadata_level": "name + description",
        "body_level": "purpose, when_to_use, how_to_apply, constraints",
        "resources_level": "scripts/search.sh, references/sources.md"
    },

    "degrees_of_freedom": {
        "level": "medium",
        "approach": "pseudocode",
        "rationale": "Search strategy varies by query type"
    }
}

================================================================================
"""
