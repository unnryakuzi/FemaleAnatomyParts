/*
 * BOOTH の作品ファイルを新しい zip に差し替える（バリエーション「個人利用／法人利用」の両方に付ける）
 *   node scripts/listing/booth_files.js <female|male|set> <step>
 *   step: inspect … 2つのファイル欄のチェック状態と容量を読む（保存しない）
 *         upload  … NEW の zip を上げ、1つ目のファイル欄（個人利用）で NEW にチェック → 保存。古い zip は消さない
 *         check   … 2つ目のファイル欄（法人利用）で NEW にチェック → 保存
 *         delete  … OLD に当たる zip を消す → 保存（削除は保存の前に即時に効く）
 *         verify  … 2つの欄とも NEW が全部付いていて、OLD（NEW 以外）が無いことを確かめる
 *   セットは PART=female|male で扱う組を選ぶ（既定 female）
 *   男性の zip は新旧で同じ名前（MaleAnatomy_v1.2.1_*）なので、delete で消してから upload する
 * 2026-10-18 女性 v1.68.0 で作成。手順の元は C:\Users\abesh\Documents\Blender\tier_zips_2026-10\booth_tier.js
 * （BOOTH のバリエーションは作品ファイルを欄ごとにチェックで付ける。上げたファイルは商品内で共通）
 * 前提: Brave をデバッグポート付き・PC プロファイルで起動済み。公開中の商品なので「公開で保存する」で保存する
 */
const path = require('path'), fs = require('fs');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const LOGD = path.join(ROOT, 'scripts/listing/booth_log'); fs.mkdirSync(LOGD, { recursive: true });
const FMT = ['blend', 'fbx', 'glb', 'obj'];
const FEMALE = { dir: '配布zip_v1.68.0', stem: 'FemaleAnatomy_v1.68.0', old: /^FemaleAnatomy_v/ };
const MALE = { dir: '配布zip_Man_v1.2.1', stem: 'MaleAnatomy_v1.2.1', old: /^MaleAnatomy_v/ };
const zips = m => FMT.map(f => `${ROOT}/${m.dir}/${m.stem}_${f}.zip`);
const PART = process.env.PART === 'male' ? MALE : FEMALE;
const ITEMS = {
  female: { id: '8481858', set: FEMALE },
  male: { id: '8496247', set: MALE },
  set: { id: '8496725', set: PART },
};
const [key, step] = process.argv.slice(2);
const it = ITEMS[key]; if (!it) throw new Error('key: female | male | set');
const NEW = zips(it.set), NEWN = NEW.map(f => path.basename(f));
// 消す対象: 同じ組の zip のうち NEW 以外（女性）／同じ組の zip 全部（男性＝新旧同名なので upload の前に流す）
const isOld = n => it.set.old.test(n) && (it.set === MALE || !NEWN.includes(n));
const tag = key + (key === 'set' ? '_' + (it.set === MALE ? 'male' : 'female') : '');
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, key + '.log'), new Date().toISOString() + ' ' + tag + ' ' + step + ' ' + s + '\n'); };
const sleep = (p, ms) => p.waitForTimeout(ms);

