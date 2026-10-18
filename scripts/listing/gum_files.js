/*
 * Gumroad の Content タブの zip を、新しい版の zip に差し替える
 *   node scripts/listing/gum_files.js <female|male> <files|verify>
 *   files : 今の zip の行を画面上で消し、新しい zip を1本ずつ上げて Save changes（保存するまで公開中の商品は旧 zip のまま）
 *   verify: 上がっている zip の大きさが手元の新しい zip と同じかを確かめる（署名付き URL は出力しない）
 *   RESUME=1: 途中で止まったとき。今ある行（新しい zip の名前）は残し、足りない分だけ上げる
 * 2026-10-18 女性 v1.68.0 で作成。手順の元は C:\Users\abesh\Documents\Blender\tier_zips_2026-10\gum_tier.js
 * （版 Personal / Business は中身が共通。セットのバンドルは単体の商品を参照するので差し替え不要）
 */
const fs = require('fs'), path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const [key, step] = process.argv.slice(2);
const FMT = ['blend', 'fbx', 'glb', 'obj'];
const P = {
  female: { id: 'zdlbhd', dir: '配布zip_v1.68.0', stem: 'FemaleAnatomy_v1.68.0', old: /^FemaleAnatomy_v/ },
  male: { id: 'hgbvor', dir: '配布zip_Man_v1.2.1', stem: 'MaleAnatomy_v1.2.1', old: /^MaleAnatomy_v/ },
}[key];
if (!P) throw new Error('key: female | male');
const ZIPDIR = path.join(ROOT, P.dir);
const ZIPS = FMT.map(f => `${P.stem}_${f}.zip`);
const LOGD = path.join(ROOT, 'scripts/listing/gum_log'); fs.mkdirSync(LOGD, { recursive: true });
const EDIT = `https://gumroad.com/products/${P.id}/edit`;
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, key + '.log'), new Date().toISOString() + ' ' + step + ' ' + s + '\n'); };

async function save(page) {
  const btn = page.getByRole('button', { name: /^(Save changes|Save and continue)$/ }).first();
  for (let t = 0; t < 7200 && await btn.isDisabled(); t += 5) await page.waitForTimeout(5000);   // アップロード中は押せない
  await btn.click(); await page.waitForTimeout(8000);
  const ok = await page.evaluate(() => /Changes saved/i.test(document.body.innerText));
  log('saved', ok ? 'Changes saved!' : '(no message)');
  // 保存のあとに購入者への通知を勧める画面が出たら、ここでは送らない（告知は Emails から決めた文面で送る）
  const dlg = await page.evaluate(() => [...document.querySelectorAll('[role=dialog]')].filter(d => d.getBoundingClientRect().width > 0).map(d => d.innerText.slice(0, 300)));
  if (dlg.length) log('dialog after save', JSON.stringify(dlg));
  return ok;
}

