import type { Message } from "../api/types";

/**
 * Utility function to group consecutive messages by agent
 */
export function groupMessagesByAgent(messages: Message[]): {
  groupId: string;
  messages: Message[];
  isUserGroup: boolean;
}[] {
  const groups: {
    groupId: string;
    messages: Message[];
    isUserGroup: boolean;
  }[] = [];
  let currentGroup: Message[] = [];
  let currentGroupId = "";
  let currentAuthor = "";
  let currentRole: "user" | "assistant" | "system" | null = null;

  for (const message of messages) {
    const messageAuthor =
      message.author || (message.role === "user" ? "user" : "AI");
    const isNewGroup =
      currentRole !== message.role ||
      (message.role === "assistant" && currentAuthor !== messageAuthor) ||
      // Don't group workflow placeholders with actual responses
      (message.isWorkflowPlaceholder &&
        currentGroup.length > 0 &&
        !currentGroup[0].isWorkflowPlaceholder);

    if (isNewGroup && currentGroup.length > 0) {
      groups.push({
        groupId: currentGroupId,
        messages: currentGroup,
        isUserGroup: currentRole === "user",
      });
      currentGroup = [];
    }

    if (currentGroup.length === 0) {
      currentGroupId = message.groupId || `group-${groups.length}`;
    }

    currentGroup.push(message);
    currentAuthor = messageAuthor;
    currentRole = message.role;
  }

  // Push the last group
  if (currentGroup.length > 0) {
    groups.push({
      groupId: currentGroupId,
      messages: currentGroup,
      isUserGroup: currentRole === "user",
    });
  }

  return groups;
}
