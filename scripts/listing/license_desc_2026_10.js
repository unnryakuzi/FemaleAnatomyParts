/**
 * 2026-10 ライセンス変更: BOOTH / Gumroad の商品説明のライセンス表記を書き換える。
 *
 *   node license_desc_2026_10.js booth <itemId> [--dry]
 *   node license_desc_2026_10.js gumroad <productId> [--dry]
 *
 * 置き換えるのは3か所だけ（ほかの本文には触れない）:
 *   1) 特徴の箇条「商用利用・改変・再配布OK（CC BY-SA 2.1 JP）」→「商用利用・改変OK（データの再配布・転売は禁止）」
 *   2) ライセンスの段落 → ユーザー指定の文面（LICENSE_JA / LICENSE_EN）
 *   3) 出典の行（3DAnatomyman / always3d の派生）→ 削除（出典は 2) の文面に含まれる）
 *
 * BOOTH は textarea を同一セッションで書き換えて「公開で保存する」（booth.js と混ぜない。SKILL の罠4）。
 * Gumroad は tiptap(ProseMirror) のブロック単位で選択→insertText / 削除し、Save changes。
 */
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');

const [site, id] = process.argv.slice(2);
const DRY = process.argv.includes('--dry');

const LICENSE_JA = '・ライセンス：本モデルは「BodyParts3D」© ライフサイエンス統合データベースセンター（CC 表示 4.0 国際）を改変して作成しました。商用・非商用を問わず、作品の制作に利用・改変できます。対象はイラスト・漫画・映像などのほか、モデルを単体で取り出せない形でのゲームへの組み込みも含みます。本モデルのデータそのもの（改変したものを含む）の再配布・転売・共有は禁止します。';
const FEATURE_JA = '・商用利用・改変OK（データの再配布・転売は禁止）';
const LICENSE_EN = 'License: This model is an adaptation of "BodyParts3D" © The Database Center for Life Science (CC BY 4.0). You may use and modify it to create your own works, commercial or non-commercial: illustrations, comics, video and more, including embedding it in a game in a form where the model cannot be extracted on its own. Redistributing, reselling or sharing the model data itself (including modified versions) is prohibited.';
const FEATURE_EN = 'Commercial use and modification allowed (no redistribution or resale of the model data)';

function boothTransform(text) {
  const out = []; const hits = { feature: 0, license: 0, source: 0 };
  for (const line of text.split('\n')) {
    const ind = line.match(/^\s*/)[0]; const t = line.trim();
    if (t === '・商用利用・改変・再配布OK（CC BY-SA 2.1 JP）') { out.push(ind + FEATURE_JA); hits.feature++; continue; }
    if (t.startsWith('・ライセンスは CC BY-SA 2.1 JP。')) { out.push(ind + LICENSE_JA); hits.license++; continue; }
    if (t.startsWith('・出典：「3DAnatomyman」(always3d)')) { hits.source++; continue; }
    out.push(line);
  }
  return { text: out.join('\n'), hits };
}

