/*
 * BOOTH の商品名・説明文を、今の文面に決まった置き換えだけをかけて更新する（2026-10-18 女性 v1.68.0）
 *   node scripts/listing/booth_text.js <female|set> <preview|apply>
 *   preview: 今の文面を読み、置き換えたあとの文面と差分を booth_log/ に書く（保存しない）
 *   apply  : 置き換えて「公開で保存する」→ 読み直して一致を確かめる
 * 置き換えはどれも「ちょうど1回当たる」ことを確かめてからかける（当たらない・2回以上なら止める）
 */
const fs = require('fs'), path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const LOGD = path.join(ROOT, 'scripts/listing/booth_log'); fs.mkdirSync(LOGD, { recursive: true });
const LINE168 = '  ★ v1.68.0：欠けていた43パーツ（腹直筋・内腹斜筋・腹横筋・菱形筋など。男性モデルには入っていたもの）を修正しました';
const ITEMS = {
  female: {
    id: '8481858',
    title: [['）673パーツ / ', '）716パーツ / ']],
    body: [['胸の形状を673個のパーツに分けています', '胸の形状を716個のパーツに分けています'],
           ['・673個のパーツ（骨格・筋肉・歯・軟骨・靱帯・胸の形状）', '・716個のパーツ（骨格・筋肉・歯・軟骨・靱帯・胸の形状）'],
           ['\n  ★ v1.67.0：全パーツをカラーで着色', '\n' + LINE168 + '\n\n  ★ v1.67.0：全パーツをカラーで着色']],
  },
  set: {
    id: '8496725',
    title: [['女性673＋男性939パーツ', '女性716＋男性939パーツ']],
    body: [['・女性解剖モデル：673パーツ', '・女性解剖モデル：716パーツ'],
           ['（男性932／女性673パーツ）', '（男性932／女性716パーツ）']],
  },
};
const [key, step] = process.argv.slice(2);
const it = ITEMS[key]; if (!it) throw new Error('key: female | set');
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, key + '_text.log'), new Date().toISOString() + ' ' + step + ' ' + s + '\n'); };
function apply(s, reps, what) {
  for (const [a, b] of reps) {
    const n = s.split(a).length - 1;
    if (n !== 1) throw new Error(`${what}: 「${a.trim().slice(0, 30)}」が ${n} 回（1回でない）`);
    s = s.replace(a, b);
  }
  return s;
}
withBrowser(async ({ context }) => {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 1000 });
  page.on('dialog', async d => { try { await d.accept(); } catch (e) { } });
  try {
    await page.goto(`https://manage.booth.pm/items/${it.id}/edit`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(7000);
    if (!/manage\.booth\.pm\/items\/\d+\/edit/.test(page.url())) throw new Error('編集画面が開かない: ' + page.url());
    const read = () => page.evaluate(() => ({ title: document.querySelector('input[type=text]').value, body: document.querySelector('textarea:not([name="g-recaptcha-response"])').value }));
    const cur = await read();
    const next = { title: apply(cur.title, it.title, 'title'), body: apply(cur.body, it.body, 'body') };
    const left = (next.title + next.body).match(/673/g);
    fs.writeFileSync(path.join(LOGD, `${key}_text_before.txt`), 'TITLE:\n' + cur.title + '\n\nBODY:\n' + cur.body);
    fs.writeFileSync(path.join(LOGD, `${key}_text_after.txt`), 'TITLE:\n' + next.title + '\n\nBODY:\n' + next.body);
    log('title', JSON.stringify(cur.title), '->', JSON.stringify(next.title), '| body', cur.body.length, '->', next.body.length, '| 673 left:', left ? left.length : 0);
    if (left) throw new Error('673 が残る');
    if (step === 'preview') return;
    if (step !== 'apply') throw new Error('step: preview | apply');
    await page.locator('input[type=text]').first().fill(next.title);
    await page.evaluate(v => {
      const el = document.querySelector('textarea:not([name="g-recaptcha-response"])');
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true }));
    }, next.body);
    await page.waitForTimeout(800);
    const got = await read();
    if (got.title !== next.title || got.body !== next.body) throw new Error('入力が一致しない（保存していない）');
    await page.getByRole('button', { name: '公開で保存する', exact: true }).first().click();
    let ok = false;
    for (let i = 0; i < 15 && !ok; i++) { await page.waitForTimeout(2000); ok = await page.evaluate(() => document.body.innerText.includes('商品を保存しました')); }
    log('save', ok ? 'OK 商品を保存しました' : 'NO MESSAGE');
    if (!ok) throw new Error('保存できなかった');
    await page.reload({ waitUntil: 'domcontentloaded' }); await page.waitForTimeout(7000);
    const fin = await read();
    log('after reload', fin.title === next.title ? 'title ok' : 'TITLE DIFF', fin.body === next.body ? 'body ok' : 'BODY DIFF');
    if (fin.title !== next.title || fin.body !== next.body) throw new Error('読み直すと食い違う');
  } finally { await page.close(); }
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, key + '_text.log'), 'ERROR ' + step + ' ' + e.message + '\n'); process.exit(1); });
