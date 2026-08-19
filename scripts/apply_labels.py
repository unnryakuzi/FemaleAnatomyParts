# -*- coding: utf-8 -*-
"""
解剖名3言語ラベル付与スクリプト（女性版v1.66.0ロジックを再構築）
anatomy_terms.json: 正規化base名(JA) -> {en, la, conf}
  番号は key 内で 'N'、value 内で {o}=英序数 {n}=算用 {r}=ローマ で展開。
  左右は本スクリプトで en="Right/Left " 接頭・la=" dext./sin." 接尾。
使い方(Blender内):
  import apply_labels; apply_labels.run(dry_run=True)   # カバレッジと未訳一覧
  apply_labels.run(dry_run=False)                       # 全meshに custom property付与
"""
import bpy, json, re, os

TERMS_PATH = r"C:\Users\abesh\Documents\Blender\MaleAnatomy\scripts\anatomy_terms.json"

_K = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
      '十一':11,'十二':12}

def kanji_to_int(s):
    if s is None: return None
    if s.isdigit(): return int(s)
    if s in _K: return _K[s]
    if '十' in s:
        a, _, b = s.partition('十')
        tens = _K.get(a, 1) if a else 1
        ones = _K.get(b, 0) if b else 0
        return tens*10 + ones
    return _K.get(s)

def to_ordinal(n):
    if n is None: return ''
    if 10 <= n % 100 <= 20: suf = 'th'
    else: suf = {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')
    return f"{n}{suf}"

_ROMAN = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),
          (50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
def to_roman(n):
    if n is None: return ''
    out='';
    for v,s in _ROMAN:
        while n>=v: out+=s; n-=v
    return out

def strip_furigana(name):
    """末尾の対応括弧(入れ子可)をふりがなとして除去し、(本体, かな) を返す。
    ［］角括弧は解剖名の一部なので残す。"""
    s = name.rstrip()
    if not (s.endswith(')') or s.endswith('）')):
        return s, ''
    depth = 0; start = None
    for i in range(len(s)-1, -1, -1):
        c = s[i]
        if c in ')）':
            depth += 1
        elif c in '(（':
            depth -= 1
            if depth == 0:
                start = i; break
    if start is None:
        return s, ''
    kana = s[start+1:len(s)-1]
    return s[:start].strip(), kana

def detect_side(s):
    if s.startswith('右'): return 'right', s[1:]
    if s.startswith('左'): return 'left', s[1:]
    return None, s

def normalize_key(s):
    """side除去済み文字列 -> dictキー（番号をNに）と抽出番号"""
    num = None
    # 第<番号> パターン
    m = re.search(r'第([0-9０-９一二三四五六七八九十]+)', s)
    if m:
        num = kanji_to_int(m.group(1).translate(str.maketrans('０１２３４５６７８９','0123456789')))
        s = s[:m.start()] + '第N' + s[m.end():]
    else:
        # 末尾や単独の算用/ローマ数字（椎骨 T1 等は名前に無いのでまれ）
        pass
    s = re.sub(r'\.\d+$','',s)  # .001 除去
    return s.strip(), num

def expand(val, num):
    if val is None: return val
    return (val.replace('{o}', to_ordinal(num))
               .replace('{n}', str(num) if num is not None else '')
               .replace('{r}', to_roman(num)))

def load_terms():
    with open(TERMS_PATH, encoding='utf-8') as f:
        return json.load(f)

def lookup(name, terms):
    """object名 -> dict(name_ja, name_kana, name_en, name_la, conf) or None(未訳)"""
    base, kana = strip_furigana(name)
    side, base_ns = detect_side(base)
    key, num = normalize_key(base_ns)
    entry = terms.get(key)
    if entry is None:
        return None, key  # 未訳キー返す
    en = expand(entry.get('en',''), num)
    la = expand(entry.get('la',''), num)
    if side == 'right':
        en = 'Right ' + en;  la = la + ' dext.'
    elif side == 'left':
        en = 'Left ' + en;   la = la + ' sin.'
    name_ja = base  # 表示用JA（ふりがな除去・左右含む全体）
    return {'name_ja': name_ja, 'name_kana': kana, 'name_en': en,
            'name_la': la, 'conf': entry.get('conf')}, key

def run(dry_run=True):
    terms = load_terms()
    meshes = [o for o in bpy.data.objects if o.type=='MESH']
    matched = 0
    unmatched = {}   # key -> example object name
    for o in meshes:
        res, key = lookup(o.name, terms)
        if res is None:
            unmatched.setdefault(key, o.name)
            continue
        matched += 1
        if not dry_run:
            o['name_ja'] = res['name_ja']
            o['name_kana'] = res['name_kana']
            o['name_en'] = res['name_en']
            o['name_la'] = res['name_la']
    print(f"[apply_labels] matched {matched}/{len(meshes)}  unmatched_keys={len(unmatched)}  dry_run={dry_run}")
    return {'matched': matched, 'total': len(meshes), 'unmatched': unmatched}
