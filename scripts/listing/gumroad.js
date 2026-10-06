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
 *   node gumroad.js files   <product>              Contentタブの配布zipを config の版へ差替
 *
 * ★files の順序（2026-08-19 BOOTHでの事故を踏まえた設計）:
 *   「先にアップロード → 全部揃ったのを確認 → 旧版を削除 → Save changes」。
 *   先に消すと、アップロード側で落ちたときに商品のファイルが 0 本になる。
 *   BOOTH は総容量 10GB 上限のため削除が先だが、Gumroad にその制約は無い。
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
  console.error('usage: node gumroad.js <verify|covers|desc|thumb|files> <female|male|set>');
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

// product の配布zip（絶対パス）。booth.js と同じ規則。
function zipSpec(p) {
  const root = CFG.root;
  // 骨格SKUのように1商品=1zipのものは config の zips（絶対パス可）をそのまま使う
  if (CFG[p] && CFG[p].zips) return CFG[p].zips.map(z => (path.isAbsolute(z) ? z : path.join(root, z)));
  const mk = g => CFG[g].preview_order ? ['blend', 'fbx', 'glb', 'obj'].map(ext =>
    path.join(root, CFG[g].zip_dir, `${CFG[g].zip_prefix}_${ext}.zip`)) : [];
  if (p === 'set') return [...mk('male'), ...mk('female')];
  return mk(p);
}

// Content タブに出ているファイル名（拡張子なしで表示される: MaleAnatomy_v1.2.0_obj）
async function listFiles(page) {
  return await page.evaluate(() =>
    [...new Set((document.body.innerText.match(/(?:(?:Male|Female)Anatomy|AnatomySkeleton)_[A-Za-z0-9_.\-]+/g) || []))]);
}

async function gotoContent(page) {
  await page.goto(EDIT + '/content', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(7000);
  // ファイルがフォルダに畳まれていると一覧に出ず、旧版を「0本」と誤判定して消し残す
  // （2026-10-07: 女性の v1.67.0 4本がフォルダ内に残った）。実クリックで全部開く。
  try { await page.bringToFront(); } catch (e) { /* ignore */ }
  for (let i = 0; i < 10; i++) {
    const folded = page.locator('[role=treeitem][aria-expanded="false"]');
    if (!(await folded.count())) break;
    await folded.first().click({ timeout: 15000 });
    await page.waitForTimeout(1500);
  }
}

// 行の「Actions」→「Delete」。行はホバーしないとボタンが出ないので座標で当てる。
async function deleteFileByName(page, name) {
  const box = await page.evaluate((nm) => {
    const el = [...document.querySelectorAll('div')]
      .filter(e => (e.textContent || '').includes(nm) && e.querySelectorAll('*').length <= 12).pop();
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
  }, name);
  if (!box) { console.log('  行が見つからない:', name); return false; }
  await page.mouse.move(box.x, box.y);
  await page.waitForTimeout(700);
  const btn = await page.evaluate((y) => {
    const c = [...document.querySelectorAll('button,[role=button]')]
      .filter(e => /Actions/i.test(e.getAttribute('aria-label') || e.textContent || ''))
      .map(e => { const r = e.getBoundingClientRect(); return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2), d: Math.abs(r.y + r.height / 2 - y) }; })
      .sort((a, b) => a.d - b.d)[0];
    return c || null;
  }, box.y);
  if (!btn) { console.log('  Actions が出ない:', name); return false; }
  await page.mouse.click(btn.x, btn.y);
  await page.waitForTimeout(1200);
  const del = page.getByRole('menuitem', { name: 'Delete', exact: true }).first();
  if (await del.count()) await del.click();
  else await page.getByText('Delete', { exact: true }).last().click();
  await page.waitForTimeout(2000);
  return true;
}

