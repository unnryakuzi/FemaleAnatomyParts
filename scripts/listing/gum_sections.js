/*
 * Gumroad のプロフィールを系統ごとの3セクションに分け、法人向け（Business license）の2商品を一覧から外す（2026-10-31 ユーザー決定: 案2）
 *   node scripts/listing/gum_sections.js          … 画面で設定するだけで保存しない（スクショを撮る）
 *   SAVE=1 node scripts/listing/gum_sections.js   … 最後に「Update profile」で保存する
 * 変える前の状態: セクションは「Anatomy Models」1つで全10商品にチェック、Add new products by default はオン。
 * 法人向けの商品は一覧に出さず、個人向けの説明文のリンクから開いてもらう。
 * 新しい商品が勝手にどこかのセクションへ入らないよう、Add new products by default は全セクションでオフにする。
 */
const path = require('path');
const { withBrowser } = require('C:/Users/abesh/tools/browser-auto/connect.js');
const LOGD = path.join(__dirname, 'gum_log');

const SECTIONS = [
  ['Colored Anatomy Models', t => /^(Female Anatomy Model —|Male Anatomy Model —|Male \+ Female Anatomy Models —)/.test(t)],
  ['Rigged Muscle Body', t => /^Anatomy Muscle Body/.test(t)],
  ['Rigged Skeleton', t => /^Anatomy Skeleton/.test(t)],
];

withBrowser(async ({ context }) => {
  const p = await context.newPage();
  await p.setViewportSize({ width: 1400, height: 1000 }).catch(() => { });
  p.on('dialog', d => d.accept().catch(() => { }));
  try {
    await p.goto('https://gumroad.com/settings/profile', { waitUntil: 'domcontentloaded', timeout: 90000 }); await p.waitForTimeout(5000);
    await p.mouse.click(447, 100); await p.waitForTimeout(3000);   // Pages タブ（左のメニューにも同じ文字があるので座標で押す）

    const nSec = async () => p.getByRole('button', { name: 'Duplicate section' }).count();
    if (await nSec() !== 1) throw new Error('セクションが1つではない（' + await nSec() + '）。手順の前提が違うので止める');
    for (let i = 0; i < 2; i++) { await p.getByRole('button', { name: 'Duplicate section' }).first().click(); await p.waitForTimeout(2500); }
    if (await nSec() !== 3) throw new Error('複製後のセクションが3つにならない: ' + await nSec());
    // 畳まれているセクションを開く
    for (let i = 0; i < 5; i++) {
      const ex = p.getByRole('button', { name: /^Expand .* section$/ });
      if (!(await ex.count())) break;
      await ex.first().click(); await p.waitForTimeout(1500);
    }

    const names = p.getByLabel('Section name', { exact: true });
    if (await names.count() !== 3) throw new Error('Section name 欄が3つ見えない: ' + await names.count());
    for (let s = 0; s < 3; s++) {
      const [title, belongs] = SECTIONS[s];
      await names.nth(s).fill(title); await p.waitForTimeout(500);
      // このセクションの範囲 = s 番目の Section name 欄から次の Section name 欄（または Add section）まで
      const res = await p.evaluate(({ s, src }) => {
        const belongs = new Function('t', 'return (' + src + ')(t)');
        const inputs = [...document.querySelectorAll('input')].filter(e => e.labels?.[0]?.innerText.trim() === 'Section name');
        const top = inputs[s].getBoundingClientRect().top + scrollY;
        const next = inputs[s + 1] ? inputs[s + 1].getBoundingClientRect().top + scrollY : Infinity;
        const inSec = e => { const y = e.getBoundingClientRect().top + scrollY; return y > top && y < next; };
        const out = [];
        for (const e of document.querySelectorAll('input[type=checkbox]')) {
          if (!inSec(e)) continue;
          const lab = (e.labels?.[0]?.innerText || e.closest('label')?.innerText || '').trim();
          const want = lab === 'Add new products by default' ? false : lab === 'Show product filters' ? e.checked : belongs(lab) && !/Business license$/.test(lab);
          if (e.checked !== want) e.click();
          out.push(`${want ? '■' : '□'} ${lab.slice(0, 80)}`);
        }
        return out;
      }, { s, src: belongs.toString() });
      console.log(`== ${title}\n` + res.join('\n'));
      await p.waitForTimeout(1000);
    }
    // 画面上の状態を読み直して確かめる
    const check = await p.evaluate(() => [...document.querySelectorAll('input[type=checkbox]:checked')].map(e => (e.labels?.[0]?.innerText || '').trim().slice(0, 40)));
    console.log('checked now:', check.length, JSON.stringify(check));
    await p.screenshot({ path: path.join(LOGD, 'sections_before_save.png'), fullPage: true });

    if (process.env.SAVE === '1') {
      await p.getByRole('button', { name: 'Update profile' }).click(); await p.waitForTimeout(5000);
      console.log('saved');
    } else console.log('DRY: not saved');
  } finally { await p.close(); }
});