withBrowser(async ({ context, getPage }) => {
  const page = await getPage('gumroad.com'); try { await page.bringToFront(); } catch (e) { }
  page.on('dialog', d => d.accept().catch(() => { }));
  if (step === 'files') {
    for (const z of ZIPS) if (!fs.existsSync(path.join(ZIPDIR, z))) throw new Error('zip が無い: ' + z);
    await page.goto(EDIT + '/content', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(8000);
    const rowNames = () => page.evaluate(() => [...document.querySelectorAll('.node-fileEmbed')].map(e => e.innerText.split('\n')[0].trim()));
    const want = ZIPS.map(z => z.replace(/\.zip$/, '')).sort();
    const cur = await rowNames(); log('rows before', JSON.stringify(cur));
    const resume = process.env.RESUME === '1';
    if (!cur.length || !cur.every(n => P.old.test(n))) throw new Error('今のファイルが想定と違う（手で確かめる）: ' + JSON.stringify(cur));
    if (resume && !cur.every(n => want.includes(n))) throw new Error('RESUME なのに想定外の行がある');
    const toUpload = resume ? ZIPS.filter(z => !cur.includes(z.replace(/\.zip$/, ''))) : ZIPS;
    // 旧 zip を画面上で消す（保存するまで公開中の商品には効かない）
    for (let k = 0; k < 12 && !resume && (await rowNames()).length; k++) {
      const row = page.locator('.node-fileEmbed').first(); await row.scrollIntoViewIfNeeded(); await row.hover(); await page.waitForTimeout(600);
      await row.locator('button[aria-label="Actions"]').first().click({ force: true }); await page.waitForTimeout(1200);
      const del = page.getByRole('menuitem', { name: 'Delete', exact: true }).first();
      if (await del.count()) await del.click(); else await page.getByText('Delete', { exact: true }).last().click();
      await page.waitForTimeout(1500);
    }
    const left = await rowNames(); log('rows after delete', JSON.stringify(left));
    if (!resume && left.length) throw new Error('消し切れない（保存していない）');
    const client = await context.newCDPSession(page); await client.send('DOM.enable');
    const findTarget = async () => {   // 1つ上げると input が作り直されることがあるので、毎回取り直す（accept の無い input が Content 用）
      const doc = await client.send('DOM.getDocument', { depth: -1 });
      const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
      let target = null;
      for (const nid of q.nodeIds) { const a = await client.send('DOM.getAttributes', { nodeId: nid }); const i = a.attributes.indexOf('accept'); if (!(i >= 0 ? a.attributes[i + 1] : '')) target = nid; }
      if (!target) throw new Error('Content タブの input[type=file] が無い');
      return target;
    };
    // 同じ input に続けて渡すと最初の1つしか残らない（2026-10-14）。行が出て、上げ終わってから次を渡す
    for (const z of toUpload) {
      await client.send('DOM.setFileInputFiles', { files: [path.join(ZIPDIR, z).replace(/\\/g, '/')], nodeId: await findTarget() });
      const n = z.replace(/\.zip$/, ''); let seen = false;
      for (let t = 0; t < 60 && !(seen = (await rowNames()).includes(n)); t++) await page.waitForTimeout(2000);
      log('upload started', z, seen ? 'row shown' : 'ROW NOT SHOWN');
      if (!seen) throw new Error('行が出ない（保存しない）: ' + z);
      const btn = page.getByRole('button', { name: 'Save changes', exact: true }).first();
      await page.waitForTimeout(3000);
      for (let t = 0; t < 7200 && await btn.isDisabled(); t += 5) await page.waitForTimeout(5000);
      log('upload finished', z);
    }
    const rb = (await rowNames()).sort(); log('rows before save', JSON.stringify(rb));
    if (JSON.stringify(rb) !== JSON.stringify(want)) throw new Error('保存前の行が想定と違う（保存していない）');
    await save(page);
    await page.goto(EDIT + '/content', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(8000);
    const names = (await rowNames()).sort(); log('rows after reload', JSON.stringify(names));
    if (JSON.stringify(names) !== JSON.stringify(want)) throw new Error('保存後のファイルが想定と違う');
  } else if (step === 'verify') {
    await page.goto(EDIT + '/content', { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(8000);
    const links = await page.evaluate(() => [...document.querySelectorAll('.node-fileEmbed')].map(e => [e.innerText.split('\n')[0].trim(), (e.querySelector('a[href*="product_files"]') || {}).href]));
    let bad = 0;
    for (const [name, href] of links) {
      const r1 = await context.request.get(href, { maxRedirects: 0 });
      const loc = r1.headers()['location'];
      const r2 = loc ? await context.request.head(loc) : null;
      const size = r2 ? Number(r2.headers()['content-length']) : NaN;
      const lp = path.join(ZIPDIR, name + '.zip');
      const local = fs.existsSync(lp) ? fs.statSync(lp).size : -1;
      log('verify', name, 'gumroad', size, 'local', local, size === local ? 'SAME' : 'DIFF');
      if (size !== local) bad++;
    }
    if (bad || links.length !== ZIPS.length) throw new Error('大きさが合わない／本数が違う');
    log('verify OK');
  } else throw new Error('step: files | verify');
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, key + '.log'), 'ERROR ' + step + ' ' + e.message + '\n'); process.exit(1); });
