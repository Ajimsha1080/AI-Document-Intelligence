import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

test.describe("Frontend Security & Honest Authentication", () => {
  test("login page never calls /auth/login without explicit user submission", async ({ page }) => {
    let authLoginCalled = false;

    page.on("request", (req) => {
      if (req.url().includes("/auth/login")) {
        authLoginCalled = true;
      }
    });

    // Navigate with potential auto-login query param
    await page.goto("http://localhost:3000/?autologin=true");

    // Wait 2 seconds to ensure no timeout or auto-trigger occurs
    await page.waitForTimeout(2000);

    // Verify /auth/login was NEVER called
    expect(authLoginCalled).toBe(false);

    // Verify email and password fields are present and empty
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    expect(await emailInput.inputValue()).toBe("");
    expect(await passwordInput.inputValue()).toBe("");
  });

  test("frontend/src source code contains no hardcoded credentials or AdminSecurePass", () => {
    const srcDir = path.resolve(__dirname, "../src");

    function checkDir(dir: string) {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          checkDir(fullPath);
        } else if (entry.isFile() && (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))) {
          const content = fs.readFileSync(fullPath, "utf-8");
          expect(content.includes("AdminSecurePass")).toBe(false);
          expect(content.includes("admin@alhilal-demo.ae")).toBe(false);
        }
      }
    }

    checkDir(srcDir);
  });
});
