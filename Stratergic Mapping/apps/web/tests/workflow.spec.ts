import { expect, test } from "@playwright/test";

test("landing page exposes required intake and upload layout", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Generate a full 7Cs analysis" })).toBeVisible();
  await expect(page.getByLabel("Project name")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Upload supporting files" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent projects" })).toBeVisible();
  await expect(page.getByText("What this prototype demonstrates")).toHaveCount(0);
});

test("generation block banner explains missing intake fields", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Geography").fill("");
  await page.getByRole("button", { name: "Generate 7Cs" }).click();
  await expect(page.getByText("Generation blocked: Geography is needed to scope sources and market context.")).toBeVisible();
});
