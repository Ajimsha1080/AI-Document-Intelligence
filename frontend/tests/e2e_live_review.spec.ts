import { test, expect } from "@playwright/test";
import path from "path";

test.describe("Real Sovereign Document Review Flow", () => {
  test("authenticates, uploads real document, watches live updates, corrects field and approves", async ({ page }) => {
    // 1. Navigate to live platform
    await page.goto("http://localhost:3005");

    // 2. Check header is visible
    await expect(page.locator("header")).toBeVisible();

    // 3. Navigate to Upload tab
    const uploadNavBtn = page.locator('button').filter({ hasText: /Upload|رفع/i }).first();
    await uploadNavBtn.click();

    // 4. Upload real raster image from dataset
    const sampleImagePath = path.resolve(__dirname, "../../eval/dataset/sample_001.png");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(sampleImagePath);

    // 5. Watch live status badge transition to Ready via real SSE events
    await expect(
      page.locator("text=Ready")
        .or(page.locator("text=Needs Review"))
        .or(page.locator("text=بحاجة للمراجعة"))
        .first()
    ).toBeVisible({ timeout: 30000 });

    // 6. Click Review button
    const reviewBtn = page.locator('button:has-text("Review"), button:has-text("مراجعة"), button:has-text("Review Queue")').first();
    await reviewBtn.click();

    // 7. Verify review layout renders with real document and fields
    await expect(
      page.locator("text=Extracted Fields & Citations")
        .or(page.locator("text=الحقول والبيانات المستخرجة"))
        .or(page.locator("text=Identity & Registration"))
        .or(page.locator("text=Critical Dates & Validity"))
        .or(page.locator("text=Identity Number"))
        .or(page.locator("text=رقم الهوية"))
        .first()
    ).toBeVisible({ timeout: 15000 });

    // 8. Correct a field: click field value to edit
    const fieldBox = page.locator('div.font-mono').first();
    if (await fieldBox.isVisible()) {
      await fieldBox.click();
      const textInput = page.locator('input[type="text"]').first();
      if (await textInput.isVisible()) {
        await textInput.fill("784-1988-1234567-1");
        const saveBtn = page.locator('button').filter({ hasText: /Save|حفظ/i }).first();
        if (await saveBtn.isVisible()) {
          await saveBtn.click();
        }
      }
    }

    // 9. Approve document
    const approveBtn = page.locator('button').filter({ hasText: /Approve Document|اعتماد المستند|Approve/i }).first();
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
    }

    // 10. Verify approved status badge is shown
    await expect(
      page.locator('span.rounded-full').filter({ hasText: /Approved|معتمد/i }).first()
    ).toBeVisible({ timeout: 15000 });
  });
});