async function gotoEdit(page, vp) {
  if (vp) { try { await page.setViewportSize(vp); } catch (e) {} }
  await page.goto(EDIT, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
}

async function run() {
  await withBrowser(async ({ context, getPage }) => {
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

    if (cmd === 'files') {
      // ★Gumroad の set は「バンドル」商品（/products/<id>/edit が /bundles/<key>/product/edit へ
      //   リダイレクトする）。Content タブは同梱商品(Male l/hgbvor + Female l/zdlbhd)を並べるだけで
      //   自前のファイルを持たない＝汎用 input[type=file] が無い。個別商品を更新すれば
      //   バンドルの配布物も自動で新しくなるので、ここでやることは無い（2026-08-19 実測）。
      //   ※BOOTH のセットは実ファイルを8本持つので、そちらは booth.js files set が必要。
      if (product === 'set') {
        console.log('Gumroad の set はバンドル商品です。同梱の male / female を更新すれば');
        console.log('配布物は自動で反映されるため、ここでの操作は不要です。');
        return;
      }
      const want = zipSpec(product);
      const wantNames = want.map(f => path.basename(f, '.zip'));

      // ── 1) アップロード → 保存 → 再読込で確認（削除はそのあと）
      await gotoContent(page);
      console.log('現在:', await listFiles(page));
      console.log('目標:', wantNames);
      const before = await listFiles(page);
      const need = want.filter(f => !before.includes(path.basename(f, '.zip')));
      if (need.length) {
        // ★1本ずつアップして都度保存する。4本まとめて setFileInputFiles すると
        //   Save は有効化されるのに保存後は1本も残らない（2026-08-19 実測）。
        //   1本ずつなら "Changes saved!" が出て再読込後も残ることを確認済み。
        for (const f of need) {
          const name = path.basename(f, '.zip');
          await gotoContent(page);
          console.log('uploading', path.basename(f));
          const client = await context.newCDPSession(page);
          await client.send('DOM.enable');
          const doc = await client.send('DOM.getDocument', { depth: -1 });
          const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
          let target = null;
          for (const id of q.nodeIds) {
            const a = await client.send('DOM.getAttributes', { nodeId: id });
            const idx = a.attributes.indexOf('accept');
            if (!(idx >= 0 ? a.attributes[idx + 1] : '')) target = id;   // accept 無し = 汎用
          }
          if (!target) throw new Error('Content タブの汎用 input[type=file] が見つからない');
          await client.send('DOM.setFileInputFiles', { files: [f], nodeId: target });

          // 行が出るまで待つ（＝クライアント側にアップロードが登録された）
          let listed = false;
          for (let i = 0; i < 180; i++) {
            if ((await listFiles(page)).includes(name)) { listed = true; break; }
            await page.waitForTimeout(5000);
          }
          if (!listed) throw new Error(name + ' がリストに現れない');
          if (!(await save(page))) throw new Error(name + ' の保存ができなかった');

          await gotoContent(page);
          if (!(await listFiles(page)).includes(name)) throw new Error(name + ' が保存されなかった');
          console.log('  保存OK:', name);
        }
      } else console.log('all current zips already present');

      // 再読込して「本当に保存されたか」を確認してから削除に進む
      await gotoContent(page);
      const after = await listFiles(page);
      console.log('保存後:', after);
      const missing = wantNames.filter(n => !after.includes(n));
      if (missing.length) throw new Error('新版が保存されていないため削除を中止: ' + missing.join(','));

      // ── 2) 旧版を削除 → 保存 → 再読込で確認
      const olds = after.filter(n => /Anatomy_v|AnatomySkeleton_/.test(n) && !wantNames.includes(n));
      console.log('削除対象(旧版):', olds);
      if (olds.length) {
        for (const n of olds) { console.log('delete', n); await deleteFileByName(page, n); }
        if (!(await save(page))) throw new Error('削除後の保存ができなかった');
      }

      await gotoContent(page);
      console.log('最終:', await listFiles(page));
      console.log('files 完了 + saved');
      return;
    }
  });
}

// ★Save changes は「アップロード処理中」も「変更なし」も disabled になる。
//   実測(2026-08-19): 442MB 1本で約90秒 disabled のままだった。押せるまで待つ。
async function waitSaveEnabled(page, maxMs) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    const dis = await page.evaluate(() => {
      const b = [...document.querySelectorAll('button')].find(x => /Save changes/i.test(x.textContent || ''));
      return b ? b.disabled : null;
    });
    if (dis === null) throw new Error('Save changes ボタンが見つからない');
    if (dis === false) return true;
    console.log('  Save disabled… 待機', Math.round((Date.now() - t0) / 1000) + 's');
    await page.waitForTimeout(10000);
  }
  return false;
}

async function save(page, maxWaitMs = 1800000) {
  if (!(await waitSaveEnabled(page, maxWaitMs))) {
    console.log('Save changes が有効にならなかった（変更なし or 処理継続中）');
    return false;
  }
  // ★タブが背面だと描画が止まり、Playwright の click は「安定待ち」で固まる（2026-10-07 実測）。
  //   前面化したうえで DOM の click で押す。
  try { await page.bringToFront(); } catch (e) { /* ignore */ }
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find(x => /^\s*Save changes\s*$/i.test(x.textContent || '') && !x.disabled); if (b) b.click(); });
  await page.waitForTimeout(8000);
  return true;
}

run().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
