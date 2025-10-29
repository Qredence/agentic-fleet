/**
 * ChatSuggestions Component
 *
 * Displays prompt suggestions for users:
 * - Pre-defined prompt suggestions
 * - Context-aware suggestions based on current state
 * - Keyboard shortcuts display
 * - Interactive suggestion buttons
 */

import { PromptSuggestion } from "@/components/ui/prompt-kit";
import { Badge } from "@/components/ui/shadcn/badge";
import { Button } from "@/components/ui/shadcn/button";
import { Search, Sparkles, Target, TrendingUp } from "lucide-react";
import { memo, useCallback, useMemo } from "react";

interface ChatSuggestionsProps {
  onSuggestionSelect: (suggestion: string) => void;
  isVisible?: boolean;
  chatStatus?: "ready" | "submitted" | "streaming" | "error";
  className?: string;
}

const ChatSuggestionsComponent = ({
  onSuggestionSelect,
  isVisible = true,
  chatStatus = "ready",
  className = "",
}: ChatSuggestionsProps) => {
  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      onSuggestionSelect(suggestion);
    },
    [onSuggestionSelect]
  );

  if (!isVisible || chatStatus !== "ready") {
    return null;
  }

  const suggestions = useMemo(
    () => [
      {
        text: "Analyze Python code quality in my repository",
        icon: <Search className="h-4 w-4" />,
        category: "analysis",
        description: "Review and improve code quality",
      },
      {
        text: "Create a detailed plan for implementing a new feature",
        icon: <Target className="h-4 w-4" />,
        category: "planning",
        description: "Step-by-step implementation plan",
      },
      {
        text: "Research best practices for React performance optimization",
        icon: <TrendingUp className="h-4 w-4" />,
        category: "research",
        description: "Performance optimization strategies",
      },
      {
        text: "Help me debug this TypeScript compilation error",
        icon: <Sparkles className="h-4 w-4" />,
        category: "debugging",
        description: "Troubleshoot compilation issues",
      },
    ],
    []
  );

  const categories = [
    {
      name: "analysis",
      color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    },
    {
      name: "planning",
      color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    },
    {
      name: "research",
      color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    },
    {
      name: "debugging",
      color: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    },
  ];

  const getCategoryColor = (category: string) => {
    const found = categories.find((c) => c.name === category);
    return found ? found.color : "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="text-center space-y-2">
        <h3 className="text-xl font-semibold text-foreground">What would you like to work on?</h3>
        <p className="mx-auto max-w-2xl text-sm text-muted-foreground">
          Choose a suggestion below or type your own request to get started.
        </p>
      </div>

      {/* Enhanced Suggestions Grid */}
      <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
        {suggestions
          .filter((suggestion) => suggestion && suggestion.text && suggestion.icon)
          .map((suggestion, index) => (
            <PromptSuggestion
              key={`${suggestion.category}-${index}`}
              onClick={() => handleSuggestionClick(suggestion.text)}
              variant="outline"
              size="lg"
              className="!h-auto min-h-[140px] w-full !items-stretch !justify-start rounded-xl border border-border/60 bg-card/80 p-4 text-left shadow-sm transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-lg focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <div className="flex h-full w-full flex-col justify-between gap-4">
                <div className="flex w-full items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    {suggestion.icon}
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex flex-col gap-2">
                      <h4 className="text-sm font-medium leading-snug text-foreground">
                        {suggestion.text}
                      </h4>
                      <Badge
                        variant="secondary"
                        className={`w-fit text-xs ${getCategoryColor(suggestion.category)}`}
                      >
                        {suggestion.category}
                      </Badge>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {suggestion.description}
                    </p>
                  </div>
                </div>
                <span className="text-xs font-medium text-primary/70">Tap to use this prompt</span>
              </div>
            </PromptSuggestion>
          ))}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("Show me current project status")}
        >
          Project Overview
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("List available agents and their capabilities")}
        >
          Agent Capabilities
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("Help me understand the current workflow")}
        >
          Workflow Help
        </Button>
      </div>
    </div>
  );
};

export const ChatSuggestions = memo(ChatSuggestionsComponent);
