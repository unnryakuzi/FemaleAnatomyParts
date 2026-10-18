/*
 * Gumroad の説明文に、決まった置き換えと1行の追加だけをかける（画像などの段落以外のノードはそのまま）（2026-10-18 女性 v1.68.0）
 *   node scripts/listing/gum_desc.js <female|set|set_business> <preview|apply>
 *   preview: 今の説明文を読み、変えたあとの文と差分を gum_log/ に書く（保存しない）
 *   apply  : 書き換えて Save changes → 読み直して一致を確かめる
 * 置き換えはどれも「ちょうど1回当たる」ことを確かめてからかける。1つの文字ノードの中でしか探さない（太字などで分かれていたら止まる）
 */
const fs = require('fs'), path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const LOGD = path.join(ROOT, 'scripts/listing/gum_log'); fs.mkdirSync(LOGD, { recursive: true });
const LINE168 = 'v1.68.0: Fixed missing parts. 43 parts that the male model already had (rectus abdominis, internal oblique, transversus abdominis, rhomboids and more) were missing.';
const P = {
  female: { id: 'zdlbhd',
    reps: [['split into 673 separate meshes', 'split into 716 separate meshes'], ['673 individually separated meshes', '716 individually separated meshes']],
    insertAfter: { prefix: '🎨 NOW IN COLOR (v1.67.0)', lines: ['', LINE168] } },
  set: { id: 'dbwncg', reps: [['Female: 673 labeled meshes', 'Female: 716 labeled meshes']] },
  set_business: { id: 'pxfku', reps: [['Female: 673 labeled meshes', 'Female: 716 labeled meshes']] },
};
const [key, step] = process.argv.slice(2);
const it = P[key]; if (!it) throw new Error('key: female | set | set_business');
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, key + '_desc.log'), new Date().toISOString() + ' ' + step + ' ' + s + '\n'); };
const textOf = doc => doc.content.map(n => n.type === 'paragraph' ? (n.content || []).map(c => c.text || '').join('') : `[${n.type}]`).join('\n');

function edit(doc) {
  const d = JSON.parse(JSON.stringify(doc));
  for (const [a, b] of it.reps) {
    let hits = 0;
    for (const n of d.content) for (const c of (n.content || [])) if (c.type === 'text' && c.text.includes(a)) { hits += c.text.split(a).length - 1; c.text = c.text.split(a).join(b); }
    if (hits !== 1) throw new Error(`「${a}」が ${hits} 回（1回でない）`);
  }
  if (it.insertAfter) {
    const idx = d.content.findIndex(n => n.type === 'paragraph' && (n.content || []).map(c => c.text || '').join('').startsWith(it.insertAfter.prefix));
    if (idx < 0) throw new Error('入れる場所が無い: ' + it.insertAfter.prefix);
    const paras = it.insertAfter.lines.map(l => l ? { type: 'paragraph', content: [{ type: 'text', text: l }] } : { type: 'paragraph' });
    d.content.splice(idx + 1, 0, ...paras);
  }
  return d;
}

withBrowser(async ({ context }) => {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1400, height: 1000 }).catch(() => { });
  page.on('dialog', d => d.accept().catch(() => { }));
  try {
    await page.goto(`https://gumroad.com/products/${it.id}/edit`, { waitUntil: 'domcontentloaded', timeout: 90000 }); await page.waitForTimeout(9000);
    const getDoc = () => page.evaluate(() => document.querySelector('.ProseMirror').editor.getJSON());
    const cur = await getDoc();
    const next = edit(cur);
    fs.writeFileSync(path.join(LOGD, `${key}_desc_before.txt`), textOf(cur));
    fs.writeFileSync(path.join(LOGD, `${key}_desc_after.txt`), textOf(next));
    fs.writeFileSync(path.join(LOGD, `${key}_desc_before.json`), JSON.stringify(cur));
    const left = textOf(next).match(/\b673\b/g);
    log('nodes', cur.content.length, '->', next.content.length, '| images', cur.content.filter(n => n.type === 'image').length, '| 673 left:', left ? left.length : 0);
    if (left) throw new Error('673 が残る');
    if (step === 'preview') return;
    if (step !== 'apply') throw new Error('step: preview | apply');
    await page.evaluate(doc => document.querySelector('.ProseMirror').editor.commands.setContent(doc, true), next);
    await page.waitForTimeout(1000);
    const got = await getDoc();
    if (textOf(got) !== textOf(next) || JSON.stringify(got.content.filter(n => n.type !== 'paragraph')) !== JSON.stringify(cur.content.filter(n => n.type !== 'paragraph')))
      throw new Error('エディタに思った通りに入らない（保存していない）');
    const btn = page.getByRole('button', { name: 'Save changes', exact: true }).first();
    await btn.click(); await page.waitForTimeout(8000);
    log('saved', await page.evaluate(() => /Changes saved/i.test(document.body.innerText)) ? 'Changes saved!' : '(no message)');
    await page.reload({ waitUntil: 'domcontentloaded' }); await page.waitForTimeout(9000);
    const fin = await getDoc();
    const same = textOf(fin) === textOf(next);
    log('after reload', same ? 'text ok' : 'TEXT DIFF', '| images', fin.content.filter(n => n.type === 'image').length);
    if (!same) throw new Error('読み直すと食い違う');
  } finally { await page.close().catch(() => { }); }
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, key + '_desc.log'), 'ERROR ' + step + ' ' + e.message + '\n'); process.exit(1); });