async function closeModals(page) {
  for (const loc of [page.getByRole('button', { name: '閉じる', exact: true }), page.getByText('閉じる', { exact: true })])
    for (let i = 0; i < await loc.count(); i++) if (await loc.nth(i).isVisible()) { await loc.nth(i).click(); await sleep(page, 1500); break; }
}
async function save(page) {
  await closeModals(page);
  log('save via 公開で保存する');
  await page.getByRole('button', { name: '公開で保存する', exact: true }).first().click();
  let ok = false;
  for (let i = 0; i < 15 && !ok; i++) { await sleep(page, 2000); ok = await page.evaluate(() => document.body.innerText.includes('商品を保存しました')); }
  log('save', ok ? 'OK 商品を保存しました' : 'NO MESSAGE');
  if (!ok) throw new Error('保存できなかった');
}
async function openFileModal(page, which) {   // which: 0=個人利用の欄, 1=法人利用の欄
  // ボタンはページ内の JS で文字を比べて探す（Playwright の hasText に正規表現を渡すと「ファイルの追加・管理」に当たらなかった。2026-10-18）
  // 読み込み直後や、別の欄のモーダルを閉じた直後はまだ見えないことがあるので、2つ見えるまで待つ
  let idx = [];
  for (let t = 0; t < 20; t++) {
    idx = await page.evaluate(() => [...document.querySelectorAll('button')].map((b, i) => ({ i, t: (b.textContent || '').trim(), w: b.getBoundingClientRect().width }))
      .filter(x => /^(変更する|ファイルの追加・管理)$/.test(x.t) && x.w > 0).map(x => x.i));
    if (idx.length === 2) break;
    await sleep(page, 1000);
  }
  if (idx.length !== 2) throw new Error('ファイル欄のボタンが2つでない: ' + idx.length);
  const btn = page.locator('button').nth(idx[which]);
  await btn.scrollIntoViewIfNeeded(); await btn.click(); await sleep(page, 3000);
  const open = await page.evaluate(() => [...document.querySelectorAll('div')].some(x => /cursor-pointer/.test(x.className) && /ファイルをドラッグ/.test(x.textContent || '') && x.getBoundingClientRect().width > 0));
  if (!open) throw new Error('ファイルのモーダルが開かない');
}
// 見えているチェック欄（zip の行）の状態
const boxes = page => page.evaluate(() => [...document.querySelectorAll('input[type=checkbox]')].map(c => {
  const r = c.getBoundingClientRect(); const l = c.closest('label')?.textContent || c.parentElement?.textContent || '';
  const m = l.match(/[\w.\-]+\.zip/); return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, checked: c.checked, name: m && m[0] };
}).filter(c => c.w > 0 && c.name));
async function checkNames(page, names) {   // names の行だけ、実際のクリックで ON にする（隠れたモーダルの同じ欄は触らない）
  for (let k = 0; k < 30; k++) {
    const t = (await boxes(page)).find(b => names.includes(b.name) && !b.checked);
    if (!t) break;
    await page.mouse.click(t.x, t.y); await sleep(page, 800);
  }
  return (await boxes(page)).map(b => b.name + '=' + b.checked);
}
const zipLinks = page => page.evaluate(() => [...document.querySelectorAll('a')].filter(a => /\.zip$/.test(a.textContent.trim()) && a.getBoundingClientRect().width > 0).map(a => a.textContent.trim()));
const usage = page => page.evaluate(() => (document.body.innerText.match(/[^\n]*(GB|MB)[^\n]*/g) || []).filter(s => s.length < 80).slice(0, 4));

