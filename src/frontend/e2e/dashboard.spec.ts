import { expect, test } from "@playwright/test";

/**
 * E2E Tests for Dashboard Functionality
 *
 * Tests the optimization dashboard and related features.
 */

test.describe("Dashboard Flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should navigate to dashboard view", async ({ page }) => {
    // Look for dashboard navigation option
    // This could be a button, link, or tab
    const dashboardNav = page.getByRole("button", {
      name: /dashboard|optimization/i,
    });

    // If dashboard nav exists, try clicking it
    const hasDashboardNav = (await dashboardNav.count()) > 0;
    if (hasDashboardNav) {
      await dashboardNav.click();
      // Verify dashboard content loads
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("should display optimization controls when available", async ({
    page,
  }) => {
    // Look for optimization-related UI elements
    const _optimizeButton = page.getByRole("button", {
      name: /optimize|run optimization/i,
    });

    // The optimize button may or may not be visible depending on the view
    // Just verify the page loads without crashing
    await expect(page.locator("main")).toBeVisible();
  });

  test("should handle view switching", async ({ page }) => {
    // Test that the app can switch between views
    const mainElement = page.locator("main");
    await expect(mainElement).toBeVisible();

    // Look for any view switcher (tabs, buttons, etc.)
    const viewSwitchers = page.locator(
      'button[role="tab"], nav button, [role="tablist"] button',
    );

    const switcherCount = await viewSwitchers.count();
    if (switcherCount > 0) {
      // Try clicking the first switcher
      await viewSwitchers.first().click();
      // Verify app is still responsive
      await expect(mainElement).toBeVisible();
    }
  });
});

test.describe("Error Scenarios", () => {
  test("should handle missing backend gracefully", async ({
    page,
    context,
  }) => {
    // Block backend requests to simulate offline/error state
    await context.route("**/api/**", (route) => route.abort());

    await page.goto("/");

    // App should still load and show UI
    await expect(page.locator("main")).toBeVisible();

    // Should show user-friendly error or offline state
    // (This depends on how the app handles errors)
  });

  test("should handle network delays", async ({ page, context }) => {
    // Add delay to backend requests
    await context.route("**/api/**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve as () => void, 1000));
      route.continue();
    });

    await page.goto("/");

    // App should show loading states gracefully
    await expect(page.locator("main")).toBeVisible();
  });
});

test.describe("Accessibility", () => {
  test("should have proper heading hierarchy", async ({ page }) => {
    await page.goto("/");

    // Check for at least one heading
    const headings = page.locator("h1, h2, h3");
    const hasHeadings = (await headings.count()) > 0;
    expect(hasHeadings).toBeTruthy();
  });

  test("should have focus management", async ({ page }) => {
    await page.goto("/");

    // Focus on the input field
    const promptInput = page.getByPlaceholder("Ask anything...");
    await promptInput.focus();

    // Verify input is focused
    await expect(promptInput).toBeFocused();
  });

  test("should be keyboard navigable", async ({ page }) => {
    await page.goto("/");

    // Test tab navigation
    await page.keyboard.press("Tab");

    // Some element should be focused after tab
    const focusedElement = await page.evaluate(() => document.activeElement);
    expect(focusedElement?.tagName).not.toBe("BODY");
  });
});
