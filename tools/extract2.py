# -*- coding: utf-8 -*-
r"""추출 보충 (2026-10-02 실기 «미추출») — extract.py 가 놓친 SCR.BIN 글
  extract.py 는 «{…}» 와 «TC+글» 만 잡는다. 실제로는 NUL 로 끝나는 글이 더 있다:
    · «OP　…\0» (장면 대사 OP/CL) · «TC\0　…\0» · «FLE001 『虚空の道』。 …» · 기술 설명 «000　　敵単MK1RT…\0» · 일기·상태 문구 등
  규칙: 이미 잡힌 범위 밖의 NUL 구간에서 첫 SJIS(또는 반각 가나) 글자부터 NUL(또는 «}» 앞, 단 짝 없는 «}» 로 끝나면 찌꺼기라 버림)까지.
        가나·한자 2자↑. 글자 토큰 = extract.decode 와 같다.
  ★제자리: 어느 표가 가리키는지 모르는 글(아이템 설명 등)이 섞여 있어 길이를 바꾸지 않는다 — 구분 «보충:NB» = 원래 N바이트 안(남으면 반각 공백)
  → work/text/scr2.tsv (ID C#####, 같은 원문 한 줄) · work/extract.json 에 sec='scr' 항목 추가(id C…)
  python tools/extract2.py
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from extract import decode, lead, DISC
NL = chr(92) + 'n'


def units(d, cov):
    out, i, n = [], 0, len(d)
    while i < n:
        j = d.find(b'\0', i)
        if j < 0:
            j = n
        seg = d[i:j]
        k = 0
        while k < len(seg) and not (lead(seg[k]) or 0xA1 <= seg[k] <= 0xDF):
            k += 1
        a = i + k
        if a < j and any(cov[a:j]):                              # 뒷부분이 이미 잡힘(«… TCど、…» 의 TC 뒤) → 앞부분만, 끝 ASCII 명령은 뺀다
            c0 = a + cov[a:j].index(1)
            while c0 > a and d[c0 - 1] < 0x80 and not (c0 - 2 >= a and lead(d[c0 - 2])):
                c0 -= 1
            j = c0
        if a < j and not any(cov[a:j]):
            body = d[a:j]
            # 몸통 검사: SJIS·반각 가나·명령 ASCII 만, 2바이트 경계 맞음
            p, ok, cnt = 0, True, 0
            while p < len(body):
                c = body[p]
                if lead(c):
                    if p + 1 >= len(body) or not (0x40 <= body[p + 1] <= 0xFC and body[p + 1] != 0x7F):
                        ok = False; break
                    p += 2; cnt += 1
                elif 0xA1 <= c <= 0xDF:
                    p += 1; cnt += 1
                elif 0x20 <= c < 0x7F and c not in (0x7B, 0x7D):
                    p += 1
                else:
                    ok = False; break
            t = decode(body) if ok else ''
            plain = re.sub(r'\{[^}]*\}', '', t).replace(NL, '')
            if ok and cnt >= 2 and not re.search(r'[A-Za-z]', plain) \
                    and sum(1 for ch in plain if '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿') >= 2:
                out.append((a, j))
        i = d.find(bytes(1), i)
        i = n if i < 0 else i + 1
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = open(os.path.join(DISC, 'SCR.BIN'), 'rb').read()
    occ = [o for o in json.load(open(os.path.join(ROOT, 'work', 'extract.json'), encoding='utf-8')) if not o['id'].startswith('C')]
    cov = bytearray(len(d))
    for o in occ:
        if o['sec'] == 'scr':
            cov[o['start']:o['end']] = b'\1' * (o['end'] - o['start'])
    uniq, order = {}, []
    for a, e in units(d, cov):
        t = decode(d[a:e])
        o = {'file': 'SCR.BIN', 'start': a, 'end': e, 'kind': '보충:%dB' % (e - a), 'text': t, 'sec': 'scr'}
        if t not in uniq:
            uniq[t] = []; order.append(t)
        uniq[t].append(o); occ.append(o)
    rows = []
    for k, t in enumerate(order, 1):
        rid = 'C%05d' % k
        for o in uniq[t]:
            o['id'] = rid
        rows.append('\t'.join([rid, 'SCR.BIN:%X' % uniq[t][0]['start'], '보충:%dB' % min(o['end'] - o['start'] for o in uniq[t]), str(len(uniq[t])), t, '']))
    open(os.path.join(ROOT, 'work', 'text', 'scr2.tsv'), 'w', encoding='utf-8', newline='\n').write(
        'ID\t위치\t구분\t공유\t원문\t번역\n' + '\n'.join(rows) + '\n')
    json.dump(occ, open(os.path.join(ROOT, 'work', 'extract.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    chars = sum(len(re.sub(r'\{[^}]*\}|\n', '', t)) for t in order)
    print('scr2.tsv: 출현 %d · 고유 %d · 글자 %d' % (sum(len(v) for v in uniq.values()), len(order), chars))


if __name__ == '__main__':
    main()
