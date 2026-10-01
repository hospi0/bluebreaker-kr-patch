# -*- coding: utf-8 -*-
r"""번역 삽입 (2026-10-02) — work/ko/{scr,sys}.tsv → 4.KNJ · SCR.BIN · 0.BIN 등 → 트랙 1
  글자: 번역에 나오는 한글 음절을 4.KNJ 한자 칸(JIS 16구 1점부터 차례로)에 갈무리14 로 그리고 그 SJIS 코드로 쓴다.
  대사(SCR.BIN): 묶음(tools/scrblk.py)마다 대사 단위를 바꿔 다시 짜고 머리 오프셋 표를 고친다
                 (점프는 스크립트 번호라 그대로) — 새 묶음이 원래 묶음 칸(다음 묶음 시작까지)을 넘으면 빌드 실패.
  메뉴(0.BIN 등): 제자리 — 원래 바이트 안, 남는 곳은 00. 0x1FA24 «す。»(두 설정 설명의 둘째 줄 공용) → «다。».
  빌더 규칙: 문장부호 뒤 공백 1칸 삭제 · 대사의 ASCII 영숫자·괄호 → 전각(원문 대사엔 1바이트가 쉼표·반각 가나뿐)
             · 대사 한 줄 폭 ≤ 17(전각 1 · 반각 0.5) · 인코딩 못 하는 글자 = 빌드 실패.
  python tools/insert.py [--dry] [--install]
"""
import json, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, iso, poc, scrblk
from ko_merge import width

DISC = os.path.join(ROOT, 'work', 'disc')
OUT = poc.OUT
INSTALL = r'F:\hospi\roms\ss roms\Blue Breaker - Ken yori mo Hohoemi o (Japan)'
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
NL = chr(92) + 'n'
WIDTH = 17
TOK = re.compile(r'\{[^}]*\}|\\n')


def squeeze(s):
    """문장부호 뒤 공백 1칸 삭제(2칸 이상은 칸 맞춤이라 둔다)"""
    return re.sub('([' + re.escape(PUNCT) + ']) (?! )', r'\1', s)


def to_full(s):
    """토큰 밖 ASCII 영숫자·괄호 → 전각"""
    out = []
    for t in re.split(r'(\{[^}]*\}|\\n)', s):
        if not TOK.fullmatch(t or 'x'):
            t = ''.join(chr(ord(c) + 0xFEE0) if c.isascii() and (c.isalnum() or c in '()') else c for c in t)
        out.append(t)
    return ''.join(out)


def load(name):
    rows = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'ko', name + '.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    return {r[0]: r for r in rows}


def charmap(texts):
    syl = sorted({c for t in texts for c in TOK.sub('', t) if '가' <= c <= '힣'})
    cmap = {}
    for k, ch in enumerate(syl):
        ku, ten = 16 + k // 94, 1 + k % 94
        cmap[ch] = (ku, ten, poc.sjis_of(ku, ten))
    return cmap


def encode(s, cmap):
    out = bytearray()
    for t in re.split(r'(\{[^}]*\}|\\n)', s):
        if not t:
            continue
        if t == NL:
            out += b'RT'
        elif t in ('{PC}', '{EP}', '{TC}'):
            out += t[1:3].encode()
        elif re.fullmatch(r'\{MK\d\}', t):
            out += t[1:4].encode()
        elif t.startswith('{NMR:'):
            out += b'NMR' + t[5:-1].encode()
        elif t == '{sp}':
            out += b' '
        elif t.startswith('{a:'):
            out.append(int(t[3:5], 16))
        else:
            for c in t:
                if c in cmap:
                    out += cmap[c][2]
                else:
                    try:
                        out += c.encode('cp932')
                    except UnicodeEncodeError:
                        raise SystemExit('⛔인코딩 못 하는 글자 %r in %r' % (c, s))
    return bytes(out)


# 묶음 마지막 스크립트 뒤 찌꺼기(이전 버퍼 잔재) 시작 — 칸이 모자란 묶음만 확인해 적는다(묶음 기준 오프셋)
#   BB800: 마지막 스크립트 «MWCL SDOFPMWTCPLDFR» 뒤 0xD37 부터 «п[ムはRT}…» 잘린 글 = 찌꺼기
JUNK = {0xBB800: 0xD37}


