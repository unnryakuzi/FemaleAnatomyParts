/*
 * audit_dist.js — 配布物に4形式(blend/fbx/glb/obj)が抜けなく入っているかを機械的に検証する。
 * 読み取り専用。削除も保存もアップロードも一切しない。
 *
 *   node scripts/listing/audit_dist.js            # local + booth + gumroad
 *   node scripts/listing/audit_dist.js local      # ローカルの zip だけ（ブラウザ不要）
 *   node scripts/listing/audit_dist.js booth
 *   node scripts/listing/audit_dist.js gumroad
 *
 * 期待値は config.json の <model>.zip_dir / zip_prefix から組み立てる。
 * 1つでも欠けていたら exit 1。「たぶん入っている」で済ませないための番人。
 *
 * ★Gumroad の set はバンドル商品（同梱の male / female を配信する）なので、
 *   set 自体はファイルを持たない。構成商品側を見て判定する（2026-08-19 実測）。
 */
const path = require('path');
const fs = require('fs');
const HERE = __dirname;
const CFG = JSON.parse(fs.readFileSync(path.join(HERE, 'config.json'), 'utf8'));

const EXTS = ['blend', 'fbx', 'glb', 'obj'];
const which = (process.argv[2] || 'all').toLowerCase();
let failures = 0;

function expectedFor(group) {
  return EXTS.map(e => `${CFG[group].zip_prefix}_${e}.zip`);
}
function expectedZips(product) {
  return product === 'set'
    ? [...expectedFor('male'), ...expectedFor('female')]
    : expectedFor(product);
}
function report(label, expected, found) {
  const missing = expected.filter(n => !found.includes(n));
  const extra = found.filter(n => /Anatomy_v/.test(n) && !expected.includes(n));
  const ok = missing.length === 0;
  console.log(`  ${ok ? 'OK  ' : 'NG  '} ${label}  (${expected.length - missing.length}/${expected.length})`);
  if (missing.length) console.log('        欠落:', missing.join(', '));
  if (extra.length) console.log('        旧版が残存:', extra.join(', '));
  if (!ok) failures++;
  return ok;
}

// ── ローカル ─────────────────────────────────────────────
function auditLocal() {
  console.log('\n===== ローカル（配布zip） =====');
  for (const g of ['male', 'female']) {
    const dir = path.join(CFG.root, CFG[g].zip_dir);
    const found = fs.existsSync(dir) ? fs.readdirSync(dir) : [];
    const ok = report(`${g}  ${CFG[g].zip_dir}`, expectedFor(g), found);
    if (!ok) continue;
    // zip の中身に models/<stem>.<ext> があるか（拡張子違いの取り違え防止）
    for (const e of EXTS) {
      const zp = path.join(dir, `${CFG[g].zip_prefix}_${e}.zip`);
      const buf = fs.readFileSync(zp);
      const needle = Buffer.from(`models/${CFG[g].zip_prefix}.${e}`);
      if (buf.indexOf(needle) === -1) {
        console.log(`        NG: ${path.basename(zp)} に models/${CFG[g].zip_prefix}.${e} が無い`);
        failures++;
      }
    }
  }
}

// ── マーケットプレイス ───────────────────────────────────
async function auditBooth() {
  const { withBrowser } = require(CFG.connect_js);
  console.log('\n===== BOOTH =====');
  await withBrowser(async ({ getPage }) => {
    const page = await getPage('audit_booth');
    page.on('dialog', async d => { try { await d.accept(); } catch (e) {} });
    for (const product of ['male', 'female', 'set']) {
      const PID = CFG.booth.products[product].id;
      await page.goto(CFG.booth.base_edit + PID + '/edit', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(5000);
      const info = await page.evaluate(() => ({
        files: [...new Set([...document.querySelectorAll('a')]
          .filter(a => /\.zip/.test(a.textContent || '')).map(a => a.textContent.trim()))],
        unchecked: [...document.querySelectorAll('input[type=checkbox]')]
          .filter(c => /\.zip/.test((c.closest('label') || c.parentElement || {}).textContent || '') && !c.checked)
          .map(c => ((c.closest('label') || c.parentElement).textContent || '').trim().slice(0, 60)),
      }));
      report(`${product} (${PID})`, expectedZips(product), info.files);
      if (info.unchecked.length) {
        console.log('        NG: 購入者に提供されないチェックOFF:', info.unchecked.join(', '));
        failures++;
      }
    }
  });
}

async function auditGumroad() {
  const { withBrowser } = require(CFG.connect_js);
  console.log('\n===== Gumroad =====');
  await withBrowser(async ({ getPage }) => {
    const page = await getPage('audit_gumroad');
    page.on('dialog', async d => { try { await d.dismiss(); } catch (e) {} });
    for (const product of ['male', 'female']) {
      const PID = CFG.gumroad.products[product].id;
      await page.goto(CFG.gumroad.base_edit + PID + '/edit/content', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(7000);
      // ★ファイルは「フォルダ」に畳まれていることがある（女性は
      //   "Female Anatomy Model — all formats (v1.67.0 colored)" の中）。
      //   畳まれたままだと innerText に出ず 0/4 と誤判定するので必ず展開する。
      //   treeitem の div に対する DOM の .click() では開かない。Playwright の実クリックが要る。
      for (let i = 0; i < 10; i++) {
        const folders = page.locator('[role=treeitem][aria-expanded="false"]');
        if (!(await folders.count())) break;
        try { await folders.first().click({ timeout: 8000 }); } catch (e) { break; }
        await page.waitForTimeout(2500);
      }
      // Gumroad は拡張子なしで表示される → .zip を補って突き合わせる
      const names = await page.evaluate(() =>
        [...new Set((document.body.innerText.match(/(?:Male|Female)Anatomy_[A-Za-z0-9_.\-]+/g) || []))]);
      report(`${product} (${PID})`, expectedZips(product), names.map(n => n + '.zip'));
    }
    console.log('  --  set: バンドル商品（同梱の male / female を配信）。上2件が OK なら set も最新。');
  });
}

(async () => {
  console.log('期待バージョン: male=' + CFG.male.zip_prefix + ' / female=' + CFG.female.zip_prefix);
  if (which === 'all' || which === 'local') auditLocal();
  if (which === 'all' || which === 'booth') await auditBooth();
  if (which === 'all' || which === 'gumroad') await auditGumroad();
  console.log(failures === 0
    ? '\n==> すべて4形式そろっています。'
    : `\n==> 問題 ${failures} 件。上の NG を解消してください。`);
  process.exit(failures === 0 ? 0 : 1);
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