async function booth(page) {
  await page.goto('https://manage.booth.pm/items/' + id + '/edit', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  const ta = page.locator('textarea').first();
  const cur = await ta.inputValue();
  const { text, hits } = boothTransform(cur);
  console.log('hits', JSON.stringify(hits));
  if (hits.feature !== 1 || hits.license !== 1 || hits.source !== 1) throw new Error('想定の3行が1つずつ見つからない（中止）');
  if (/BY-SA|3DAnatomyman|always3d/.test(text)) throw new Error('置換後にも旧表記が残る（中止）');
  if (DRY) { console.log('--- DRY ---\n' + text); return; }
  await ta.evaluate((el, v) => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, text);
  await page.waitForTimeout(1000);
  await page.getByRole('button', { name: '公開で保存する', exact: true }).first().click();
  await page.waitForTimeout(8000);
  // 公開ページで確認（編集画面の表示では判断しない）
  await page.goto('https://kabe-tech.booth.pm/items/' + id, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(5000);
  const body = await page.evaluate(() => document.body.innerText);
  console.log('public: BY-SA', (body.match(/BY-SA/g) || []).length, '/ always3d', (body.match(/always3d/g) || []).length,
    '/ 新文面', body.includes('再配布・転売・共有は禁止します'), '/ 特徴', body.includes('データの再配布・転売は禁止'));
}

async function gumroad(page) {
  await page.goto('https://gumroad.com/products/' + id + '/edit', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  const plan = await page.evaluate(({ LICENSE_EN, FEATURE_EN, DRY }) => {
    const ed = document.querySelector('.tiptap, .ProseMirror');
    if (!ed) return { err: 'no editor' };
    const blocks = [...ed.querySelectorAll('p, li')].filter(b => !b.querySelector('p, li'));
    const hits = { feature: 0, license: 0, source: 0 };
    const acts = [];
    for (const b of blocks) {
      const t = b.textContent.trim();
      const pre = (t.match(/^[•\-]\s*/) || [''])[0];
      if (/^[•\-]?\s*Commercial use, modification,? (and )?redistribution (are )?allowed \(CC BY-SA 2\.1 JP\)$/.test(t)) { acts.push([b, pre + FEATURE_EN]); hits.feature++; }
      else if (/Licen[cs]e(d under| is|:) CC BY-SA 2\.1 JP/.test(t)) {
        const tail = (t.match(/(Each download includes.*)$/) || [''])[0];
        acts.push([b, pre + LICENSE_EN + (tail ? ' ' + tail : '')]); hits.license++;
      }
      else if (/(Source: derivative of|Derived from) "3DAnatomyman"/.test(t)) { acts.push([b, null]); hits.source++; }
      // 女性(zdlbhd)はライセンス段落が複数の <p> に折れている。続きの行も消す
      else if (/^redistribute, BUT due to ShareAlike|^redistribute\/resell — the seller cannot forbid this|^LICENSE\.txt \/ CREDITS\.txt\.$/.test(t)) { acts.push([b, null]); hits.cont = (hits.cont || 0) + 1; }
    }
    if (DRY) return { hits, preview: acts.map(([b, n]) => [b.tagName, b.textContent.trim()]) };
    // 後ろから処理（前のブロックの位置がずれないように）
    for (const [b, n] of acts.reverse()) {
      const s = getSelection(); const r = document.createRange();
      ed.focus();
      if (n === null) {
        // 中身だけ消す（隣のブロックと結合させない＝近くの画像を巻き込まない）
        r.selectNodeContents(b);
        s.removeAllRanges(); s.addRange(r); document.execCommand('delete');
      } else {
        r.selectNodeContents(b); s.removeAllRanges(); s.addRange(r);
        document.execCommand('insertText', false, n);
      }
    }
    const after = ed.innerText;
    return { hits, left: (after.match(/BY-SA|3DAnatomyman|always3d/g) || []).length, ok: after.includes('is prohibited.') };
  }, { LICENSE_EN, FEATURE_EN, DRY });
  console.log(JSON.stringify(plan, null, 1));
  if (DRY || plan.err) return;
  if (plan.left) throw new Error('旧表記が残っている（保存しない）');
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: 'Save changes', exact: true }).first().click({ timeout: 30000 });
  await page.waitForTimeout(6000);
  const pub = (await page.evaluate(() => location.href)).includes('/bundles/') ? null : 'https://liberation58.gumroad.com/l/' + id;
  await page.goto('https://liberation58.gumroad.com/l/' + id, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  const body = await page.evaluate(() => document.body.innerText);
  console.log('public: BY-SA', (body.match(/BY-SA/g) || []).length, '/ always3d', (body.match(/always3d/g) || []).length,
    '/ new license', body.includes('is prohibited.'), pub ? '' : '(bundle)');
}

setTimeout(() => { console.log('TIMEOUT'); process.exit(2); }, 300000);
withBrowser(async ({ getPage }) => {
  const page = await getPage(site === 'booth' ? 'manage.booth.pm' : 'gumroad.com');
  if (site === 'booth') await booth(page); else await gumroad(page);
}).then(() => process.exit(0)).catch(e => { console.error('ERROR:', e.message); process.exit(1); });