def rebuild(d, b, offs, e, mine, tr, cmap):
    """묶음 [b, e) 안 대사 단위 mine 을 번역으로 바꾸고 머리 오프셋 표를 고친 새 묶음"""
    parts, pos, shifts = [], b, []
    for o in mine:
        new = encode(tr[o['id']], cmap)
        parts.append(d[pos:o['start']]); parts.append(new)
        shifts.append((o['start'] - b, len(new) - (o['end'] - o['start'])))
        pos = o['end']
    parts.append(d[pos:e])
    blk = bytearray(b''.join(parts))
    for k, off in enumerate(offs):
        no = off + sum(dl for s, dl in shifts if s < off)
        struct.pack_into('>I', blk, 4 * k, no)
        if d[b + off] != blk[no]:                                # 검산: 스크립트 첫 바이트(명령)가 그대로인지
            raise SystemExit('⛔오프셋 검산 실패 묶음 %X 항목 %d' % (b, k))
    while len(blk) > e - b and blk[-1] == 0:                     # 끝 00 은 덜어 낼 수 있음
        blk.pop()
    return blk


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    scr_tr, sys_tr = load('scr'), load('sys')
    tr = {}
    errs = []
    for i, r in scr_tr.items():
        if r[5]:
            t = to_full(squeeze(r[5]))
            for seg in t.replace('{PC}', NL).split(NL):
                if width(seg) > WIDTH:
                    errs.append('%s 폭 %.1f > %d: %s' % (i, width(seg), WIDTH, seg))
            tr[i] = t
    for i, r in sys_tr.items():
        if r[5]:
            tr[i] = squeeze(r[5])
    if errs:
        raise SystemExit('⛔대사 줄 폭 초과 %d줄\n' % len(errs) + '\n'.join(errs))
    cmap = charmap(list(tr.values()))
    print('번역 %d줄 · 한글 %d자 → KNJ %d구‥%d구' % (len(tr), len(cmap), 16, 16 + (len(cmap) - 1) // 94))

    # 글꼴
    F = poc.bdf.Font(poc.GAL)
    knj = bytearray(open(os.path.join(DISC, '4.KNJ'), 'rb').read())
    for ch, (ku, ten, _) in cmap.items():
        i = 128 + (ku - 1) * 94 + (ten - 1)
        knj[i * 32:i * 32 + 32] = poc.glyph(F, ch)

    occ = json.load(open(os.path.join(ROOT, 'work', 'extract.json'), encoding='utf-8'))
    files = {'4.KNJ': bytes(knj)}

    # 대사 SCR.BIN — 묶음마다 다시 짜기
    d = open(os.path.join(DISC, 'SCR.BIN'), 'rb').read()
    out = bytearray(d)
    units = sorted((o for o in occ if o['sec'] == 'scr' and o['id'] in tr), key=lambda o: o['start'])
    B = scrblk.blocks(d); over = []; nchg = 0; ntail = 0
    ui = 0
    for b, n, offs, e in B:
        mine = []
        while ui < len(units) and units[ui]['start'] < e:
            if units[ui]['start'] >= b:
                mine.append(units[ui])
            ui += 1
        if not mine:
            continue
        blk = rebuild(d, b, offs, e, mine, tr, cmap)
        if len(blk) > e - b and b in JUNK:                      # 칸 초과 → 확인된 찌꺼기 꼬리를 버리고 다시
            assert JUNK[b] > offs[-1]
            mine = [o for o in mine if o['start'] < b + JUNK[b]]
            blk = rebuild(d, b, offs, b + JUNK[b], mine, tr, cmap); ntail += 1
        if len(blk) > e - b:
            over.append('%X: %d B > 칸 %d B' % (b, len(blk), e - b)); continue
        out[b:e] = bytes(blk) + bytes(e - b - len(blk))
        nchg += 1
    if over:
        raise SystemExit('⛔묶음 칸 초과 %d곳\n' % len(over) + '\n'.join(over))
    files['SCR.BIN'] = bytes(out)
    print('대사 단위 %d · 바뀐 묶음 %d/%d (찌꺼기 꼬리 버림 %d)' % (len(units), nchg, len(B), ntail))

    # 메뉴 — 제자리
    bufs = {}; over = []; nput = 0
    for o in occ:
        if o['sec'] != 'sys' or o['id'] not in tr:
            continue
        f = o['file']
        if f not in bufs:
            bufs[f] = bytearray(open(os.path.join(DISC, f), 'rb').read())
        new = encode(tr[o['id']], cmap); room = o['end'] - o['start']
        if len(new) > room:
            over.append('%s %s:%X 예산 %d B < %d B  %s' % (o['id'], f, o['start'], room, len(new), tr[o['id']])); continue
        bufs[f][o['start']:o['end']] = new + bytes(room - len(new)); nput += 1
    if over:
        raise SystemExit('⛔메뉴 문자열 예산 초과 %d곳\n' % len(over) + '\n'.join(sorted(set(over))))
    b0 = bufs.setdefault('0.BIN', bytearray(open(os.path.join(DISC, '0.BIN'), 'rb').read()))
    assert bytes(b0[0x1FA24:0x1FA28]) == 'す。'.encode('cp932')
    b0[0x1FA24:0x1FA26] = encode('다', cmap)
    for f, v in bufs.items():
        files[f] = bytes(v)
    print('메뉴 %d자리 · 바뀐 파일 %s' % (nput, sorted(files)))

    if '--dry' in sys.argv:
        print('(--dry: 디스크 안 씀)'); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    iso.patch(disc.ROM, OUT, files)
    print('→', OUT)
    if '--install' in sys.argv:
        dst = os.path.join(INSTALL, os.path.basename(OUT))
        shutil.copy2(OUT, dst); print('F: 설치', dst)


if __name__ == '__main__':
    main()
