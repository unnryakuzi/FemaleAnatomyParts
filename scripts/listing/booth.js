/*
 * BOOTH 出品自動化（実証済み 2026-06-14）。connect.js(withBrowser) 経由で CDP 接続。
 *
 * 前提: Brave を PC プロファイルで起動済み（kabe-tech ログイン）:
 *   pwsh -File C:\Users\abesh\tools\browser-auto\brave-debug.ps1 -Profile "PC"
 *
 * サブコマンド（個別実行 or all）:
 *   node booth.js title  <female|male|set>   商品名に【カラー版】を前置（React value setter）
 *   node booth.js images <product>           商品画像を全削除→config順で一括追加（1番目=一覧サムネ）
 *   node booth.js files  <product>           作品ファイル: 旧zip削除→新zipアップ（★容量10GB上限→削除を先に）
 *   node booth.js save   <product>           「公開で保存する」（R-18維持）
 *   node booth.js all    <product>           title→images→files→save を順に
 *   node booth.js verify <product>           公開ページをスクショ
 *
 * ★BOOTH の肝:
 *   - 画像/ファイルとも D&D ドロップゾーンは「クリックで一時 input[type=file] 生成→filechooser 発火」。
 *     page.on('filechooser') で OS ダイアログ抑止 → 生CDP DOM.setFileInputFiles(絶対パス) で
 *     50MB 制限なく一括アップ。完了は <a>.zip がリストに出るまでポーリング。
 *   - 画像は 0枚だとドロップゾーン、1枚以上だと「画像を追加」セル。全削除→正順追加が確実。
 *   - 「削除」は別カラムの <span>削除</span>（行リンクと非親子）。行リンクと中心Yの最近傍で対応付け、
 *     対象版のみ座標クリック（confirm accept）。リフローするので毎回再計測し下(大Y)から。
 *   - 保存後 confirm/公開ダイアログは accept。R-18 は触らない。
 */
const path = require('path');
const fs = require('fs');
const HERE = __dirname;
const CFG = JSON.parse(fs.readFileSync(path.join(HERE, 'config.json'), 'utf8'));
const { withBrowser } = require(CFG.connect_js);

const cmd = process.argv[2];
const product = process.argv[3];
if (!cmd || !product || !CFG.booth.products[product]) {
  console.error('usage: node booth.js <title|images|files|save|all|verify> <female|male|set>');
  process.exit(1);
}
const PID = CFG.booth.products[product].id;
const EDIT = CFG.booth.base_edit + PID + '/edit';

function fwd(p) { return p.replace(/\\/g, '/'); }

function imagePaths(p) {
  const root = CFG.root;
  if (p === 'set') return CFG.set_image_order.map(spec => {
    if (spec.includes(':')) { const [g, f] = spec.split(':'); return fwd(path.join(root, CFG[g].previews_dir, f)); }
    return fwd(path.join(root, spec));
  });
  return CFG[p].preview_order.map(f => fwd(path.join(root, CFG[p].previews_dir, f)));
}

// product の作品ファイル(zip)絶対パスと、削除すべき旧版判定
function zipSpec(p) {
  const root = CFG.root;
  const mk = g => CFG[g].preview_order ? ['blend', 'fbx', 'glb', 'obj'].map(ext =>
    fwd(path.join(root, CFG[g].zip_dir, `${CFG[g].zip_prefix}_${ext}.zip`))) : [];
  if (p === 'set') return [...mk('male'), ...mk('female')];
  return mk(p);
}

async function gotoEdit(page) {
  await page.goto(EDIT, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
}

async function setTitle(page) {
  const cur = await page.evaluate(() => { const i = [...document.querySelectorAll('input')].find(x => /解剖|Anatomy|セット/.test(x.value || '')); return i ? i.value : null; });
  if (cur && !cur.includes('カラー版')) {
    const nv = '【カラー版】' + cur;
    await page.evaluate(v => { const i = [...document.querySelectorAll('input')].find(x => /解剖|Anatomy|セット/.test(x.value || '')); const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(i, v); i.dispatchEvent(new Event('input', { bubbles: true })); i.dispatchEvent(new Event('change', { bubbles: true })); }, nv);
    console.log('title ->', nv);
  } else console.log('title already has カラー版 or not found:', cur);
}

const COUNT_IMGS = () => [...document.querySelectorAll('*')].filter(e => { const s = e.getAttribute('style') || ''; return /background-image/.test(s) && /(booth|pximg|amazonaws|item)/.test(s); }).filter(c => c.getBoundingClientRect().width > 50).length;

async function deleteAllImages(page) {
  for (let it = 0; it < 30; it++) {
    const cells = await page.evaluate(() => {
      const cs = [...document.querySelectorAll('*')].filter(e => { const s = e.getAttribute('style') || ''; return /background-image/.test(s) && /(booth|pximg|amazonaws|item)/.test(s); });
      return cs.map(c => { const r = c.getBoundingClientRect(); const ic = c.querySelector('i.icon-cancel,[class*=cancel]') || c.parentElement?.querySelector('i.icon-cancel,[class*=cancel]'); let d = null; if (ic) { const b = ic.getBoundingClientRect(); d = { x: Math.round(b.x + b.width / 2), y: Math.round(b.y + b.height / 2) }; } return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), d }; }).filter(c => c.w > 50 && c.d);
    });
    if (cells.length === 0) break;
    const last = cells[cells.length - 1];
    await page.mouse.move(last.x + last.w / 2, last.y + last.h / 2); await page.waitForTimeout(300);
    await page.mouse.click(last.d.x, last.d.y); await page.waitForTimeout(1200);
  }
}

