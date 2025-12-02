"use client";

import React, { memo } from "react";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";

// Animation variants for message entry/exit
const messageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 20,
    scale: 0.95,
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring",
      stiffness: 350,
      damping: 25,
      mass: 0.8,
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.95,
    transition: {
      duration: 0.15,
      ease: "easeOut",
    },
  },
};

// Stagger variants for grouped messages
const groupVariants: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

// Subtle slide-in for streaming content
const streamingVariants: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.2,
    },
  },
};

// Typing indicator animation
const typingDotVariants: Variants = {
  initial: { y: 0 },
  animate: {
    y: [0, -6, 0],
    transition: {
      duration: 0.6,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

interface AnimatedMessageProps {
  /** Unique key for AnimatePresence */
  messageId: string;
  /** Whether this message is currently streaming */
  isStreaming?: boolean;
  /** Whether to use minimal animation (for performance during streaming) */
  minimal?: boolean;
  /** Child content to render */
  children: React.ReactNode;
  className?: string;
}

/**
 * Wrapper component that applies smooth enter/exit animations to messages.
 * Uses framer-motion for physics-based spring animations.
 */
export const AnimatedMessage = memo(function AnimatedMessage({
  messageId,
  isStreaming = false,
  minimal = false,
  children,
  className,
}: AnimatedMessageProps) {
  const variants = minimal || isStreaming ? streamingVariants : messageVariants;

  return (
    <motion.div
      key={messageId}
      layout={!isStreaming} // Disable layout animation during streaming for perf
      layoutId={isStreaming ? undefined : messageId}
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={cn("will-change-transform", className)}
    >
      {children}
    </motion.div>
  );
});

interface AnimatedMessageListProps {
  /** Array of message IDs for tracking */
  messageIds: string[];
  /** Render function for each message */
  children: React.ReactNode;
  className?: string;
}

/**
 * Container that handles AnimatePresence for a list of messages.
 */
export function AnimatedMessageList({
  children,
  className,
}: AnimatedMessageListProps) {
  return (
    <AnimatePresence initial={false} mode="popLayout">
      <motion.div
        variants={groupVariants}
        initial="initial"
        animate="animate"
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

interface TypingIndicatorProps {
  /** Name of the agent currently typing */
  agentName?: string;
  className?: string;
}

/**
 * Animated typing indicator with bouncing dots.
 */
export function TypingIndicator({
  agentName = "AI",
  className,
}: TypingIndicatorProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -5 }}
      className={cn("flex items-center gap-3", className)}
    >
      <div className="flex items-center gap-1 px-3 py-2 rounded-lg bg-secondary/50">
        <span className="text-xs text-muted-foreground mr-2">{agentName}</span>
        <motion.span
          variants={typingDotVariants}
          initial="initial"
          animate="animate"
          className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
          style={{ animationDelay: "0ms" }}
        />
        <motion.span
          variants={typingDotVariants}
          initial="initial"
          animate="animate"
          className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
          style={{ animationDelay: "150ms" }}
        />
        <motion.span
          variants={typingDotVariants}
          initial="initial"
          animate="animate"
          className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </motion.div>
  );
}

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

/**
 * Simple fade-in animation wrapper.
 */
export function FadeIn({
  children,
  delay = 0,
  duration = 0.3,
  className,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay, duration }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

interface SlideInProps {
  children: React.ReactNode;
  direction?: "up" | "down" | "left" | "right";
  delay?: number;
  className?: string;
}

/**
 * Slide-in animation from any direction.
 */
export function SlideIn({
  children,
  direction = "up",
  delay = 0,
  className,
}: SlideInProps) {
  const offsets = {
    up: { y: 20 },
    down: { y: -20 },
    left: { x: 20 },
    right: { x: -20 },
  };

  return (
    <motion.div
      initial={{ opacity: 0, ...offsets[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 24,
        delay,
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/**
 * Pulse animation for streaming content indicator.
 */
export function StreamingPulse({ className }: { className?: string }) {
  return (
    <motion.div
      animate={{
        scale: [1, 1.2, 1],
        opacity: [1, 0.7, 1],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className={cn("w-2 h-2 rounded-full bg-blue-500", className)}
    />
  );
}
