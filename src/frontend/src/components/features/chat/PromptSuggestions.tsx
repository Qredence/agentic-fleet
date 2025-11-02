import React, { useState, useEffect, useMemo } from "react";
import { useChatStore } from "@/stores/chatStore";
import { chatApi } from "@/api/chatApi";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

// Types
interface PromptSuggestion {
  id: string;
  title: string;
  description: string;
  content: string;
  category: string;
  tags: string[];
  icon?: string;
  requiresTool?: string;
  isCustom?: boolean;
  usageCount?: number;
  lastUsed?: number;
}

interface PromptSuggestionsProps {
  className?: string;
  maxSuggestions?: number;
  enableCustomPrompts?: boolean;
  enableSearch?: boolean;
  onPromptSelect?: (prompt: PromptSuggestion) => void;
  categories?: string[];
}

// Built-in suggestions
const BUILTIN_SUGGESTIONS: PromptSuggestion[] = [
  {
    id: "summarize-repo",
    title: "Summarize Repository",
    description: "Get an overview of the codebase structure and purpose",
    content:
      "Please provide a comprehensive summary of this repository. Include:\n1. Main purpose and functionality\n2. Key components and architecture\n3. Technologies used\n4. Setup instructions\n5. Important files to review",
    category: "Analysis",
    tags: ["repository", "summary", "overview"],
    icon: "📋",
  },
  {
    id: "list-tasks",
    title: "List Open Tasks",
    description: "Find TODO comments, issues, and pending work",
    content:
      "Please identify all open tasks, TODOs, and pending work in this codebase. Organize them by:\n1. Priority level\n2. File location\n3. Estimated complexity\n4. Dependencies",
    category: "Planning",
    tags: ["tasks", "todo", "planning"],
    icon: "📝",
  },
  {
    id: "plan-next-steps",
    title: "Plan Next Steps",
    description: "Create an actionable plan for development",
    content:
      "Based on the current state of this repository, please help me plan the next steps for development. Consider:\n1. Current issues and bugs\n2. Feature gaps\n3. Technical debt\n4. Testing coverage\n5. Documentation needs",
    category: "Planning",
    tags: ["planning", "strategy", "development"],
    icon: "🎯",
  },
  {
    id: "review-code",
    title: "Code Review",
    description: "Analyze code quality and suggest improvements",
    content:
      "Please conduct a thorough code review of this repository. Focus on:\n1. Code quality and best practices\n2. Performance optimization opportunities\n3. Security vulnerabilities\n4. Maintainability and readability\n5. Testing coverage and quality",
    category: "Quality",
    tags: ["review", "quality", "best-practices"],
    icon: "🔍",
  },
  {
    id: "explain-concept",
    title: "Explain Concept",
    description: "Get detailed explanation of specific concepts",
    content:
      "Please explain the key concepts and patterns used in this codebase. Include:\n1. Design patterns and architecture\n2. Algorithms and data structures\n3. Domain-specific terminology\n4. Key abstractions and their purposes\n5. How different components interact",
    category: "Learning",
    tags: ["explanation", "concepts", "learning"],
    icon: "💡",
  },
  {
    id: "debug-issue",
    title: "Debug Issue",
    description: "Help identify and fix problems",
    content:
      "I'm experiencing an issue with this codebase. Please help me debug by:\n1. Analyzing error logs and stack traces\n2. Identifying potential root causes\n3. Suggesting debugging strategies\n4. Providing fix recommendations\n5. Explaining the issue in simple terms",
    category: "Debugging",
    tags: ["debug", "troubleshooting", "fix"],
    icon: "🐛",
  },
  {
    id: "optimize-performance",
    title: "Optimize Performance",
    description: "Identify and improve performance bottlenecks",
    content:
      "Please analyze this codebase for performance optimization opportunities. Focus on:\n1. Algorithm efficiency\n2. Memory usage patterns\n3. Database query optimization\n4. Network request optimization\n5. Frontend performance improvements",
    category: "Performance",
    tags: ["performance", "optimization", "efficiency"],
    icon: "⚡",
  },
  {
    id: "write-tests",
    title: "Write Tests",
    description: "Generate comprehensive test coverage",
    content:
      "Please help me write comprehensive tests for this codebase. Include:\n1. Unit tests for core functionality\n2. Integration tests for component interactions\n3. End-to-end tests for user workflows\n4. Performance tests for critical paths\n5. Edge cases and error scenarios",
    category: "Testing",
    tags: ["testing", "quality", "coverage"],
    icon: "🧪",
  },
];

