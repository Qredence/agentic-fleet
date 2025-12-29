import type { ConversationStep } from "@/api/types";

/**
 * Parsed verification report structure
 */
export interface ParsedReport {
  summary?: string;
  checklist?: string[];
  defects?: string[];
  recommendedFollowUps?: string[];
  conclusion?: string;
  rawContent: string;
}

/**
 * Parse a verification report from agent output text.
 * Looks for structured sections: Summary, Checklist, Defects, Recommended follow-ups, Conclusion
 */
export function parseVerificationReport(content: string): ParsedReport | null {
  if (!content || typeof content !== "string") {
    return null;
  }

  const report: ParsedReport = {
    rawContent: content,
  };

  // Try to extract Summary section (more flexible pattern)
  const summaryMatch = content.match(
    /(?:^|\n)\s*(?:Verification\s+report\s+)?Summary\s*:?\s*\n?([\s\S]*?)(?=\n\s*(?:Checklist|Defects|Recommended|Conclusion|$))/i,
  );
  if (summaryMatch) {
    report.summary = summaryMatch[1].trim();
  }

  // Try to extract Checklist section (handles "Checklist Verify..." format)
  const checklistMatch = content.match(
    /(?:^|\n)\s*Checklist\s+([\s\S]*?)(?=\n\s*(?:Defects|Recommended|Conclusion|Summary|$))/i,
  );
  if (checklistMatch) {
    const checklistText = checklistMatch[1].trim();
    // Parse checklist items (lines starting with - or • or numbered, or "done —" format)
    report.checklist = checklistText
      .split(/\n/)
      .map((line) => {
        // Remove bullet points, numbers, and "done —" / "—" prefixes
        return line
          .replace(/^[\s•\-\d.)]+/, "")
          .replace(/^(done|✓|completed)\s*[—–-]\s*/i, "")
          .trim();
      })
      .filter((line) => line.length > 0);
  }

  // Try to extract Defects section (handles "Defects / Missing Information" format)
  const defectsMatch = content.match(
    /(?:^|\n)\s*Defects\s*(?:\/|\s+)?(?:Missing\s+Information)?\s*:?\s*\n?([\s\S]*?)(?=\n\s*(?:Recommended|Conclusion|Summary|Checklist|$))/i,
  );
  if (defectsMatch) {
    const defectsText = defectsMatch[1].trim();
    if (
      defectsText.toLowerCase().includes("none") ||
      defectsText.toLowerCase().includes("no") ||
      defectsText.toLowerCase().includes("none apparent")
    ) {
      report.defects = [];
    } else {
      report.defects = defectsText
        .split(/\n/)
        .map((line) => line.replace(/^[\s•\-\d.)]+/, "").trim())
        .filter((line) => line.length > 0);
    }
  }

  // Try to extract Recommended follow-ups section
  const followUpsMatch = content.match(
    /(?:^|\n)\s*Recommended\s+(?:follow[- ]?ups?|actions?)\s*:?\s*\n?([\s\S]*?)(?=\n\s*(?:Conclusion|Summary|Checklist|Defects|$))/i,
  );
  if (followUpsMatch) {
    const followUpsText = followUpsMatch[1].trim();
    report.recommendedFollowUps = followUpsText
      .split(/\n/)
      .map((line) => line.replace(/^[\s•\-\d.)]+/, "").trim())
      .filter((line) => line.length > 0);
  }

  // Try to extract Conclusion section
  const conclusionMatch = content.match(
    /(?:^|\n)\s*Conclusion\s*:?\s*\n?([\s\S]*?)(?=\n\s*(?:Summary|Checklist|Defects|Recommended|$)|$)/i,
  );
  if (conclusionMatch) {
    report.conclusion = conclusionMatch[1].trim();
  }

  // Only return parsed report if we found at least one section
  if (
    report.summary ||
    (report.checklist && report.checklist.length > 0) ||
    (report.defects && report.defects.length > 0) ||
    (report.recommendedFollowUps && report.recommendedFollowUps.length > 0) ||
    report.conclusion
  ) {
    return report;
  }

  return null;
}

/**
 * Convert a parsed verification report into chain-of-thought steps
 */
export function formatReportAsSteps(
  report: ParsedReport,
  baseTimestamp: string = new Date().toISOString(),
): ConversationStep[] {
  const steps: ConversationStep[] = [];
  let stepIndex = 0;

  // Summary step
  if (report.summary) {
    steps.push({
      id: `report-summary-${Date.now()}-${stepIndex++}`,
      type: "status",
      content: report.summary,
      timestamp: baseTimestamp,
      kind: "verification_summary",
      category: "analysis",
      data: {
        section: "summary",
      },
    });
  }

  // Checklist step
  if (report.checklist && report.checklist.length > 0) {
    steps.push({
      id: `report-checklist-${Date.now()}-${stepIndex++}`,
      type: "status",
      content: report.checklist.join("\n"),
      timestamp: baseTimestamp,
      kind: "verification_checklist",
      category: "analysis",
      data: {
        section: "checklist",
        items: report.checklist,
      },
    });
  }

  // Defects step
  if (report.defects !== undefined) {
    const defectsContent =
      report.defects.length === 0
        ? "No defects or missing information found."
        : report.defects.join("\n");
    steps.push({
      id: `report-defects-${Date.now()}-${stepIndex++}`,
      type: report.defects.length > 0 ? "error" : "status",
      content: defectsContent,
      timestamp: baseTimestamp,
      kind: "verification_defects",
      category: report.defects.length > 0 ? "error" : "analysis",
      data: {
        section: "defects",
        items: report.defects,
      },
    });
  }

  // Recommended follow-ups step
  if (report.recommendedFollowUps && report.recommendedFollowUps.length > 0) {
    steps.push({
      id: `report-followups-${Date.now()}-${stepIndex++}`,
      type: "status",
      content: report.recommendedFollowUps.join("\n"),
      timestamp: baseTimestamp,
      kind: "verification_followups",
      category: "analysis",
      data: {
        section: "recommended_followups",
        items: report.recommendedFollowUps,
      },
    });
  }

  // Conclusion step
  if (report.conclusion) {
    steps.push({
      id: `report-conclusion-${Date.now()}-${stepIndex++}`,
      type: "status",
      content: report.conclusion,
      timestamp: baseTimestamp,
      kind: "verification_conclusion",
      category: "analysis",
      data: {
        section: "conclusion",
      },
    });
  }

  return steps;
}

/**
 * Check if content contains a verification report pattern
 */
export function isVerificationReport(content: string): boolean {
  if (!content || typeof content !== "string") {
    return false;
  }

  // Check for key phrases that indicate a verification report
  const hasVerificationReportPrefix = /(?:^|\n)\s*Verification\s+report/i.test(
    content,
  );
  const hasSummary =
    /(?:^|\n)\s*(?:Verification\s+report\s+)?Summary\s*:?\s*\n?/i.test(content);
  const hasChecklist = /(?:^|\n)\s*Checklist/i.test(content);
  const hasDefects = /(?:^|\n)\s*Defects/i.test(content);
  const hasConclusion = /(?:^|\n)\s*Conclusion\s*:?\s*\n?/i.test(content);

  // Consider it a verification report if it has the prefix OR at least 2 of these sections
  const sectionCount = [
    hasSummary,
    hasChecklist,
    hasDefects,
    hasConclusion,
  ].filter(Boolean).length;
  return hasVerificationReportPrefix || sectionCount >= 2;
}