// ドロップゾーンをクリック→生成された input に生CDPでファイル投入（50MB制限回避）
async function dropzoneUpload(context, page, dzText, files) {
  let dz = page.getByText(dzText, { exact: false }).first();
  let captured = null; page.on('filechooser', fc => { captured = fc; });
  await dz.click(); await page.waitForTimeout(1500);
  const client = await context.newCDPSession(page); await client.send('DOM.enable');
  const doc = await client.send('DOM.getDocument', { depth: -1 });
  const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
  if (q.nodeIds.length) { await client.send('DOM.setFileInputFiles', { files, nodeId: q.nodeIds[q.nodeIds.length - 1] }); return true; }
  if (captured) { try { await captured.setFiles(files); return true; } catch (e) { console.log('fc.setFiles err', e.message); } }
  return false;
}

async function save(page) {
  const close = page.getByRole('button', { name: '閉じる', exact: true }).first();
  if (await close.count()) { await close.click(); await page.waitForTimeout(2000); }
  await page.getByRole('button', { name: '公開で保存する', exact: true }).first().click();
  await page.waitForTimeout(9000);
  const msg = await page.evaluate(() => { const e = [...document.querySelectorAll('*')].find(x => /保存しました|公開しました/.test(x.textContent || '') && (x.textContent || '').length < 30); return e ? e.textContent.trim() : '(no msg)'; });
  console.log('save:', msg);
}

async function doImages(context, page) {
  await deleteAllImages(page);
  console.log('images after delete', await page.evaluate(COUNT_IMGS));
  const ok = await dropzoneUpload(context, page, '画像ファイルをドラッグ', imagePaths(product));
  if (!ok) { // 画像が残っている等で「画像を追加」セルの場合
    const add = page.getByText('画像を追加', { exact: false }).first();
    if (await add.count()) { await add.click(); await page.waitForTimeout(800); const fis = await page.$$('input[type=file]'); await fis[fis.length - 1].setInputFiles(imagePaths(product)); }
  }
  await page.waitForTimeout(10000);
  console.log('image cells now', await page.evaluate(COUNT_IMGS));
}

async function doFiles(context, page) {
  const change = page.getByText('変更する', { exact: false }).first();
  if (await change.count()) { await change.scrollIntoViewIfNeeded(); await change.click(); await page.waitForTimeout(3000); }
  // 旧版判定: 現行 zip_prefix と一致しない .zip を削除（容量10GB対策で先に削除）
  const keep = new Set(zipSpec(product).map(f => path.basename(f)));
  for (let it = 0; it < 20; it++) {
    const map = await page.evaluate(() => {
      const dels = [...document.querySelectorAll('*')].filter(e => { const t = (e.textContent || '').trim(); return t === '削除' && e.querySelectorAll('*').length <= 1; }).map(e => { const r = e.getBoundingClientRect(); return { y: r.y + r.height / 2, x: r.x + r.width / 2 }; });
      const files = [...document.querySelectorAll('a')].filter(a => /\.zip/.test(a.textContent || '')).map(a => { const r = a.getBoundingClientRect(); return { y: r.y + r.height / 2, name: a.textContent.trim() }; });
      return dels.map(d => { let best = null, bd = 1e9; for (const f of files) { const dd = Math.abs(f.y - d.y); if (dd < bd) { bd = dd; best = f; } } return { x: Math.round(d.x), y: Math.round(d.y), name: best ? best.name : '?' }; });
    });
    const olds = map.filter(m => m.name !== '?' && !keep.has(m.name)).sort((a, b) => b.y - a.y);
    if (olds.length === 0) break;
    console.log('delete old', olds[0].name);
    await page.mouse.click(olds[0].x, olds[0].y); await page.waitForTimeout(1800);
  }
  // 既にある現行版はスキップ、無いものだけアップ
  const present = await page.evaluate(() => new Set([...document.querySelectorAll('a')].filter(a => /\.zip/.test(a.textContent || '')).map(a => a.textContent.trim())));
  const need = zipSpec(product).filter(f => !present.has(path.basename(f)));
  if (need.length) {
    console.log('uploading', need.map(f => path.basename(f)));
    await dropzoneUpload(context, page, 'ファイルをドラッグ', need);
    const wantNames = zipSpec(product).map(f => path.basename(f));
    for (let i = 0; i < 40; i++) {
      const have = await page.evaluate(() => [...document.querySelectorAll('a')].filter(a => /\.zip/.test(a.textContent || '')).map(a => a.textContent.trim()));
      const done = wantNames.every(n => have.includes(n));
      console.log('upload poll', i, 'have', new Set(have).size);
      if (done) { console.log('UPLOAD COMPLETE'); break; }
      await page.waitForTimeout(10000);
    }
  } else console.log('all current zips already present');
  // 全 zip チェックON
  await page.evaluate(() => { document.querySelectorAll('input[type=checkbox]').forEach(c => { const lbl = (c.closest('label')?.textContent || c.parentElement?.textContent || ''); if (/\.zip/.test(lbl) && !c.checked) c.click(); }); });
}

async function run() {
  await withBrowser(async ({ context, getPage }) => {
    const page = await getPage('booth');
    page.on('dialog', async d => { await d.accept(); });
    if (cmd === 'verify') {
      await page.goto(CFG.booth.base_public + PID, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(6000);
      const out = process.env.TEMP + `/booth_${product}_pub.png`;
      await page.screenshot({ path: out }); console.log('saved', out); return;
    }
    await gotoEdit(page);
    if (cmd === 'title') { await setTitle(page); await save(page); }
    else if (cmd === 'images') { await doImages(context, page); await save(page); }
    else if (cmd === 'files') { await doFiles(context, page); await save(page); }
    else if (cmd === 'all') { await setTitle(page); await doImages(context, page); await doFiles(context, page); await save(page); }
  });
}

run().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
