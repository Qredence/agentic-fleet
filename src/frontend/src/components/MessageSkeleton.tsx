"use client";

import { cn } from "@/lib/utils";
import { Skeleton, SkeletonAvatar, SkeletonText } from "./ui/skeleton";

interface MessageSkeletonProps {
  /** Whether this is a user message (right-aligned) */
  isUser?: boolean;
  /** Number of text lines to show */
  lines?: number;
  className?: string;
}

/**
 * Skeleton placeholder for a chat message bubble.
 * Shows animated loading state while message content loads.
 */
export function MessageSkeleton({
  isUser = false,
  lines = 2,
  className,
}: MessageSkeletonProps) {
  if (isUser) {
    return (
      <div className={cn("flex justify-end", className)}>
        <Skeleton className="h-10 w-48 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className={cn("flex gap-3", className)}>
      <SkeletonAvatar size="md" className="shrink-0" />
      <div className="flex-1 space-y-2 max-w-[80%]">
        {/* Agent name */}
        <Skeleton className="h-3 w-16" />
        {/* Message content */}
        <div className="bg-secondary/50 rounded-lg p-3 space-y-2">
          <SkeletonText lines={lines} />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton for the conversation list in sidebar.
 */
export function ConversationListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2 px-3 py-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-2 rounded-md"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <Skeleton className="h-4 w-4 shrink-0" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Full chat area skeleton shown on initial load.
 */
export function ChatAreaSkeleton() {
  return (
    <div className="flex-1 flex flex-col p-4 space-y-6">
      {/* Simulate a conversation */}
      <MessageSkeleton isUser lines={1} />
      <MessageSkeleton lines={3} />
      <MessageSkeleton isUser lines={1} />
      <MessageSkeleton lines={4} />
    </div>
  );
}

/**
 * Workflow events skeleton for loading state.
 */
export function WorkflowEventsSkeleton() {
  return (
    <div className="bg-muted/10 rounded-lg p-2 space-y-2">
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>
      <div className="ml-6 space-y-1">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton className="h-3 w-3" />
            <Skeleton className="h-3 w-48" />
          </div>
        ))}
      </div>
    </div>
  );
}