withBrowser(async ({ context }) => {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 1000 });
  page.on('dialog', async d => { try { await d.accept(); } catch (e) { } });
  try {
    await page.goto(`https://manage.booth.pm/items/${it.id}/edit`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await sleep(page, 7000);
    if (!/manage\.booth\.pm\/items\/\d+\/edit/.test(page.url())) throw new Error('編集画面が開かない（ログイン切れ？）: ' + page.url());
    if (step === 'inspect' || step === 'verify') {
      const out = [];
      for (const w of [0, 1]) {
        await openFileModal(page, w);
        const b = await boxes(page);
        out.push({ field: w, checked: [...new Set(b.filter(x => x.checked).map(x => x.name))], unchecked: [...new Set(b.filter(x => !x.checked).map(x => x.name))], usage: await usage(page) });
        await page.screenshot({ path: path.join(LOGD, `${tag}_${step}_field${w}.png`) });
        await closeModals(page);
      }
      log(JSON.stringify(out));
      if (step === 'verify') {
        const bad = out.filter(o => !NEWN.every(n => o.checked.includes(n)) || o.checked.concat(o.unchecked).some(n => it.set.old.test(n) && !NEWN.includes(n)));
        if (bad.length) throw new Error('欄の中身が想定と違う: ' + JSON.stringify(bad));
        log('verify OK', NEWN.join(','));
      }
    } else if (step === 'upload') {
      NEW.forEach(f => { if (!fs.existsSync(f)) throw new Error('no ' + f); });
      await openFileModal(page, 0);
      const before = [...new Set(await zipLinks(page))]; log('zips before', JSON.stringify(before), 'usage', JSON.stringify(await usage(page)));
      if (NEWN.some(n => before.includes(n))) throw new Error('同じ名前の zip がもうある（男性は先に delete）');
      const z = await page.evaluate(() => { const e = [...document.querySelectorAll('div')].filter(x => /cursor-pointer/.test(x.className) && /ファイルをドラッグ/.test(x.textContent || '') && x.getBoundingClientRect().width > 0)[0]; const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
      await page.mouse.click(z.x, z.y); await sleep(page, 1500);
      const client = await context.newCDPSession(page); await client.send('DOM.enable');
      const doc = await client.send('DOM.getDocument', { depth: -1 });
      const q = await client.send('DOM.querySelectorAll', { nodeId: doc.root.nodeId, selector: 'input[type=file]' });
      if (!q.nodeIds.length) throw new Error('input[type=file] が無い');
      await client.send('DOM.setFileInputFiles', { files: NEW, nodeId: q.nodeIds[q.nodeIds.length - 1] });
      let have = [];
      for (let i = 0; i < 400; i++) {   // 最大約53分
        await sleep(page, 8000);
        have = await zipLinks(page);
        if (i % 5 === 0) log('poll', i, JSON.stringify([...new Set(have)]));
        if (NEWN.every(n => have.includes(n))) break;
        const err = await page.evaluate(() => (document.body.innerText.match(/[^\n]*(容量|上限|失敗|エラー)[^\n]*/g) || []).slice(0, 3));
        if (err.length && i % 5 === 0) log('page says', JSON.stringify(err));
      }
      if (!NEWN.every(n => have.includes(n))) throw new Error('上がりきらない: ' + JSON.stringify(have));
      const c = await checkNames(page, NEWN); log('checked', JSON.stringify([...new Set(c)]));
      await page.screenshot({ path: path.join(LOGD, tag + '_upload.png') });
      if (!NEWN.every(n => c.includes(n + '=true'))) throw new Error('チェックが入らない');
      await save(page);
    } else if (step === 'check') {
      await openFileModal(page, 1);
      const c = await checkNames(page, NEWN); log('checked', JSON.stringify([...new Set(c)]));
      if (!NEWN.every(n => c.includes(n + '=true'))) throw new Error('チェックが入らない');
      await save(page);
    } else if (step === 'checkboth') {
      // ファイルが無いバリエーションがあると「公開で保存する」が押せない（「作品ファイルの無いダウンロード販売商品があります」）。
      // 全部消したあと（男性）は、2つの欄にチェックを入れてから1回で保存する（2026-10-18）
      for (const w of [0, 1]) {
        await openFileModal(page, w);
        const c = await checkNames(page, NEWN); log('checked field' + w, JSON.stringify([...new Set(c)]));
        if (!NEWN.every(n => c.includes(n + '=true'))) throw new Error('チェックが入らない: field' + w);
        await closeModals(page);
      }
      await save(page);
    } else if (step === 'delete') {
      await openFileModal(page, 0);
      log('zips before', JSON.stringify([...new Set(await zipLinks(page))]));
      // 「削除」とファイル名の行を Y 座標で対応付け、消す対象の行だけ下から消す
      for (let n = 0; n < 30; n++) {
        const rows = await page.evaluate(() => {
          const dels = [...document.querySelectorAll('*')].filter(e => (e.textContent || '').trim() === '削除' && e.querySelectorAll('*').length <= 1 && e.getBoundingClientRect().width > 0).map(e => { const r = e.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
          const files = [...document.querySelectorAll('a')].filter(a => /\.zip$/.test(a.textContent.trim()) && a.getBoundingClientRect().width > 0).map(a => { const r = a.getBoundingClientRect(); return { y: r.y + r.height / 2, name: a.textContent.trim() }; });
          return dels.map(d => { let best = null, bd = 1e9; for (const f of files) { const dd = Math.abs(f.y - d.y); if (dd < bd) { bd = dd; best = f; } } return { ...d, name: best && bd < 30 ? best.name : null }; }).filter(x => x.name).sort((a, b) => b.y - a.y);
        });
        const m = rows.filter(r => isOld(r.name));
        if (!m.length) break;
        log('delete', m[0].name); await page.mouse.click(m[0].x, m[0].y); await sleep(page, 1500);
        const okd = page.locator('[role=dialog]:has(button:text-is("OK")), [aria-modal=true]:has(button:text-is("OK"))').last();
        if (await okd.count() && await okd.isVisible()) { await okd.getByRole('button', { name: 'OK', exact: true }).click(); await sleep(page, 2500); }
      }
      const left = [...new Set(await zipLinks(page))]; log('zips left', JSON.stringify(left));
      if (left.some(isOld)) throw new Error('消しきれない');
      await save(page);
    } else throw new Error('step: inspect | upload | check | checkboth | delete | verify');
  } finally { await page.close(); }
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, key + '.log'), 'ERROR ' + tag + ' ' + step + ' ' + e.message + '\n'); process.exit(1); });
