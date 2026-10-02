# -*- coding: utf-8 -*-
r"""빌드 결과(work/new)에 남은 일본어 찾기 — 한글이 쓰는 JIS 구(16구~)를 빼고 가나·한자가 2자↑ 남은 SJIS 덩어리
  python tools/leftover.py [파일 …]   (기본 0.BIN SCR.BIN)
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import lead


def jis(b1, b2):
    if b1 >= 0xE0: b1 -= 0x40
    ku = (b1 - 0x81) * 2 + 1; 
    if b2 >= 0x9F: ku += 1; ten = b2 - 0x9E
    else: ten = b2 - 0x40 + (0 if b2 < 0x80 else -1) + 1
    return ku, ten


def runs(d, kmax):
    i, n = 0, len(d)
    while i < n - 1:
        if not lead(d[i]):
            i += 1; continue
        j, jp, ko = i, 0, 0
        while j + 1 < n and lead(d[j]) and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F:
            ku, ten = jis(d[j], d[j + 1])
            if 16 <= ku <= kmax: ko += 1
            elif ku in (4, 5) or ku >= 16: jp += 1
            j += 2
        if jp >= 2 and jp >= ko:
            yield i, j, jp, ko
        i = max(j, i + 1)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    kmax = int(os.environ.get('KMAX', '0')) or None
    if kmax is None:
        import insert
        tr = {}
        for nm in ('scr', 'scr2', 'sys'):
            for k, r in insert.load(nm).items():
                if r[5]: tr[k] = r[5]
        kmax = 16 + (len(insert.charmap(list(tr.values()))) - 1) // 94
    print('한글 구 16‥%d' % kmax)
    for f in sys.argv[1:] or ['0.BIN', 'SCR.BIN']:
        new = open(os.path.join(ROOT, 'work', 'new', f), 'rb').read()
        r = list(runs(new, kmax))
        print('==', f, len(r))
        for a, e, jp, ko in r:
            print('  %06X %3d %s' % (a, e - a, new[a:e].decode('cp932', 'replace')))
