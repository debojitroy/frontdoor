import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("stream, inspect, review, export and reload without changing the model decision", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "The sorting desk." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Live inference", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Run demo stream" }).click();
  await expect(
    page.getByRole("button", { name: "Stream complete" }),
  ).toBeVisible({ timeout: 15000 });
  await page
    .getByRole("button", {
      name: /Workspace security.*Your session needs attention/,
    })
    .click();
  await expect(page.getByText("LAYA DECISION", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Recorded inference", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Edit & test" }),
  ).toBeDisabled();
  await page.getByText("Compare the same message", { exact: true }).click();
  await expect(page.getByText("TF–IDF + logistic regression")).toBeVisible();
  const before = await page.request
    .get("/api/messages/D02/export")
    .then((r) => r.json());
  await page
    .getByRole("button", { name: "Would you make the same call?" })
    .click();
  await page.getByLabel("Your assessment").selectOption("phishing");
  await page
    .getByLabel("Review note")
    .fill("Asks for an authentication secret.");
  await page.getByRole("button", { name: "Save review" }).click();
  await expect(
    page.getByText("Reviewed as phishing", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Reviewed as phishing", { exact: true }),
  ).toBeVisible();
  const after = await page.request
    .get("/api/messages/D02/export")
    .then((r) => r.json());
  expect(after.prediction).toEqual(before.prediction);
  const exported = await page.request
    .get("/api/export/reviews")
    .then((r) => r.json());
  expect(exported.examples).toHaveLength(1);
  expect(exported.examples[0].label).toBe("phishing");
});

test("model lab and failure explorer expose the measured limitations", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Model lab" }).click();
  await expect(
    page.getByRole("heading", { name: "The training notebook." }),
  ).toBeVisible();
  await expect(
    page.getByText("3 of 5 frozen quality checks pass"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Inspect the full evaluation" })
    .click();
  await expect(
    page.getByRole("heading", { name: "The evaluation record." }),
  ).toBeVisible();
  await expect(page.getByText("13 cases", { exact: true })).toBeVisible();
  await page.getByLabel("Show failures only").uncheck();
  await expect(page.getByText("30 cases", { exact: true })).toBeVisible();
  await page.getByLabel("Dataset", { exact: true }).selectOption("sms");
  await expect(page.getByText("200 cases", { exact: true })).toBeVisible();
  await page.getByLabel("Show failures only").check();
  await expect(page.getByText("10 cases", { exact: true })).toBeVisible();
  await page.getByLabel("Model", { exact: true }).selectOption("base");
  await expect(page.getByText("16 cases", { exact: true })).toBeVisible();
});

test("keyboard dialog and responsive layout stay usable", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "About this experiment" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const tabLabel = page
      .getByRole("navigation", { name: "Main navigation" })
      .getByText("Screening desk", { exact: true });
    expect(
      await tabLabel.evaluate(
        (element) => element.getBoundingClientRect().width,
      ),
    ).toBeGreaterThan(30);
    await page.getByRole("button", { name: "Evaluation", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "The evaluation record." }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  }
});
