/*
 * Gumroad 出品自動化（実証済み 2026-06-14）。connect.js(withBrowser) 経由で CDP 接続。
 *
 * 前提: Brave を PC プロファイルで起動済み（liberation58 ログイン）:
 *   pwsh -File C:\Users\abesh\tools\browser-auto\brave-debug.ps1 -Profile "PC"
 *
 * サブコマンド:
 *   node gumroad.js verify  <female|male|set>      公開ページをスクショ（$TEMP/gum_<p>_pub.png）
 *   node gumroad.js covers  <product>              ★「Product covers」の旧ゴミを全削除（狭VP）→説明欄先頭がメイン昇格
 *   node gumroad.js desc    <product>              説明欄画像を全削除→config順で再挿入（※bannerも消える。必要時のみ）
 *   node gumroad.js thumb   <product>              正方形サムネを thumbnails/thumb_<p>.png に差替
 *
 * ★最重要の罠（6/14発見）:
 *   Gumroad には Description とは別に「Product covers」アセットがあり、存在すると
 *   それが公開メイン画像になる（説明欄を直してもメインがグレーのまま＝旧launchの残骸）。
 *   Female/Set は covers 0枚（=説明欄がギャラリー）だが Male には旧covers 6枚が残っていた。
 *   → covers を全削除すれば説明欄先頭のカラー画像がメインに昇格する。
 *   covers 削除UIは「狭ビューポート(780px)」でのみ aria-label「Remove cover」が出る。
 */
const path = require('path');
const fs = require('fs');
const HERE = __dirname;
const CFG = JSON.parse(fs.readFileSync(path.join(HERE, 'config.json'), 'utf8'));
const { withBrowser } = require(CFG.connect_js);

const cmd = process.argv[2];
const product = process.argv[3];
if (!cmd || !product || !CFG.gumroad.products[product]) {
  console.error('usage: node gumroad.js <verify|covers|desc|thumb> <female|male|set>');
  process.exit(1);
}
const PID = CFG.gumroad.products[product].id;
// EDIT_URL 環境変数で編集ページを上書きできる（バンドル https://gumroad.com/bundles/<id>/product/edit 用。
// バンドルは products/<id>/edit と別URLだが編集UIは同じ tiptap + Save changes）
const EDIT = process.env.EDIT_URL || (CFG.gumroad.base_edit + PID + '/edit');

// product の表示画像(絶対パス・順序)を解決
function imagePaths(p) {
  const root = CFG.root;
  if (p === 'set') {
    return CFG.set_image_order.map(spec => {
      if (spec.includes(':')) { const [g, f] = spec.split(':'); return path.join(root, CFG[g].previews_dir, f); }
      return path.join(root, spec);
    });
  }
  return CFG[p].preview_order.map(f => path.join(root, CFG[p].previews_dir, f));
}

async function gotoEdit(page, vp) {
  if (vp) { try { await page.setViewportSize(vp); } catch (e) {} }
  await page.goto(EDIT, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
}

async function run() {
  await withBrowser(async ({ getPage }) => {
    const page = await getPage('gumroad');
    page.on('dialog', async d => { await d.accept(); });

    if (cmd === 'verify') {
      await page.goto(CFG.gumroad.products[product].public, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(6000);
      const out = process.env.TEMP + `/gum_${product}_pub.png`;
      await page.screenshot({ path: out, fullPage: true });
      console.log('saved', out);
      return;
    }

    if (cmd === 'covers') {
      await gotoEdit(page, { width: 780, height: 1000 });
      for (let i = 0; i < 12; i++) {
        const cnt = await page.evaluate(() =>
          [...document.querySelectorAll('a.border img')].filter(im => im.naturalWidth > 800).length);
        console.log('iter', i, 'covers', cnt);
        if (cnt === 0) break;
        const btn = page.locator('[aria-label="Remove cover"], button[aria-label="Remove"]').first();
        if (await btn.count() === 0) { console.log('no remove btn'); break; }
        await btn.click({ force: true });
        await page.waitForTimeout(2000);
      }
      await save(page);
      console.log('covers cleared + saved. verify public main image is colored.');
      return;
    }

    if (cmd === 'desc') {
      await gotoEdit(page);
      const ed = page.locator('.tiptap, .ProseMirror').first();
      console.log('text len before', (await ed.innerText()).length);
      for (let i = 0; i < 40; i++) {
        const imgs = page.locator('.tiptap img, .ProseMirror img');
        if (await imgs.count() === 0) break;
        await imgs.first().click(); await page.waitForTimeout(150);
        await page.keyboard.press('Delete'); await page.waitForTimeout(250);
      }
      console.log('text len after delete', (await ed.innerText()).length, '(must be unchanged)');
      // 逆順に prepend すると最終的に config 順(先頭=01)になる
      const files = imagePaths(product).slice().reverse();
      for (const f of files) {
        await ed.click(); await page.keyboard.press('Control+Home'); await page.waitForTimeout(300);
        await page.locator('input[type=file]').nth(0).setInputFiles(f);
        await page.waitForTimeout(6000);
        console.log('inserted', path.basename(f));
      }
      await save(page);
      console.log('desc rebuilt + saved');
      return;
    }

    if (cmd === 'thumb') {
      await gotoEdit(page);
      const thumb = path.join(CFG.root, CFG.thumbnails_dir, `thumb_${product}.png`);
      const ti = page.locator('img[alt="Thumbnail image"]').first();
      if (await ti.count()) {
        const sec = page.locator('section:has(img[alt="Thumbnail image"])').first();
        await sec.locator('button[aria-label="Remove"]').first().click({ force: true });
        await page.waitForTimeout(2500);
      }
      await page.waitForTimeout(1000);
      const imgInputs = page.locator('input[type=file][accept*="png"]');
      const n = await imgInputs.count();
      await imgInputs.nth(n - 1).setInputFiles(thumb);  // 末尾=サムネ用ドロップゾーン input
      await page.waitForTimeout(6000);
      console.log('thumb set, imgs', await page.locator('img[alt="Thumbnail image"]').count());
      await save(page);
      console.log('thumb replaced + saved:', path.basename(thumb));
      return;
    }
  });
}

async function save(page) {
  await page.getByRole('button', { name: 'Save changes', exact: true }).first().click();
  await page.waitForTimeout(8000);
}

run().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
