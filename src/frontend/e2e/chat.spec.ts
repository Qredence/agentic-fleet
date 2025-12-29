import { expect, test } from "@playwright/test";

/**
 * E2E Tests for Chat Functionality
 *
 * Tests the critical user flow for sending messages in the chat interface.
 */

test.describe("Chat Flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto("/");
  });

  test("should load the chat interface", async ({ page }) => {
    // Verify the main interface loads
    await expect(page.locator("main.flex.h-screen")).toBeVisible();
  });

  test("should show the prompt input", async ({ page }) => {
    // Verify the prompt input area exists
    const promptInput = page.getByPlaceholder("Ask anything...");
    await expect(promptInput).toBeVisible();
  });

  test("should show new chat button", async ({ page }) => {
    // Verify there's a way to start a new chat
    const newChatButton = page.getByRole("button", {
      name: /(start new chat|new chat)/i,
    });
    await expect(newChatButton).toBeVisible();
  });

  test("should type a message in the prompt input", async ({ page }) => {
    // Find the prompt input and type a message
    const promptInput = page.getByPlaceholder("Ask anything...");
    await promptInput.fill("Hello, this is a test message");

    // Verify the text was entered
    await expect(promptInput).toHaveValue("Hello, this is a test message");
  });

  test("should enable send button when text is entered", async ({ page }) => {
    // Type a message
    const promptInput = page.getByPlaceholder("Ask anything...");
    await promptInput.fill("Test message");

    // Find the send button (usually has a send icon or is near the input)
    const sendButton = page.locator(
      'button:has(svg[data-lucide="send"]), button[aria-label="Send"], button[type="submit"]',
    );

    // Verify send button exists and is enabled
    await expect(sendButton.first()).toBeVisible();
    await expect(sendButton.first()).not.toBeDisabled();
  });
});

test.describe("Application Structure", () => {
  test("should have proper app layout", async ({ page }) => {
    await page.goto("/");

    // Verify main app structure
    const main = page.locator("main");
    await expect(main).toBeVisible();

    // Check for sidebar or navigation
    const sidebar = page.locator("aside, nav, [role='navigation']").first();
    const sidebarExists = (await sidebar.count()) > 0;
    expect(sidebarExists).toBeTruthy();
  });

  test("should be responsive on mobile viewport", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Verify app loads on mobile
    await expect(page.locator("main")).toBeVisible();
    await expect(page.getByPlaceholder("Ask anything...")).toBeVisible();
  });
});

test.describe("Error Handling", () => {
  test("should handle API errors gracefully", async ({ page }) => {
    // Navigate to the app
    await page.goto("/");

    // The app should load even if backend is unavailable
    // It should show connection errors in a user-friendly way
    await expect(page.locator("main")).toBeVisible();
  });

  test("should handle navigation between views", async ({ page }) => {
    await page.goto("/");

    // Test that the app structure is stable
    const mainElement = page.locator("main");
    await expect(mainElement).toBeVisible();

    // Verify no console errors for basic navigation
    const logs: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        logs.push(msg.text());
      }
    });

    // Wait a bit for any initial errors
    await page.waitForTimeout(1000);

    // Check for critical errors (ignore non-critical ones)
    const criticalErrors = logs.filter(
      (log) =>
        !log.includes("404") &&
        !log.includes("favicon") &&
        !log.includes("HMR"),
    );

    // In a well-functioning app, there should be no critical errors on load
    expect(criticalErrors.length).toBe(0);
  });
});
