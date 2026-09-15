/**
 * Reticle End-to-End Application Journey Verification
 * Drives Reticle's Chromium engine through the complete user onboarding and telemetry lifecycle:
 *
 *   Dashboard -> Generate 1-Click Join Link -> Show QR -> Open Phone Join Page
 *   -> Claim Ticket -> Unique Node ID Issued -> REGISTERING -> 30s Heartbeat -> ONLINE
 *   -> Dashboard Updates Live -> Security Invariant Checks
 */

const path = require("path");
const reticleModulePath = "/home/system/.local/lib/node_modules/@reticlehq/server/node_modules/playwright";
const { chromium } = require(reticleModulePath);

const BASE_URL = process.env.TEST_BASE_URL || "http://127.0.0.1:8080";

const assertions = [];

function assert(condition, testName, details = "") {
  const passed = Boolean(condition);
  const mark = passed ? "[PASS]" : "[FAIL]";
  console.log(`${mark} ${testName}: ${details}`);
  assertions.push({ name: testName, passed, details });
  if (!passed) {
    throw new Error(`Assertion failed: ${testName} - ${details}`);
  }
}

async function runReticleJourney() {
  console.log("==================================================");
  console.log("STARTING RETICLE E2E USER JOURNEY VERIFICATION");
  console.log(`Target Application: ${BASE_URL}`);
  console.log("==================================================\n");

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"]
  });

  try {
    const context = await browser.newContext({
      userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
    });

    // ----------------------------------------------------
    // STEP 1: LOAD CENTRAL DASHBOARD
    // ----------------------------------------------------
    console.log("--- 1. DASHBOARD INITIALIZATION ---");
    const dashboardPage = await context.newPage();
    await dashboardPage.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });

    const title = await dashboardPage.title();
    assert(title.includes("Clipper-X Central Device Dashboard"), "Dashboard Title Verified", `Title: "${title}"`);

    // Verify stat cards present
    const totalEl = await dashboardPage.$("#stat-total");
    assert(totalEl !== null, "Total Devices Stat Card Present");
    const initialTotal = parseInt(await totalEl.innerText(), 10) || 0;
    console.log(`  Initial Registered Devices in Dashboard: ${initialTotal}`);

    // ----------------------------------------------------
    // STEP 2: GENERATE 1-CLICK JOIN LINK & TEST QR
    // ----------------------------------------------------
    console.log("\n--- 2. ONE-CLICK JOIN LINK & QR GENERATION ---");
    // Click "+ Create 1-Click Join Link"
    await dashboardPage.click("button:has-text('+ Create 1-Click Join Link')");
    await dashboardPage.waitForSelector("#join-modal", { state: "visible" });

    const joinUrlInput = await dashboardPage.$("#modal-join-url");
    const joinUrl = await joinUrlInput.inputValue();
    assert(joinUrl.includes("/join?token=cne_"), "Generated Single-Use Join URL", `URL: ${joinUrl}`);

    // Test Show QR toggle
    await dashboardPage.click("#qr-btn");
    await dashboardPage.waitForTimeout(300);
    const qrCanvas = await dashboardPage.$("#qr-canvas");
    const qrVisible = await qrCanvas.isVisible();
    assert(qrVisible, "QR Code Canvas Rendered and Displayed");

    // Close modal
    await dashboardPage.click("button:has-text('Close')");
    await dashboardPage.waitForTimeout(200);

    // ----------------------------------------------------
    // STEP 3: PHONE DEVICE ONBOARDING JOURNEY
    // ----------------------------------------------------
    console.log("\n--- 3. MOBILE PHONE ZERO-INSTALL ONBOARDING ---");
    // Open a new phone tab
    const phoneContext = await browser.newContext({
      userAgent: "Mozilla/5.0 (Linux; Android 14; Mobile) Chrome/124.0 Mobile Safari/537.36"
    });
    const phonePage = await phoneContext.newPage();
    await phonePage.goto(joinUrl, { waitUntil: "networkidle" });

    const phoneTitle = await phonePage.title();
    assert(phoneTitle.includes("Clipper-X Node Join"), "Join Page Rendered on Mobile Client");

    const detectedPlatform = await phonePage.$eval("#detected-platform", el => el.textContent);
    assert(detectedPlatform.toLowerCase().includes("android") || detectedPlatform.toLowerCase().includes("linux"), "Mobile Client Platform Auto-Detected", `Platform: ${detectedPlatform}`);

    // Click "Connect Device"
    await phonePage.click("#connect-btn");

    // Wait for enrollment claim and initial heartbeat
    await phonePage.waitForSelector(".badge.online", { timeout: 10000 });
    const badgeText = await phonePage.$eval("#status-badge", el => el.textContent);
    assert(badgeText === "ONLINE", "Device Status Transitioned to ONLINE", `Badge: ${badgeText}`);

    const issuedNodeId = await phonePage.$eval("#node-id-val", el => el.textContent);
    assert(issuedNodeId.startsWith("node_"), "Unique Node ID Assigned to Device", `Node ID: ${issuedNodeId}`);

    const observedIp = await phonePage.$eval("#public-ip-val", el => el.textContent);
    assert(observedIp.length > 0, "Public Egress IP Observed", `IP: ${observedIp}`);

    const hbStat = await phonePage.$eval("#hb-stat-val", el => el.textContent);
    assert(hbStat.includes("ONLINE"), "Heartbeat Pulse Confirmed Active (30s)", `Status: ${hbStat}`);

    // ----------------------------------------------------
    // STEP 4: VERIFY CENTRAL DASHBOARD LIVE UPDATE
    // ----------------------------------------------------
    console.log("\n--- 4. LIVE DASHBOARD UPDATE VERIFICATION ---");
    // Wait for the 3-second dashboard auto-polling cycle
    console.log("  Waiting for dashboard 3-second live polling update...");
    await dashboardPage.waitForTimeout(4000);

    const updatedTotal = parseInt(await dashboardPage.$eval("#stat-total", el => el.textContent), 10);
    assert(updatedTotal === initialTotal + 1, "Dashboard Total Devices Incremented by 1", `New Total: ${updatedTotal}`);

    const tableHtml = await dashboardPage.$eval("#device-table-body", el => el.innerHTML);
    assert(tableHtml.includes(issuedNodeId), "Enrolled Device Appears in Live Dashboard Table", `Found: ${issuedNodeId}`);
    assert(tableHtml.includes("ONLINE"), "Device Status Displayed as ONLINE in Table");
    assert(tableHtml.includes("HEALTHY"), "Device Health Displayed as HEALTHY in Table");

    // ----------------------------------------------------
    // STEP 5: SECURITY & INVARIANT ASSERTIONS
    // ----------------------------------------------------
    console.log("\n--- 5. SECURITY & REPLAY INVARIANT VERIFICATIONS ---");

    // 5.1 Single-Use Ticket Replay Rejected
    const replayContext = await browser.newContext();
    const replayPage = await replayContext.newPage();
    await replayPage.goto(joinUrl, { waitUntil: "networkidle" });
    await replayPage.click("#connect-btn");
    await replayPage.waitForTimeout(1000);
    const errorMsg = await replayPage.$eval("#error-msg", el => el.textContent);
    assert(errorMsg.length > 0, "Single-Use Ticket Replay Rejected by Backend", `Error: "${errorMsg}"`);
    await replayContext.close();

    // 5.2 Invalid Ticket Rejected
    const invalidContext = await browser.newContext();
    const invalidPage = await invalidContext.newPage();
    await invalidPage.goto(`${BASE_URL}/join?token=cne_invalid_forged_ticket_12345`, { waitUntil: "networkidle" });
    await invalidPage.click("#connect-btn");
    await invalidPage.waitForTimeout(1000);
    const invalidError = await invalidPage.$eval("#error-msg", el => el.textContent);
    assert(invalidError.length > 0, "Forged Ticket Claim Rejected by Backend", `Error: "${invalidError}"`);
    await invalidContext.close();

    // 5.3 Unauthenticated Heartbeat Rejected
    const unauthRes = await fetch(`${BASE_URL}/api/v1/nodes/${issuedNodeId}/heartbeat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sdk_version: "1.0.0" })
    });
    assert(unauthRes.status === 401, "Unauthenticated Heartbeat Ping Rejected (401)", `HTTP Status: ${unauthRes.status}`);

    // 5.4 Cross-Node Access Isolation
    const crossNodeRes = await fetch(`${BASE_URL}/api/v1/nodes/${issuedNodeId}/heartbeat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer cnx_tok_tampered_alien_token"
      },
      body: JSON.stringify({ sdk_version: "1.0.0" })
    });
    assert(crossNodeRes.status === 401 || crossNodeRes.status === 403, "Cross-Node Unauthorized Modification Blocked (401/403)", `HTTP Status: ${crossNodeRes.status}`);

    // ----------------------------------------------------
    // STEP 6: CLEAN TEARDOWN & RECOVERY VERIFICATION
    // ----------------------------------------------------
    console.log("\n--- 6. DEVICE DISCONNECT & SHUTDOWN CLEANUP ---");
    await phonePage.click("#disconnect-btn");
    await phonePage.waitForTimeout(500);
    const disconnectedBadge = await phonePage.$eval("#status-badge", el => el.textContent);
    assert(disconnectedBadge === "Disconnected", "Heartbeat Timer Cleanly Stopped on Disconnect");

    await phoneContext.close();
    await context.close();

    console.log("\n==================================================");
    console.log("RETICLE E2E JOURNEY VERIFICATION COMPLETED (100% PASS)");
    console.log("==================================================");

    const report = {
      timestamp: new Date().toISOString(),
      tool: "Reticle Playwright Engine (chromium-1243)",
      targetUrl: BASE_URL,
      totalAssertions: assertions.length,
      passedCount: assertions.filter(a => a.passed).length,
      failedCount: assertions.filter(a => !a.passed).length,
      verdict: "PASS",
      assertions
    };

    require("fs").writeFileSync(
      path.join(__dirname, "../reticle_journey_results.json"),
      JSON.stringify(report, null, 2)
    );
    console.log("Results written to reticle_journey_results.json\n");

  } finally {
    await browser.close();
  }
}

runReticleJourney().catch((err) => {
  console.error("Reticle Journey Failed:", err.message);
  process.exit(1);
});
