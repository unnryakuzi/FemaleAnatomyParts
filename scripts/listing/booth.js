/*
 * BOOTH 出品自動化（実証済み 2026-06-14）。connect.js(withBrowser) 経由で CDP 接続。
 *
 * 前提: Brave を PC プロファイルで起動済み（kabe-tech ログイン）:
 *   pwsh -File C:\Users\abesh\tools\browser-auto\brave-debug.ps1 -Profile "PC"
 *
 * サブコマンド（個別実行 or all）:
 *   node booth.js title  <female|male|set>   商品名に【カラー版】を前置（React value setter）
 *   node booth.js desc   <product>           config.booth_desc_notes の注記を説明文へ冪等に挿入
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
  console.error('usage: node booth.js <title|desc|images|files|save|all|verify> <female|male|set>');
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
  // ★BOOTH掲載分だけ無彩色マネキン調を使う（previews_dir_booth）。年齢制限判定は商品ページの
  //   画像を見ているため、肌色のécorché は「裸の人体」と読まれてR-18固定にされる（2026-08-10）。
  //   配布物・Gumroad はカラーのままなので previews_dir は触らない。
  //   男性は 07_skin（肌色の全裸レンダー）を落とすため掲載順も別に持つ（preview_order_booth）。
  const dir = CFG[p].previews_dir_booth || CFG[p].previews_dir;
  const order = CFG[p].preview_order_booth || CFG[p].preview_order;
  const list = order.map(f => fwd(path.join(root, dir, f)));
  // ★BOOTHの一覧サムネは1枚目画像の正方形中央クロップ → 縦長(1000x1400)だと頭と足が切れる。
  //   正方形の全身サムネを先頭に置いて回避する（2026-07-26）。
  if (CFG.booth_thumb_first) list.unshift(fwd(path.join(root, CFG.thumbnails_dir, CFG[p].booth_thumb || `thumb_${p}.png`)));
  return list;
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

// 説明文へ注記を1回だけ差し込む（冪等）。config.json の booth_desc_notes[product] が定義。
// anchor の直後に note を挿入する。marker が既にあれば何もしない。
async function setDesc(page) {
  const spec = (CFG.booth_desc_notes || {})[product];
  if (!spec) { console.log('desc: no booth_desc_notes for', product); return false; }
  const res = await page.evaluate(({ anchor, note, marker }) => {
    const ta = document.querySelectorAll('textarea')[0];
    if (!ta) return { status: 'textarea-not-found' };
    const cur = ta.value || '';
    if (cur.includes(marker)) return { status: 'already', len: cur.length };
    const i = cur.indexOf(anchor);
    if (i < 0) return { status: 'anchor-not-found', len: cur.length };
    const at = i + anchor.length;
    const nv = cur.slice(0, at) + note + cur.slice(at);
    const set = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    set.call(ta, nv);
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    ta.dispatchEvent(new Event('change', { bubbles: true }));
    return { status: 'inserted', len: nv.length };
  }, spec);
  console.log('desc:', JSON.stringify(res));
  return res.status === 'inserted';
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
  let captured = null; page.on('filechooser', fc => { captured = fc; });
  if (typeof dzText === 'string') {
    await page.getByText(dzText, { exact: false }).first().click();
  } else {
    await page.mouse.click(dzText.x, dzText.y); // {x,y} 指定
  }
  await page.waitForTimeout(1500);
  const client = await context.newCDPSession(page); await client.send('DOM.enable');
  const doc = await client.send('DOM.getDocument', { depth: -1 });
  const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
  if (q.nodeIds.length) { await client.send('DOM.setFileInputFiles', { files, nodeId: q.nodeIds[q.nodeIds.length - 1] }); return true; }
  if (captured) { try { await captured.setFiles(files); return true; } catch (e) { console.log('fc.setFiles err', e.message); } }
  return false;
}

// 「商品画像」〜「作品ファイル」見出しの間にあるドロップゾーン/「画像を追加」セルの座標を返す。
// 文言は BOOTH 側で変わる（0枚時=ドロップゾーン / 1枚以上=画像を追加）ので、
// テキスト一致ではなく「セクション内にある ドラッグ|追加 の要素」で拾う。作品ファイル側の
// ドロップゾーンに誤爆すると PNG が販売ファイルとして上がるため、範囲限定は必須。
async function imageZonePoint(page) {
  const locate = () => page.evaluate(() => {
    const leaves = [...document.querySelectorAll('*')].filter(e => e.children.length === 0);
    const topOf = re => { const e = leaves.find(x => re.test((x.textContent || '').trim())); return e ? e.getBoundingClientRect().top + window.scrollY : null; };
    const secTop = topOf(/^商品画像$/), secBottom = topOf(/^作品ファイル$/);
    const c = leaves
      .filter(e => /ドラッグ|画像を追加/.test(e.textContent || ''))
      .map(e => { const r = e.getBoundingClientRect(); return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2), absTop: r.top + window.scrollY, text: (e.textContent || '').trim().slice(0, 30) }; })
      .filter(z => (secTop === null || z.absTop > secTop) && (secBottom === null || z.absTop < secBottom))[0];
    return c ? { ...c, secTop, secBottom } : null;
  });
  let z = await locate();
  if (!z) return null;
  await page.evaluate(t => window.scrollTo(0, Math.max(t - 200, 0)), z.absTop);
  await page.waitForTimeout(800);
  return await locate();
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
  const zone = await imageZonePoint(page);
  if (!zone) throw new Error('商品画像のドロップゾーンが見つからない（BOOTHのUI変更を疑う）');
  console.log('image zone:', zone.text, zone.x, zone.y);
  const ok = await dropzoneUpload(context, page, { x: zone.x, y: zone.y }, imagePaths(product));
  if (!ok) throw new Error('input[type=file] が生成されなかった');
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
      // fullPage: 説明文まで写す（メイン画像だけ見て誤判定した事故があるため）
      await page.screenshot({ path: out, fullPage: process.env.FULLPAGE === '1' }); console.log('saved', out); return;
    }
    await gotoEdit(page);
    if (cmd === 'title') { await setTitle(page); await save(page); }
    else if (cmd === 'desc') { if (await setDesc(page)) await save(page); }
    else if (cmd === 'images') { await doImages(context, page); await save(page); }
    else if (cmd === 'files') { await doFiles(context, page); await save(page); }
    else if (cmd === 'all') { await setTitle(page); await doImages(context, page); await doFiles(context, page); await save(page); }
  });
}

run().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
