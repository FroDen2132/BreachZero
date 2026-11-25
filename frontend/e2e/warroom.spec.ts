import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOTS_DIR = path.resolve(__dirname, '../../test-artifacts/screenshots');

interface PageErrorTracker {
  label: string;
  errors: string[];
}

function attachErrorListeners(page: Page, label: string): PageErrorTracker {
  const tracker: PageErrorTracker = { label, errors: [] };
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      tracker.errors.push(`[${label} console.error] ${msg.text()}`);
    }
  });
  page.on('pageerror', (err) => {
    tracker.errors.push(`[${label} pageerror] ${err.message}`);
  });
  page.on('response', (res) => {
    if (res.status() >= 400) {
      tracker.errors.push(`[${label} HTTP ${res.status()}] ${res.url()}`);
    }
  });
  return tracker;
}

async function assertPixelLayoutHealth(page: Page, label: string): Promise<void> {
  const report = await page.evaluate(() => {
    const issues: string[] = [];

    // 1. Horizontal overflow check
    if (document.documentElement.scrollWidth > window.innerWidth) {
      issues.push(
        `Horizontal overflow: scrollWidth=${document.documentElement.scrollWidth} > innerWidth=${window.innerWidth}`,
      );
    }

    // 2. Single-line HP readout check
    const hpNodes = Array.from(document.querySelectorAll('span')).filter((el) =>
      /\d+\s*\/\s*100\s*HP/.test(el.textContent || ''),
    );
    for (const el of hpNodes) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const range = document.createRange();
      range.selectNodeContents(el);
      const clientRects = Array.from(range.getClientRects());
      const distinctLines = new Set(clientRects.map((r) => Math.round(r.top))).size;
      if (distinctLines > 1) {
        issues.push(`HP text wrapped into ${distinctLines} lines: "${el.textContent}"`);
      }
    }

    // 3. Sprite integrity and integer multiple of 16 check
    for (const img of Array.from(document.querySelectorAll('img'))) {
      const rect = img.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (!img.complete || img.naturalWidth === 0) {
        issues.push(`Broken img: ${img.getAttribute('src')}`);
      }
      const w = Math.round(rect.width);
      const h = Math.round(rect.height);
      if (w % 16 !== 0 || h % 16 !== 0) {
        issues.push(`Non-integer 16x sprite size (${w}x${h}) on ${img.getAttribute('src')}`);
      }
    }

    // 4. Zero border-radius on pixel components
    const uiSelector =
      '.pixel-panel, .pixel-card, .px-btn, .pixel-badge, .pixel-input, .pixel-select, .pixel-checkbox-box';
    for (const el of Array.from(document.querySelectorAll(uiSelector))) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const br = getComputedStyle(el).borderRadius;
      if (br !== '0px') {
        issues.push(`Non-zero borderRadius (${br}) on ${el.className}`);
      }
    }

    // 5. CrispEdges <rect>-only inline SVGs
    for (const svg of Array.from(document.querySelectorAll('svg'))) {
      const rect = svg.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) continue;
      if (svg.getAttribute('shape-rendering') !== 'crispEdges') {
        issues.push(`SVG missing shape-rendering="crispEdges"`);
      }
      const forbidden = svg.querySelectorAll('path, circle, ellipse, polygon, polyline');
      if (forbidden.length > 0) {
        issues.push(`SVG contains ${forbidden.length} forbidden vector primitives`);
      }
    }

    return issues;
  });

  expect(report, `Layout/Anti-Slop issues on ${label}`).toEqual([]);
}

