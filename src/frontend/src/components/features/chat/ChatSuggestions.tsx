/**
 * ChatSuggestions Component
 *
 * Displays prompt suggestions for users:
 * - Pre-defined prompt suggestions
 * - Context-aware suggestions based on current state
 * - Keyboard shortcuts display
 * - Interactive suggestion buttons
 */

import { memo, useCallback } from "react";
import { PromptSuggestion } from "@/components/ui/prompt-kit";
import { Badge } from "@/components/ui/shadcn/badge";
import { Button } from "@/components/ui/shadcn/button";
import { Search, Target, TrendingUp, Sparkles } from "lucide-react";

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
  const handleSuggestionClick = useCallback((suggestion: string) => {
    onSuggestionSelect(suggestion);
  }, [onSuggestionSelect]);

  if (!isVisible || chatStatus !== "ready") {
    return null;
  }

  const suggestions = [
    {
      text: "Analyze Python code quality in my repository",
      icon: <Search className="h-4 w-4" />,
      category: "analysis",
      description: "Review and improve code quality"
    },
    {
      text: "Create a detailed plan for implementing a new feature",
      icon: <Target className="h-4 w-4" />,
      category: "planning",
      description: "Step-by-step implementation plan"
    },
    {
      text: "Research best practices for React performance optimization",
      icon: <TrendingUp className="h-4 w-4" />,
      category: "research",
      description: "Performance optimization strategies"
    },
    {
      text: "Help me debug this TypeScript compilation error",
      icon: <Sparkles className="h-4 w-4" />,
      category: "debugging",
      description: "Troubleshoot compilation issues"
    }
  ];

  const categories = [
    { name: "analysis", color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" },
    { name: "planning", color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" },
    { name: "research", color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200" },
    { name: "debugging", color: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" }
  ];

  const getCategoryColor = (category: string) => {
    const found = categories.find(c => c.name === category);
    return found ? found.color : "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-foreground mb-2">
          What would you like to work on?
        </h3>
        <p className="text-sm text-muted-foreground">
          Choose a suggestion below or type your own request
        </p>
      </div>

      {/* Enhanced Suggestions Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {suggestions.map((suggestion, index) => (
          <PromptSuggestion
            key={index}
            onClick={() => handleSuggestionClick(suggestion.text)}
            variant="outline"
            size="lg"
            className="p-4 text-left hover:shadow-lg transition-all duration-200"
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                {suggestion.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-sm leading-tight">
                    {suggestion.text}
                  </h4>
                  <Badge
                    variant="secondary"
                    className={`text-xs ${getCategoryColor(suggestion.category)}`}
                  >
                    {suggestion.category}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  {suggestion.description}
                </p>
              </div>
            </div>
          </PromptSuggestion>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 justify-center">
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleSuggestionClick("Show me current project status")}
        >
          Project Overview
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleSuggestionClick("List available agents and their capabilities")}
        >
          Agent Capabilities
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleSuggestionClick("Help me understand the current workflow")}
        >
          Workflow Help
        </Button>
      </div>
    </div>
  );
};

export const ChatSuggestions = memo(ChatSuggestionsComponent);