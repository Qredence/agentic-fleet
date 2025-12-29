import { describe, it, expect } from "vitest";
import {
  resolveComponent,
  shouldBeCollapsible,
  COMPONENT_REGISTRY,
  isRegisteredComponent,
  getRegisteredComponents,
} from "@/features/workflow/components/component-registry";
import {
  ChatStepVariant,
  MessageBubbleVariant,
  InlineTextVariant,
} from "@/features/workflow/components/step-variants";
import type { ConversationStep } from "@/api/types";

describe("Component Registry", () => {
  describe("COMPONENT_REGISTRY", () => {
    it("should contain all expected components", () => {
      expect(COMPONENT_REGISTRY).toHaveProperty("ChatStep");
      expect(COMPONENT_REGISTRY).toHaveProperty("MessageBubble");
      expect(COMPONENT_REGISTRY).toHaveProperty("InlineText");
    });

    it("should map to correct component implementations", () => {
      expect(COMPONENT_REGISTRY.ChatStep).toBe(ChatStepVariant);
      expect(COMPONENT_REGISTRY.MessageBubble).toBe(MessageBubbleVariant);
      expect(COMPONENT_REGISTRY.InlineText).toBe(InlineTextVariant);
    });
  });

  describe("resolveComponent", () => {
    it("should return component from registry when ui_hint.component is valid", () => {
      const step: ConversationStep = {
        id: "1",
        type: "thought",
        content: "Test",
        timestamp: new Date().toISOString(),
        uiHint: {
          component: "MessageBubble",
          priority: "high",
          collapsible: false,
        },
      };

      expect(resolveComponent(step)).toBe(MessageBubbleVariant);
    });

    it("should return default component when ui_hint.component is invalid", () => {
      const step: ConversationStep = {
        id: "1",
        type: "thought",
        content: "Test",
        timestamp: new Date().toISOString(),
        uiHint: {
          component: "InvalidComponent",
          priority: "low",
          collapsible: true,
        },
      };

      expect(resolveComponent(step)).toBe(ChatStepVariant);
    });

    it("should use type-based heuristics when no ui_hint", () => {
      const responseStep: ConversationStep = {
        id: "1",
        type: "agent_output",
        content: "Test response",
        timestamp: new Date().toISOString(),
        category: "response",
      };

      expect(resolveComponent(responseStep)).toBe(MessageBubbleVariant);
    });

    it("should return InlineText for low-priority status", () => {
      const step: ConversationStep = {
        id: "1",
        type: "status",
        content: "Processing...",
        timestamp: new Date().toISOString(),
        uiHint: {
          component: "ChatStep",
          priority: "low",
          collapsible: true,
        },
      };

      expect(resolveComponent(step)).toBe(InlineTextVariant);
    });
  });

  describe("shouldBeCollapsible", () => {
    it("should respect backend hint when provided", () => {
      const collapsibleStep: ConversationStep = {
        id: "1",
        type: "thought",
        content: "Test",
        timestamp: new Date().toISOString(),
        uiHint: {
          component: "ChatStep",
          priority: "medium",
          collapsible: true,
        },
      };

      expect(shouldBeCollapsible(collapsibleStep)).toBe(true);

      const nonCollapsibleStep: ConversationStep = {
        ...collapsibleStep,
        uiHint: {
          ...collapsibleStep.uiHint!,
          collapsible: false,
        },
      };

      expect(shouldBeCollapsible(nonCollapsibleStep)).toBe(false);
    });

    it("should return false for response category", () => {
      const step: ConversationStep = {
        id: "1",
        type: "agent_output",
        content: "Response",
        timestamp: new Date().toISOString(),
        category: "response",
      };

      expect(shouldBeCollapsible(step)).toBe(false);
    });

    it("should return true for reasoning category", () => {
      const step: ConversationStep = {
        id: "1",
        type: "reasoning",
        content: "Thinking...",
        timestamp: new Date().toISOString(),
        category: "reasoning",
      };

      expect(shouldBeCollapsible(step)).toBe(true);
    });

    it("should default to true when no hint or heuristic matches", () => {
      const step: ConversationStep = {
        id: "1",
        type: "thought",
        content: "Test",
        timestamp: new Date().toISOString(),
      };

      expect(shouldBeCollapsible(step)).toBe(true);
    });
  });

  describe("isRegisteredComponent", () => {
    it("should return true for registered components", () => {
      expect(isRegisteredComponent("ChatStep")).toBe(true);
      expect(isRegisteredComponent("MessageBubble")).toBe(true);
      expect(isRegisteredComponent("InlineText")).toBe(true);
    });

    it("should return false for unregistered components", () => {
      expect(isRegisteredComponent("UnknownComponent")).toBe(false);
      expect(isRegisteredComponent("")).toBe(false);
    });
  });

  describe("getRegisteredComponents", () => {
    it("should return all registered component names", () => {
      const components = getRegisteredComponents();
      expect(components).toContain("ChatStep");
      expect(components).toContain("MessageBubble");
      expect(components).toContain("InlineText");
      expect(components).toHaveLength(3);
    });
  });
});
