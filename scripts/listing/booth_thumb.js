// BOOTH の1枚目（一覧サムネ）だけを差し替える。画像の変更は保存しなくても即時反映される（2026-10-31 の画面）ので、
// 消してから入れる順にはしない: 新しい画像を末尾に足す → キーボードで先頭へ → 先頭に来たのを確かめてから旧1枚目を削除
// node scripts/listing/booth_thumb.js <female|male|set>   （2026-10-31 案C で3商品に実行。thumbnails/thumb_<p>_band_ja.png を1枚目にする）
const path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const IDS = { female: 8481858, male: 8496247, set: 8496725 };
const prod = process.argv[2]; if (!IDS[prod]) throw new Error('product?');
const FILE = path.resolve(`C:/Users/abesh/Documents/Blender/MaleAnatomy/thumbnails/thumb_${prod}_band_ja.png`);
const key = u => (u.match(/\/([0-9a-f-]{36})_base/) || [])[1];
withBrowser(async ({ context }) => {
  const p = await context.newPage(); await p.setViewportSize({ width: 1400, height: 1000 }).catch(() => {});
  const sec = p.locator('div.grid:has(> label:text-is("商品画像"))');
  const cells = sec.locator('li [role=button][aria-roledescription=sortable]');
  const urls = async () => (await cells.evaluateAll(es => es.map(e => getComputedStyle(e).backgroundImage))).map(key);
  try {
    await p.goto(`https://manage.booth.pm/items/${IDS[prod]}/edit`, { waitUntil: 'domcontentloaded', timeout: 60000 }); await p.waitForTimeout(6000);
    const before = await urls(); const n = before.length;
    console.log('before', n, before.map(s => s.slice(0, 8)).join(' '));
    if (n < 2 || before.some(k => !k)) throw new Error('画像の読み取りがおかしい');
    // 1) 末尾に追加
    const fcP = p.waitForEvent('filechooser', { timeout: 10000 });
    const add = sec.getByText('画像を追加').first(); await add.scrollIntoViewIfNeeded(); await add.click();
    await (await fcP).setFiles(FILE);
    let now = [];
    for (let i = 0; i < 30; i++) { await p.waitForTimeout(2000); now = await urls(); if (now.length === n + 1 && now.every(Boolean)) break; }
    const added = now.filter(k => !before.includes(k));
    console.log('after add', now.length, 'new', added);
    if (now.length !== n + 1 || added.length !== 1 || now[n] !== added[0]) throw new Error('追加が想定と違う（削除はしない）');
    const NEW = added[0];
    // 2) キーボードで先頭へ（dnd-kit: スペースで持ち上げ→矢印→スペースで置く）
    const c = cells.nth(n); await c.scrollIntoViewIfNeeded(); await c.focus();
    await p.keyboard.press('Space'); await p.waitForTimeout(500);
    for (let i = 0; i < n + 2; i++) { await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(250); }
    for (let i = 0; i < 3; i++) { await p.keyboard.press('ArrowUp'); await p.waitForTimeout(250); }
    await p.keyboard.press('Space'); await p.waitForTimeout(4000);
    now = await urls();
    console.log('after move', now.map(s => s.slice(0, 8)).join(' '));
    if (now[0] !== NEW || now[1] !== before[0]) throw new Error('先頭へ移せていない（削除はしない）');
    // 読み直しても順番が残っているか（即時反映の確認）
    await p.reload({ waitUntil: 'domcontentloaded' }); await p.waitForTimeout(6000);
    now = await urls(); console.log('after reload', now.map(s => s.slice(0, 8)).join(' '));
    if (now[0] !== NEW || now[1] !== before[0]) throw new Error('読み直すと順番が戻っている（削除はしない）');
    // 3) 旧1枚目（いま2番目）を削除
    const old = cells.nth(1); await old.scrollIntoViewIfNeeded(); await old.hover(); await p.waitForTimeout(300);
    await old.locator('button').click(); await p.waitForTimeout(1000);
    await p.locator('button:visible', { hasText: /^OK$/ }).first().click(); await p.waitForTimeout(4000);
    await p.reload({ waitUntil: 'domcontentloaded' }); await p.waitForTimeout(6000);
    now = await urls(); console.log('final', now.length, now.map(s => s.slice(0, 8)).join(' '));
    const expect = [NEW, ...before.slice(1)];
    console.log(JSON.stringify(now) === JSON.stringify(expect) ? 'OK: 1枚目だけ差し替わった' : 'MISMATCH: ' + JSON.stringify({ expect, now }));
  } finally { await p.close(); }
});
