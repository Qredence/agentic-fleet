/**
 * Utilities for detecting and formatting code in agent responses.
 * Helps ensure code snippets are properly formatted even when agents
 * don't wrap them in markdown code fences.
 */

// Language detection patterns
const LANGUAGE_PATTERNS: Record<string, RegExp[]> = {
  python: [
    /^(import|from)\s+\w+/m,
    /^def\s+\w+\s*\(/m,
    /^class\s+\w+.*:/m,
    /^\s*if\s+.*:\s*$/m,
    /^\s*for\s+\w+\s+in\s+/m,
    /^\s*async\s+def\s+/m,
    /print\s*\(/,
  ],
  typescript: [
    /^(import|export)\s+.*from\s+['"]/m,
    /^(const|let|var)\s+\w+:\s*\w+/m,
    /^interface\s+\w+/m,
    /^type\s+\w+\s*=/m,
    /:\s*(string|number|boolean|any|void|Promise)</,
    /<\w+>\s*\(/,
  ],
  javascript: [
    /^(import|export)\s+/m,
    /^(const|let|var)\s+\w+\s*=/m,
    /^function\s+\w+\s*\(/m,
    /^(async\s+)?function\s*\(/m,
    /=>\s*{/,
    /\.then\s*\(/,
    /console\.(log|error|warn)\s*\(/,
  ],
  rust: [
    /^(use|mod|pub|fn|impl|struct|enum|trait)\s+/m,
    /let\s+mut\s+/,
    /->\s*(Self|\w+)/,
    /println!\s*\(/,
    /#\[derive\(/,
  ],
  go: [
    /^package\s+\w+/m,
    /^import\s+\(/m,
    /^func\s+(\(\w+\s+\*?\w+\)\s+)?\w+\s*\(/m,
    /fmt\.(Print|Sprintf)/,
    /:=\s*/,
  ],
  java: [
    /^(public|private|protected)\s+(class|interface|enum)/m,
    /^import\s+java\./m,
    /System\.out\.print/,
    /@Override/,
    /public\s+static\s+void\s+main/,
  ],
  cpp: [
    /^#include\s*</m,
    /^(class|struct|namespace)\s+\w+/m,
    /std::/,
    /cout\s*<</,
    /int\s+main\s*\(/,
  ],
  sql: [
    /^(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\s+/im,
    /\bFROM\s+\w+/i,
    /\bWHERE\s+/i,
    /\bJOIN\s+/i,
    /\bGROUP\s+BY\s+/i,
  ],
  bash: [
    /^#!/m,
    /^\s*(if|then|else|fi|for|do|done|while|case|esac)\s/m,
    /\$\{?\w+\}?/,
    /\|\s*grep/,
    /&&\s*\w+/,
  ],
  json: [/^\s*\{[\s\S]*\}\s*$/m, /^\s*\[[\s\S]*\]\s*$/m, /"[\w-]+"\s*:/],
  yaml: [/^\w+:\s*$/m, /^\s+-\s+\w+/m, /^\s+\w+:\s+/m],
  html: [/^<!DOCTYPE/im, /<\/?[a-z][\s\S]*>/i, /<\/?(div|span|p|a|h[1-6])/i],
  css: [
    /^\s*\.\w+\s*\{/m,
    /^\s*#\w+\s*\{/m,
    /^\s*@(media|keyframes|import)/m,
    /:\s*(flex|grid|block|none|auto);/,
  ],
};

// Patterns that indicate content is likely code (language-agnostic)
const GENERIC_CODE_PATTERNS: RegExp[] = [
  // Function/method definitions
  /^(function|def|fn|func|sub|proc)\s+\w+\s*\(/m,
  // Class/interface definitions
  /^(class|interface|struct|enum|type)\s+\w+/m,
  // Import/export statements
  /^(import|export|require|include|using)\s+/m,
  // Variable declarations with types or assignments
  /^(const|let|var|val|int|string|bool)\s+\w+\s*[=:]/m,
  // Control flow with braces or colons
  /^\s*(if|else|for|while|switch|match|try|catch)\s*[({:]/m,
  // Return statements
  /^\s*return\s+/m,
  // Arrow functions
  /=>\s*[{(]/,
  // Object/dict literals spanning multiple lines
  /^\s*\{[\s\S]*:\s*[\s\S]*\}\s*$/m,
  // Array literals spanning multiple lines
  /^\s*\[[\s\S]*,[\s\S]*\]\s*$/m,
  // Constructor or method definitions (common in OOP)
  /^\s*(constructor|init|__init__|new)\s*\(/m,
  // this/self references (OOP indicator)
  /\b(this|self)\.\w+\s*=/,
  // Curly brace blocks (strong code indicator when combined with others)
  /\{\s*\n[\s\S]*\n\s*\}/m,
];

// Patterns that suggest content is NOT code (prose indicators)
const PROSE_PATTERNS: RegExp[] = [
  // Sentences with common prose patterns
  /\b(the|a|an|is|are|was|were|have|has|will|would|could|should)\b.*[.!?]$/im,
  // Questions
  /^(what|why|how|when|where|who|can|could|would|should|is|are|do|does)\b.*\?$/im,
  // Numbered lists with prose
  /^\d+\.\s+[A-Z][a-z]+.*[.!?]$/m,
  // Bullet points with prose
  /^[-*]\s+[A-Z][a-z]+.*[.!?]$/m,
];

/**
 * Detect the likely programming language of a code snippet.
 */
export function detectLanguage(code: string): string {
  const scores: Record<string, number> = {};

  for (const [lang, patterns] of Object.entries(LANGUAGE_PATTERNS)) {
    scores[lang] = patterns.filter((p) => p.test(code)).length;
  }

  const maxScore = Math.max(...Object.values(scores));
  if (maxScore === 0) return "plaintext";

  const topLang = Object.entries(scores).find(
    ([, score]) => score === maxScore,
  );
  return topLang ? topLang[0] : "plaintext";
}

/**
 * Check if content appears to be code that should be wrapped in a code block.
 */
export function looksLikeCode(content: string): boolean {
  // Skip if already has markdown code fences
  if (content.includes("```")) return false;

  // Skip very short content
  if (content.length < 20) return false;

  // Skip if it looks like prose
  if (PROSE_PATTERNS.some((p) => p.test(content))) return false;

  // Check for generic code patterns
  const codePatternMatches = GENERIC_CODE_PATTERNS.filter((p) =>
    p.test(content),
  ).length;

  // Check for language-specific patterns
  let langPatternMatches = 0;
  for (const patterns of Object.values(LANGUAGE_PATTERNS)) {
    langPatternMatches += patterns.filter((p) => p.test(content)).length;
  }

  // Consider it code if we have pattern matches
  // Lower threshold: 1 generic + 1 lang-specific, or 2+ of either
  return (
    codePatternMatches >= 2 ||
    langPatternMatches >= 2 ||
    (codePatternMatches >= 1 && langPatternMatches >= 1)
  );
}

/**
 * Wrap content in markdown code fences if it looks like code.
 * Returns the original content unchanged if it doesn't look like code
 * or already has code fences.
 */
export function wrapCodeInMarkdown(content: string): string {
  if (!looksLikeCode(content)) return content;

  const language = detectLanguage(content);
  return `\`\`\`${language}\n${content.trim()}\n\`\`\``;
}

/**
 * Process content to ensure code blocks are properly formatted.
 * This handles cases where agents return code without markdown formatting.
 */
export function ensureCodeFormatting(content: string): string {
  // If content already has markdown code fences, return as-is
  if (content.includes("```")) return content;

  // Check if the entire content looks like a code block
  if (looksLikeCode(content)) {
    return wrapCodeInMarkdown(content);
  }

  return content;
}
