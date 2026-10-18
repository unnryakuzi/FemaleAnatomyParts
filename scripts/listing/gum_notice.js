/*
 * Gumroad の Emails で、女性モデルとセットの購入者に更新を知らせる（2026-10-18 女性 v1.68.0。ユーザー承認済みの文面）
 *   node scripts/listing/gum_notice.js <preview|send>
 *   preview: 宛先（Customers only＋Bought で3商品）・件名・本文を入れ、宛先の人数を読んでスクショを撮る（保存も送信もしない）
 *   send   : 同じ手順のあと Publish（メールで送る）。送ったあと Published の一覧で確かめる
 */
const fs = require('fs'), path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const LOGD = path.join(ROOT, 'scripts/listing/gum_log'); fs.mkdirSync(LOGD, { recursive: true });
const PRODUCTS = [
  'Female Anatomy Model — Colored Muscles + Skeleton (A-pose, Trilingual Labels)',
  'Male + Female Anatomy Models — Colored, Complete Pair (A-pose, Trilingual Labels)',
  'Male + Female Anatomy Models — Colored, Complete Pair (A-pose, Trilingual Labels) — Busine',   // 法人向けバンドル（候補の先頭一致で選ぶ）
];
const SUBJECT = 'Female Anatomy Model updated to v1.68.0';
const BODY = [
  'The Female Anatomy Model (also included in the Male + Female set) has been updated to v1.68.0. You can download the latest version from your Gumroad Library.',
  '',
  "What's new",
  '- Fixed missing parts: 43 parts that the male model already had were missing from the female model (rectus abdominis, internal oblique, transversus abdominis, rhomboids and more). The model now has 716 parts.',
  '- Fixed the width of the rib cage and the shape of the rectus abdominis, internal oblique, transversus abdominis and pyramidalis.',
  '- Fixed the position of the multifidus.',
  '- Fixed the .blend file opening with overlays turned off.',
  '',
  'Thank you for your purchase.',
  'Kabe-Tech',
];
const step = process.argv[2];
if (!['preview', 'send'].includes(step)) throw new Error('step: preview | send');
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, 'notice.log'), new Date().toISOString() + ' ' + step + ' ' + s + '\n'); };

withBrowser(async ({ context }) => {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1400, height: 1000 }).catch(() => { });
  page.on('dialog', d => d.accept().catch(() => { }));
  try {
    await page.goto('https://gumroad.com/emails/new', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(8000);
    await page.getByLabel('Customers only', { exact: true }).check({ force: true }); await page.waitForTimeout(2000);
    const bought = page.getByLabel('Bought', { exact: true }).first();
    for (const name of PRODUCTS) {
      await bought.click(); await page.waitForTimeout(800);
      const opts = page.locator('[role=option]');
      const texts = await opts.evaluateAll(es => es.map(e => e.textContent.trim()));
      // 先頭一致。同じ名前で版つき（" - Personal license" 等）の候補もあるので、名前ちょうど、なければ先頭一致の1件
      let i = texts.findIndex(t => t === name);
      if (i < 0) { const c = texts.map((t, k) => [t, k]).filter(([t]) => t.startsWith(name)); if (c.length !== 1) throw new Error('候補が1つに決まらない: ' + name + ' / ' + JSON.stringify(c.map(x => x[0]))); i = c[0][1]; }
      await opts.nth(i).click(); await page.waitForTimeout(1200);
      log('bought +', texts[i].slice(0, 90));
    }
    await page.keyboard.press('Escape'); await page.waitForTimeout(800);
    const audience = await page.evaluate(() => (document.body.innerText.match(/Audience\s*\n\s*([\d,]+\s*\/\s*[\d,]+)/) || [])[1]);
    log('audience', audience);
    if (!audience || /^0\s*\//.test(audience)) throw new Error('宛先が0人');
    const chips = await page.evaluate(() => { const b = document.getElementById(document.querySelector('label') && [...document.querySelectorAll('label')].find(l => l.textContent.trim() === 'Bought')?.htmlFor); const box = b ? b.closest('div[class]')?.parentElement : null; return box ? box.innerText.slice(0, 600) : null; });
    log('bought field', JSON.stringify(chips));
    await page.getByPlaceholder('Title').fill(SUBJECT);
    await page.evaluate(lines => {
      const ed = [...document.querySelectorAll('.ProseMirror')].map(e => e.editor).find(Boolean);
      ed.commands.setContent({ type: 'doc', content: lines.map(l => l ? { type: 'paragraph', content: [{ type: 'text', text: l }] } : { type: 'paragraph' }) }, true);
    }, BODY);
    await page.waitForTimeout(1000);
    const got = await page.evaluate(() => { const ed = [...document.querySelectorAll('.ProseMirror')].map(e => e.editor).find(Boolean); return ed.getJSON().content.map(n => (n.content || []).map(c => c.text || '').join('')).join('\n'); });
    if (got !== BODY.join('\n')) throw new Error('本文が一致しない（保存していない）');
    const title = await page.getByPlaceholder('Title').inputValue();
    if (title !== SUBJECT) throw new Error('件名が一致しない');
    const channel = await page.getByLabel('Send email', { exact: true }).isChecked();
    log('subject ok, body ok, send email:', channel);
    if (!channel) throw new Error('「Send email」がオフ');
    await page.screenshot({ path: path.join(LOGD, 'notice_form.png'), fullPage: true });
    if (step === 'preview') { log('preview only（保存も送信もしていない）'); return; }
    // Publish はポップオーバー（「Publish now」か日時を入れて「Schedule」）を開くだけ。「Publish now」を名前で押す（2026-10-18 実測）
    await page.getByRole('button', { name: 'Publish', exact: true }).first().click(); await page.waitForTimeout(2000);
    const pop = page.locator('[role=dialog]').filter({ hasText: 'Publish now' }).last();
    if (!(await pop.count())) throw new Error('Publish のポップオーバーが出ない（送っていない）');
    log('popover', JSON.stringify(await pop.innerText()));
    await pop.getByRole('button', { name: 'Publish now', exact: true }).click(); await page.waitForTimeout(8000);
    const after = await page.evaluate(() => [...document.querySelectorAll('[role=dialog], [role=alertdialog], [role=status], [role=alert]')].filter(d => d.getBoundingClientRect().width > 0).map(d => d.innerText.slice(0, 300)));
    if (after.length) log('after publish', JSON.stringify(after));
    log('after publish url', page.url());
    await page.goto('https://gumroad.com/emails/published', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(8000);
    const row = await page.evaluate(s => (document.body.innerText.split('\n').find(l => l.includes(s)) || null), SUBJECT);
    log('published row', JSON.stringify(row));
    await page.screenshot({ path: path.join(LOGD, 'notice_published.png'), fullPage: true });
    if (!row) throw new Error('Published に出ていない（Drafts／Scheduled を確かめる）');
  } finally { await page.close({ runBeforeUnload: false }).catch(() => { }); }
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, 'notice.log'), 'ERROR ' + step + ' ' + e.message + '\n'); process.exit(1); });
