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
    <div className={`space-y-4 sm:space-y-6 ${className}`}>
      {/* Header - Responsive text sizing */}
      <div className="text-center px-4">
        <h3 className="text-xl sm:text-2xl font-semibold text-foreground mb-2">
          What would you like to work on?
        </h3>
        <p className="text-sm sm:text-base text-muted-foreground">
          Choose a suggestion below or type your own request
        </p>
      </div>

      {/* Enhanced Suggestions Grid - Responsive columns */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2">
        {suggestions.map((suggestion, index) => (
          <PromptSuggestion
            key={index}
            onClick={() => handleSuggestionClick(suggestion.text)}
            variant="outline"
            size="lg"
            className="p-3 sm:p-4 text-left hover:shadow-lg transition-all duration-200 h-full"
          >
            <div className="flex items-start gap-2 sm:gap-3">
              <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                {suggestion.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 mb-1 flex-wrap">
                  <h4 className="font-medium text-sm sm:text-base leading-tight flex-1 min-w-0">
                    {suggestion.text}
                  </h4>
                  <Badge
                    variant="secondary"
                    className={`text-xs flex-shrink-0 ${getCategoryColor(suggestion.category)}`}
                  >
                    {suggestion.category}
                  </Badge>
                </div>
                <p className="text-xs sm:text-sm text-muted-foreground">
                  {suggestion.description}
                </p>
              </div>
            </PromptSuggestion>
          ))}
      </div>

      {/* Quick Actions - Responsive layout */}
      <div className="flex flex-wrap gap-2 justify-center px-4">
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("Show me current project status")}
          className="text-xs sm:text-sm"
        >
          Project Overview
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("List available agents and their capabilities")}
          className="text-xs sm:text-sm"
        >
          Agent Capabilities
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-full px-4 py-1.5"
          onClick={() => handleSuggestionClick("Help me understand the current workflow")}
          className="text-xs sm:text-sm"
        >
          Workflow Help
        </Button>
      </div>
    </div>
  );
};

export const ChatSuggestions = memo(ChatSuggestionsComponent);
