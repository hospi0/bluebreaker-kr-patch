# -*- coding: utf-8 -*-
r"""번역 묶음 병합·검사 — work/ko/{scr,sys}.tsv 의 «번역» 열을 채운다.
  python tools/ko_merge.py 묶음.txt [...]   (묶음 = «ID<TAB>번역» 줄들, # 주석 무시)
  python tools/ko_merge.py --check          (전체 검사만)
검사: 토큰({..}·\n) 순서·개수 = 원문 · 가나/한자 잔류 · 한 줄 폭(전각 1 · 반각 0.5) > 17 경고 · 메뉴:NB 바이트 예산(한글 2B)
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KO = os.path.join(ROOT, 'work', 'ko')
TOK = re.compile(r'\{[^}]*\}|\\n')
JP = re.compile(r'[\u3131-\u318e\u3040-\u30fa\u30fc-\u30ff\u3400-\u9fff\uff66-\uff9f]')  # ・(30FB) 는 허용


def load(name):
    p = os.path.join(KO, name + '.tsv')
    lines = open(p, encoding='utf-8').read().split('\n')
    return p, lines[0], [l.split('\t') for l in lines[1:] if l]


def save(p, head, rows):
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(head + '\n' + ''.join('\t'.join(r) + '\n' for r in rows))


def width(s):
    s = TOK.sub('', s)
    return sum(0.5 if ord(c) < 0x80 or 0xff61 <= ord(c) <= 0xff9f else 1 for c in s)


def nbytes(s):
    n = 0
    for t in re.split(r'(\{[^}]*\}|\\n)', s):
        if t == '\\n': n += 2
        elif t.startswith('{a:') or t == '{sp}': n += 1
        elif t.startswith('{NMR:') or t.startswith('{NM:'): n += 6
        elif t.startswith('{MK'): n += 3
        elif t.startswith('{'): n += len(t) - 2
        else: n += sum(1 if ord(c) < 0x80 or 0xff61 <= ord(c) <= 0xff9f else 2 for c in t)
    return n


def check(r):
    src, ko = r[4], r[5]
    if not ko: return []
    err = []
    if TOK.findall(src) != TOK.findall(ko): err.append('토큰 불일치')
    k = 0                                    # 원문과 같은 머리(표 데이터 바이트 등)는 그대로 둔 것 → 검사 제외
    while k < min(len(src), len(ko)) and src[k] == ko[k]: k += 1
    if JP.search(ko[k:]): err.append('가나/한자 잔류: ' + ''.join(JP.findall(ko[k:])))
    for seg in re.split(r'\\n|\{PC\}', ko):
        if width(seg) > 17: err.append('폭 %.1f: %s' % (width(seg), seg))
    m = re.match(r'(?:메뉴|보충):(\d+)B', r[2])
    if m and nbytes(ko) > int(m.group(1)): err.append('예산 초과 %dB>%sB' % (nbytes(ko), m.group(1)))
    return err


def main(args):
    tabs = {n: load(n) for n in ('scr', 'sys', 'scr2', 'sys2') if os.path.exists(os.path.join(ROOT, 'work', 'ko', n + '.tsv'))}
    idx = {r[0]: r for n in tabs for r in tabs[n][2]}
    for fn in [a for a in args if a != '--check']:
        for l in open(fn, encoding='utf-8'):
            l = l.rstrip('\n')
            if not l or l.startswith('#'): continue
            i, t = l.split('\t', 1)
            idx[i][5] = t
    bad = 0
    for n, (p, head, rows) in tabs.items():
        done = sum(1 for r in rows if r[5])
        for r in rows:
            for e in check(r):
                bad += 1; print(r[0], e)
        print('%s: %d/%d' % (n, done, len(rows)))
        if args != ['--check']: save(p, head, rows)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:] or ['--check']))
