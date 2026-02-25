import { expect, test } from "@playwright/test";

const login = async (page: import("@playwright/test").Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
};

test("loads the kanban board", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});

test("chat applies AI updates", async ({ page }) => {
  await page.route("**/api/ai/board", async (route) => {
    const body = {
      schemaVersion: 1,
      board: {
        columns: [
          { id: "col-backlog", title: "Backlog", cardIds: ["card-1"] },
          { id: "col-discovery", title: "Discovery", cardIds: [] },
          { id: "col-progress", title: "In Progress", cardIds: [] },
          { id: "col-review", title: "Review", cardIds: [] },
          { id: "col-done", title: "Done", cardIds: [] },
        ],
        cards: {
          "card-1": {
            id: "card-1",
            title: "AI updated title",
            details: "Updated via AI",
          },
        },
      },
      operations: [
        {
          type: "update_card",
          cardId: "card-1",
          title: "AI updated title",
          details: "Updated via AI",
        },
      ],
    };

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await login(page);
  await page.getByLabel(/ask the ai/i).fill("Update card-1 title");
  await page.getByRole("button", { name: /send/i }).click();

  await expect(page.getByText("AI updated title")).toBeVisible();
  await expect(page.getByText(/applied 1 update/i)).toBeVisible();
});