test('BreachZero full multi-tab war room flow & visual layout health', async ({ browser }) => {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  const adminContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const hostContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const aliContext = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const zeynepContext = await browser.newContext({ viewport: { width: 1280, height: 720 } });

  const adminPage = await adminContext.newPage();
  const hostPage = await hostContext.newPage();
  const aliPage = await aliContext.newPage();
  const zeynepPage = await zeynepContext.newPage();

  const trackers = [
    attachErrorListeners(adminPage, 'admin'),
    attachErrorListeners(hostPage, 'host'),
    attachErrorListeners(aliPage, 'ali'),
    attachErrorListeners(zeynepPage, 'zeynep'),
  ];

  try {
    // 1. /admin creates a room & verifies both scenarios checked
    await adminPage.goto('/admin');
    await expect(adminPage.getByText('1. YENİ TURNUVA ODASI OLUŞTUR')).toBeVisible();
    await assertPixelLayoutHealth(adminPage, '/admin initial');

    await adminPage.getByRole('button', { name: 'YENİ ODA OLUŞTUR' }).click();
    const roomCodeLocator = adminPage.locator('section').filter({ hasText: 'AKTİF ODA KODU' }).locator('.font-display-ascii');
    await expect(roomCodeLocator).toHaveText(/^BZ[A-Z0-9]{4}$/);
    const roomCode = (await roomCodeLocator.innerText()).trim();

    await expect(adminPage.locator('.pixel-checkbox-box.is-checked')).toHaveCount(2);
    await expect(adminPage.getByText('ALT-1001')).toBeVisible();
    await expect(adminPage.getByText('ALT-4088')).toBeVisible();
    await assertPixelLayoutHealth(adminPage, '/admin room created');

    // 2. /host (1440x900) joins & shows 3 teams at 100 / 100 HP
    await hostPage.goto(`/host?room=${roomCode}`);
    await expect(hostPage.getByText(roomCode)).toBeVisible();
    await expect(hostPage.getByText('100 / 100 HP')).toHaveCount(3);
    await assertPixelLayoutHealth(hostPage, '/host lobby');

    // 3. /play Ali (?room=...) and Zeynep (manual room code entry) join ALPHA SQUAD
    await aliPage.goto(`/play?room=${roomCode}`);
    await expect(aliPage.locator('button', { hasText: 'Ali' }).getByText('SEÇİLİ')).toBeVisible();
    await aliPage.locator('#play-nick').fill('Ali');
    await aliPage.locator('#play-team').selectOption('team_1');
    await aliPage.getByRole('button', { name: 'TERMİNALE BAĞLAN' }).click();
    await expect(aliPage.getByText('ORTAK ALARM KUYRUĞU')).toBeVisible();

    await zeynepPage.goto('/play');
    await zeynepPage.locator('#play-room').fill(roomCode);
    await zeynepPage.locator('#play-nick').fill('Zeynep');
    await zeynepPage.locator('#play-team').selectOption('team_1');
    await zeynepPage.locator('button', { hasText: 'Zeynep' }).click();
    await expect(zeynepPage.locator('button', { hasText: 'Zeynep' }).getByText('SEÇİLİ')).toBeVisible();
    await zeynepPage.getByRole('button', { name: 'TERMİNALE BAĞLAN' }).click();
    await expect(zeynepPage).toHaveURL(new RegExp(`room=${roomCode}`));
    await expect(zeynepPage.getByText('ORTAK ALARM KUYRUĞU')).toBeVisible();

    // 4. Admin starts wave -> both players see 2 alerts
    await adminPage.getByRole('button', { name: 'DALGAYI BAŞLAT' }).click();
    const aliCard1001 = aliPage.locator('article').filter({ hasText: 'ALT-1001' });
    const aliCard4088 = aliPage.locator('article').filter({ hasText: 'ALT-4088' });
    const zeynepCard1001 = zeynepPage.locator('article').filter({ hasText: 'ALT-1001' });
    const zeynepCard4088 = zeynepPage.locator('article').filter({ hasText: 'ALT-4088' });

    await expect(aliCard1001).toBeVisible();
    await expect(aliCard4088).toBeVisible();
    await expect(zeynepCard1001).toBeVisible();
    await expect(zeynepCard4088).toBeVisible();

    // Ali claims ALT-1001 -> Zeynep sees CLAIMED BY ALİ
    await aliCard1001.getByRole('button', { name: '[CLAIM]' }).click();
    await expect(aliCard1001.getByText('SİZDE')).toBeVisible();
    await expect(zeynepCard1001.getByText('CLAIMED BY ALİ')).toBeVisible();

    // Ali runs [İÇ CMDB] -> Kanıt Günlüğü updates -> screenshot 01
    await aliPage.getByRole('button', { name: /\[İÇ CMDB\]/ }).click();
    await expect(aliPage.getByText('KANIT GÜNLÜĞÜ (1)')).toBeVisible();
    await expect(aliPage.getByText(/BACKUP-SRV-01 onaylı yedekleme sunucusu/)).toBeVisible();
    await assertPixelLayoutHealth(aliPage, '/play active desk');
    await aliPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, '01-play-active-desk.png'),
      fullPage: true,
    });

    // Ali triggers F5 reload -> reconnect restores claim + persisted evidence
    await aliPage.reload();
    const aliCard1001AfterReload = aliPage.locator('article').filter({ hasText: 'ALT-1001' });
    await expect(aliCard1001AfterReload.getByText('SİZDE')).toBeVisible();
    await aliCard1001AfterReload.click();
    await expect(aliPage.getByText('KANIT GÜNLÜĞÜ (1)')).toBeVisible();
    await expect(aliPage.getByText(/BACKUP-SRV-01 onaylı yedekleme sunucusu/)).toBeVisible();

    // Ali releases -> Zeynep claims -> sees existing evidence -> stamps FALSE POSITIVE
    await aliCard1001AfterReload.getByRole('button', { name: '[RELEASE]' }).click();
    await expect(zeynepCard1001.getByRole('button', { name: '[CLAIM]' })).toBeVisible();
    await zeynepCard1001.getByRole('button', { name: '[CLAIM]' }).click();
    await zeynepCard1001.click();
    await expect(zeynepPage.getByText('KANIT GÜNLÜĞÜ (1)')).toBeVisible();
    await zeynepPage.getByRole('button', { name: '[FALSE POSITIVE - KAPAT]' }).click();
    await expect(zeynepCard1001.getByText('ÇÖZÜLDÜ')).toBeVisible();
    await expect(zeynepPage.locator('.pixel-seal')).toHaveCSS('opacity', '1');
    await assertPixelLayoutHealth(zeynepPage, '/play stamped');
    await zeynepPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, '02-play-stamped.png'),
      fullPage: true,
    });

    // 5. Admin pauses wave -> SLA frozen over 2 seconds -> screenshot 04 -> resume
    await adminPage.getByRole('button', { name: 'DURAKLAT (PAUSE)' }).click();
    await expect(aliPage.getByText(/OYUN MODERATÖR TARAFINDAN DURAKLATILDI/)).toBeVisible();
    await expect(adminPage.getByText('DURUM: PAUSED')).toBeVisible();
    await assertPixelLayoutHealth(adminPage, '/admin paused');
    await adminPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, '04-admin-paused.png'),
      fullPage: true,
    });

    const timerLocator = aliCard4088.locator('.font-display-ascii').last();
    const slaBeforePause = (await timerLocator.innerText()).trim();
    await aliPage.waitForTimeout(2200);
    const slaAfterPause = (await timerLocator.innerText()).trim();
    expect(slaAfterPause).toBe(slaBeforePause);

    await adminPage.getByRole('button', { name: 'DEVAM ET' }).click();
    await expect(adminPage.getByText('DURUM: ACTIVE')).toBeVisible();

    // 6. Ali claims ALT-4088, uses [WHOIS] (crispEdges SVG fallback), intentionally triggers FN (-40 HP)
    await aliCard4088.getByRole('button', { name: '[CLAIM]' }).click();
    await aliCard4088.click();

    const whoisBtn = aliPage.getByRole('button', { name: /\[WHOIS\]/ });
    const whoisSvgCheck = await whoisBtn.evaluate((btn) => {
      const svg = btn.querySelector('svg');
      if (!svg) return { ok: false, reason: 'missing svg' };
      return {
        ok:
          svg.getAttribute('shape-rendering') === 'crispEdges' &&
          svg.querySelectorAll('rect').length > 0 &&
          svg.querySelectorAll('path, circle, ellipse').length === 0,
        reason: 'svg primitive check',
      };
    });
    expect(whoisSvgCheck.ok).toBe(true);

    await whoisBtn.click();
    await expect(aliPage.getByText('KANIT GÜNLÜĞÜ (1)')).toBeVisible();
    await expect(aliPage.getByText(/AS205100/)).toBeVisible();

    await aliPage.getByRole('button', { name: '[FALSE POSITIVE - KAPAT]' }).click();
    await expect(aliPage.getByText('60 / 100 HP')).toBeVisible();
    await expect(hostPage.getByText('60 / 100 HP')).toBeVisible();
    await expect(hostPage.getByText(/-250 Puan, -40 HP/)).toBeVisible();
    await expect(hostPage.getByText('WebSocket bağlantı hatası oluştu.')).toHaveCount(0);
    await assertPixelLayoutHealth(hostPage, '/host live damage');
    await hostPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, '03-host-live-damage.png'),
      fullPage: true,
    });

    // 7. Admin ends match -> Debrief opens -> screenshot 05
    await adminPage.getByRole('button', { name: 'MAÇI BİTİR & DEBRIEF' }).click();
    await expect(adminPage.getByText('MAÇ SONU HATA ANALİZİ (DEBRIEF)')).toBeVisible();
    await expect(adminPage.getByText('MITRE ATT&CK: T1558.003, T1071.001')).toBeVisible();
    await expect(adminPage.getByText(/Stajyer kullanıcısı e\.demir_stajyer/)).toBeVisible();
    await expect(aliPage.getByText('MAÇ SONA ERDİ — EĞİTİM ANALİZİ (DEBRIEF)')).toBeVisible();
    await assertPixelLayoutHealth(adminPage, '/admin debrief');
    await adminPage.screenshot({
      path: path.join(SCREENSHOTS_DIR, '05-debrief.png'),
      fullPage: true,
    });

    // 8. Assert zero console/page/HTTP errors across all 4 browser contexts
    const allErrors = trackers.flatMap((t) => t.errors);
    expect(allErrors, 'Unexpected browser console/page/HTTP errors').toEqual([]);
  } finally {
    await Promise.all([
      adminContext.close(),
      hostContext.close(),
      aliContext.close(),
      zeynepContext.close(),
    ]);
  }
});
