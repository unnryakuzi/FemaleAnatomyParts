/*
 * BOOTH の「メッセージ一斉送信」で、商品の所有者に更新を知らせる（2026-10-18 女性 v1.68.0。ユーザー承認済みの文面）
 *   node scripts/listing/booth_notice.js <preview|send>
 *   preview: 宛先・メモ・本文を入れて「確認する」を押し、確認画面を読んでスクショを撮る（送らない）
 *   send   : 同じ手順のあと、確認画面で送信する。一斉送信は無料枠が月1回なので、preview で中身を見てから使う
 * 宛先は「商品の所有者」（自分用に購入、またはギフトを受け取ったユーザー）＝ダウンロードできる人
 */
const fs = require('fs'), path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const ROOT = 'C:/Users/abesh/Documents/Blender/MaleAnatomy';
const LOGD = path.join(ROOT, 'scripts/listing/booth_log'); fs.mkdirSync(LOGD, { recursive: true });
const ITEMS = ['8481858', '8496725'];   // 女性・男女セット
const MEMO = '女性 v1.68.0 更新のお知らせ 2026-10-18';
const BODY = [
  '女性解剖モデル（カラー版。男女セットにも入っています）を v1.68.0 にアップデートしました。',
  'ライブラリから最新版をダウンロードできます。',
  '',
  '■ 主な変更',
  '・欠けていた43パーツ（腹直筋・内腹斜筋・腹横筋・菱形筋など。男性モデルには入っていたもの）を修正しました。全716パーツになりました',
  '・胸郭の幅と、腹直筋・内腹斜筋・腹横筋・錐体筋の形を修正しました',
  '・多裂筋の位置を修正しました',
  '・.blend を開いたときにオーバーレイがオフになっていたのを修正しました',
  '',
  '今後ともよろしくお願いいたします。',
  'kabe-tech',
].join('\n');
const step = process.argv[2];
if (!['preview', 'send'].includes(step)) throw new Error('step: preview | send');
const log = (...a) => { const s = a.join(' '); console.log(s); fs.appendFileSync(path.join(LOGD, 'notice.log'), new Date().toISOString() + ' ' + step + ' ' + s + '\n'); };

withBrowser(async ({ context }) => {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 1000 });
  page.on('dialog', d => d.dismiss().catch(() => { }));
  try {
    await page.goto('https://manage.booth.pm/mass_messages', { waitUntil: 'domcontentloaded', timeout: 60000 }); await page.waitForTimeout(5000);
    const left = await page.evaluate(() => (document.body.innerText.match(/残り\s*(\d+)\s*件[^\n]*/) || [])[0]);
    log('quota', left);
    if (!/残り\s*[1-9]/.test(left || '')) throw new Error('送信できる残り件数が無い');
    await page.goto('https://manage.booth.pm/mass_messages/new', { waitUntil: 'domcontentloaded', timeout: 60000 }); await page.waitForTimeout(6000);
    await page.locator('input[type=radio][value=owner]').check({ force: true }); await page.waitForTimeout(2500);
    for (const id of ITEMS) {
      const cb = page.locator(`input[type=checkbox][value="${id}"]`);
      if (await cb.count() !== 1) throw new Error('商品の欄が無い: ' + id);
      // チェック欄は見た目の部品の下にあるので、ラベルごとクリックする
      const box = await cb.evaluate(e => { const l = e.closest('label') || e.parentElement; l.scrollIntoView({ block: 'center' }); const r = l.getBoundingClientRect(); return { x: r.x + 12, y: r.y + r.height / 2 }; });
      if (!(await cb.isChecked())) { await page.mouse.click(box.x, box.y); await page.waitForTimeout(1200); }
      if (!(await cb.isChecked())) await cb.check({ force: true });
      await page.waitForTimeout(800);
      log('item', id, await cb.isChecked() ? 'checked' : 'NOT CHECKED');
    }
    const target = await page.evaluate(() => (document.body.innerText.match(/対象ユーザー数：\s*\d+/) || [])[0]);
    log('target', target);
    if (!/対象ユーザー数：\s*[1-9]/.test(target || '')) throw new Error('対象ユーザーが0');
    await page.locator('input[type=text]:visible').first().fill(MEMO);
    await page.locator('textarea:not([name="g-recaptcha-response"])').first().fill(BODY);   // 最後の textarea は reCAPTCHA の隠し欄
    await page.waitForTimeout(800);
    const got = await page.locator('textarea:not([name="g-recaptcha-response"])').first().inputValue();
    if (got !== BODY) throw new Error('本文が一致しない');
    const confirm = page.getByRole('button', { name: '確認する', exact: true });
    if (await confirm.isDisabled()) throw new Error('「確認する」が押せない');
    await confirm.click(); await page.waitForTimeout(4000);
    const conf = await page.evaluate(() => ({ url: location.href, text: document.body.innerText.split('BOOTHで「売りたい」')[0].slice(0, 2500),
      buttons: [...document.querySelectorAll('button')].filter(b => b.getBoundingClientRect().width > 0).map(b => (b.textContent || '').trim()).filter(Boolean) }));
    fs.writeFileSync(path.join(LOGD, 'notice_confirm.txt'), conf.text);
    await page.screenshot({ path: path.join(LOGD, 'notice_confirm.png'), fullPage: true });
    log('confirm page', conf.url, JSON.stringify(conf.buttons));
    if (!conf.text.includes('アップデートしました')) throw new Error('確認画面に本文が無い');
    if (step === 'preview') { log('preview only（送っていない）'); return; }
    const sendBtn = page.getByRole('button', { name: /^(送信する|送信)$/ }).first();
    if (!(await sendBtn.count())) throw new Error('送信ボタンが無い: ' + JSON.stringify(conf.buttons));
    await sendBtn.click(); await page.waitForTimeout(6000);
    const after = await page.evaluate(() => ({ url: location.href, text: document.body.innerText.split('BOOTHで「売りたい」')[0].slice(0, 1500) }));
    log('after send', after.url, JSON.stringify(after.text.slice(0, 600)));
    await page.screenshot({ path: path.join(LOGD, 'notice_sent.png'), fullPage: true });
  } finally { await page.close().catch(() => { }); }
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); fs.appendFileSync(path.join(LOGD, 'notice.log'), 'ERROR ' + step + ' ' + e.message + '\n'); process.exit(1); });