export const PromptSuggestions: React.FC<PromptSuggestionsProps> = React.memo(
  ({
    className,
    maxSuggestions = 6,
    enableCustomPrompts = true,
    enableSearch = true,
    onPromptSelect,
    categories = [
      "Analysis",
      "Planning",
      "Quality",
      "Learning",
      "Debugging",
      "Performance",
      "Testing",
    ],
  }) => {
    const { currentConversationId } = useChatStore();

    // Local state
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedCategory, setSelectedCategory] = useState<string>("all");
    const [showOnlyCustom, setShowOnlyCustom] = useState(false);
    const [customPrompts, setCustomPrompts] = useState<PromptSuggestion[]>([]);
    const [isAddingCustom, setIsAddingCustom] = useState(false);
    const [newPrompt, setNewPrompt] = useState<Partial<PromptSuggestion>>({
      title: "",
      description: "",
      content: "",
      category: "Custom",
      tags: [],
    });

    // Load custom prompts from localStorage
    useEffect(() => {
      if (enableCustomPrompts) {
        try {
          const stored = localStorage.getItem("custom-prompts");
          if (stored) {
            setCustomPrompts(JSON.parse(stored));
          }
        } catch (error) {
          console.error("Failed to load custom prompts:", error);
        }
      }
    }, [enableCustomPrompts]);

    // Filter suggestions
    const filteredSuggestions = useMemo(() => {
      let suggestions = showOnlyCustom
        ? customPrompts
        : [...BUILTIN_SUGGESTIONS, ...customPrompts];

      // Filter by category
      if (selectedCategory !== "all") {
        suggestions = suggestions.filter(
          (s) => s.category === selectedCategory,
        );
      }

      // Filter by search term
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        suggestions = suggestions.filter(
          (s) =>
            s.title.toLowerCase().includes(term) ||
            s.description.toLowerCase().includes(term) ||
            s.content.toLowerCase().includes(term) ||
            s.tags.some((tag) => tag.toLowerCase().includes(term)),
        );
      }

      // Sort by usage count and last used
      return suggestions
        .sort((a, b) => {
          // Sort custom prompts to the top if enabled
          if (a.isCustom && !b.isCustom) return -1;
          if (!a.isCustom && b.isCustom) return 1;

          // Sort by usage count (descending)
          const aUsage = a.usageCount || 0;
          const bUsage = b.usageCount || 0;
          if (aUsage !== bUsage) return bUsage - aUsage;

          // Sort by last used (descending)
          const aLastUsed = a.lastUsed || 0;
          const bLastUsed = b.lastUsed || 0;
          return bLastUsed - aLastUsed;
        })
        .slice(0, maxSuggestions);
    }, [
      searchTerm,
      selectedCategory,
      showOnlyCustom,
      customPrompts,
      maxSuggestions,
    ]);

    // Handle prompt selection
    const handlePromptSelect = (prompt: PromptSuggestion) => {
      // Update usage stats
      if (prompt.isCustom) {
        const updated = customPrompts.map((p) =>
          p.id === prompt.id
            ? {
                ...p,
                usageCount: (p.usageCount || 0) + 1,
                lastUsed: Date.now(),
              }
            : p,
        );
        setCustomPrompts(updated);
        localStorage.setItem("custom-prompts", JSON.stringify(updated));
      }

      onPromptSelect?.(prompt);
      toast.success(`Selected: ${prompt.title}`);
    };

    // Add custom prompt
    const handleAddCustomPrompt = () => {
      if (!newPrompt.title || !newPrompt.content) {
        toast.error("Title and content are required");
        return;
      }

      const customPrompt: PromptSuggestion = {
        id: `custom-${Date.now()}`,
        title: newPrompt.title,
        description: newPrompt.description || newPrompt.title,
        content: newPrompt.content,
        category: newPrompt.category || "Custom",
        tags: newPrompt.tags || [],
        isCustom: true,
        usageCount: 0,
        lastUsed: Date.now(),
      };

      const updated = [...customPrompts, customPrompt];
      setCustomPrompts(updated);
      localStorage.setItem("custom-prompts", JSON.stringify(updated));

      setNewPrompt({
        title: "",
        description: "",
        content: "",
        category: "Custom",
        tags: [],
      });
      setIsAddingCustom(false);
      toast.success("Custom prompt added successfully");
    };

    // Delete custom prompt
    const handleDeleteCustomPrompt = (promptId: string) => {
      const updated = customPrompts.filter((p) => p.id !== promptId);
      setCustomPrompts(updated);
      localStorage.setItem("custom-prompts", JSON.stringify(updated));
      toast.success("Custom prompt deleted");
    };

    return (
      <div className={cn("space-y-4", className)}>
        {/* Search and filters */}
        {enableSearch && (
          <div className="space-y-3">
            <Input
              placeholder="Search suggestions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full"
            />

            <div className="flex flex-wrap gap-2">
              {/* Category filter */}
              <div className="flex items-center gap-2">
                <Label htmlFor="category-filter" className="text-sm">
                  Category:
                </Label>
                <select
                  id="category-filter"
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="all">All Categories</option>
                  {categories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </select>
              </div>

              {/* Custom prompts toggle */}
              {enableCustomPrompts && (
                <div className="flex items-center gap-2">
                  <Switch
                    id="custom-only"
                    checked={showOnlyCustom}
                    onCheckedChange={setShowOnlyCustom}
                  />
                  <Label htmlFor="custom-only" className="text-sm">
                    Custom only
                  </Label>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Suggestions grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filteredSuggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className={cn(
                "p-4 border rounded-lg cursor-pointer transition-all hover:shadow-md hover:border-primary",
                suggestion.isCustom &&
                  "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
              )}
              onClick={() => handlePromptSelect(suggestion)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  {suggestion.icon && (
                    <span className="text-lg">{suggestion.icon}</span>
                  )}
                  <h4 className="font-medium text-sm">{suggestion.title}</h4>
                </div>
                {suggestion.isCustom && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCustomPrompt(suggestion.id);
                    }}
                  >
                    ×
                  </Button>
                )}
              </div>

              <p className="text-xs text-muted-foreground mb-2">
                {suggestion.description}
              </p>

              <div className="flex flex-wrap gap-1 mb-2">
                <Badge variant="secondary" className="text-xs">
                  {suggestion.category}
                </Badge>
                {suggestion.requiresTool && (
                  <Badge variant="outline" className="text-xs">
                    {suggestion.requiresTool}
                  </Badge>
                )}
                {suggestion.usageCount !== undefined &&
                  suggestion.usageCount > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {suggestion.usageCount} uses
                    </Badge>
                  )}
              </div>

              {suggestion.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {suggestion.tags.slice(0, 3).map((tag, index) => (
                    <span key={index} className="text-xs text-muted-foreground">
                      #{tag}
                    </span>
                  ))}
                  {suggestion.tags.length > 3 && (
                    <span className="text-xs text-muted-foreground">
                      +{suggestion.tags.length - 3} more
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add custom prompt */}
        {enableCustomPrompts && (
          <div className="pt-4 border-t">
            {!isAddingCustom ? (
              <Button
                variant="outline"
                onClick={() => setIsAddingCustom(true)}
                className="w-full"
              >
                + Add Custom Prompt
              </Button>
            ) : (
              <div className="space-y-3 p-4 border rounded-lg">
                <h4 className="font-medium">Add Custom Prompt</h4>

                <div className="space-y-2">
                  <Label htmlFor="prompt-title">Title *</Label>
                  <Input
                    id="prompt-title"
                    placeholder="Enter prompt title..."
                    value={newPrompt.title || ""}
                    onChange={(e) =>
                      setNewPrompt((prev) => ({
                        ...prev,
                        title: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt-description">Description</Label>
                  <Input
                    id="prompt-description"
                    placeholder="Brief description..."
                    value={newPrompt.description || ""}
                    onChange={(e) =>
                      setNewPrompt((prev) => ({
                        ...prev,
                        description: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt-content">Content *</Label>
                  <textarea
                    id="prompt-content"
                    placeholder="Enter the prompt content..."
                    value={newPrompt.content || ""}
                    onChange={(e) =>
                      setNewPrompt((prev) => ({
                        ...prev,
                        content: e.target.value,
                      }))
                    }
                    className="w-full p-2 border rounded-md text-sm min-h-[100px] resize-y"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt-category">Category</Label>
                  <Input
                    id="prompt-category"
                    placeholder="Category..."
                    value={newPrompt.category || ""}
                    onChange={(e) =>
                      setNewPrompt((prev) => ({
                        ...prev,
                        category: e.target.value,
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="prompt-tags">Tags (comma-separated)</Label>
                  <Input
                    id="prompt-tags"
                    placeholder="tag1, tag2, tag3..."
                    value={newPrompt.tags?.join(", ") || ""}
                    onChange={(e) =>
                      setNewPrompt((prev) => ({
                        ...prev,
                        tags: e.target.value
                          .split(",")
                          .map((tag) => tag.trim())
                          .filter(Boolean),
                      }))
                    }
                  />
                </div>

                <div className="flex gap-2">
                  <Button onClick={handleAddCustomPrompt} size="sm">
                    Add Prompt
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsAddingCustom(false);
                      setNewPrompt({
                        title: "",
                        description: "",
                        content: "",
                        category: "Custom",
                        tags: [],
                      });
                    }}
                    size="sm"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* No results */}
        {filteredSuggestions.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <p>No suggestions found</p>
            {searchTerm && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSearchTerm("")}
                className="mt-2"
              >
                Clear search
              </Button>
            )}
          </div>
        )}
      </div>
    );
  },
);

PromptSuggestions.displayName = "PromptSuggestions";
