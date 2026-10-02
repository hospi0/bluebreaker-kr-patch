# -*- coding: utf-8 -*-
r"""추출 보충 3 (2026-10-02 실기 «미추출» 2차) → work/text/sys2.tsv (ID D#####, 제자리 «보충:NB»)
  놓친 원인 두 가지:
    · 0.BIN 등: 문자열 «앞 바이트»가 NUL 이 아니면(코드·포인터 표 바로 뒤에 붙은 «＜回復薬＞»·«一泊»·아이템/기술 설명 등) extract.py 가 버렸다
    · SCR.BIN: 기술 설명의 변수 토큰 «NM2000»(NM + 4자)을 몰라 «영문자 섞임»으로 버렸다 → 토큰 {NM:xxxx}
  규칙: 이미 잡힌 범위 밖, NUL 로 끝나는 덩어리의 첫 SJIS(반각 가나) 글자부터 — 몸통은 SJIS·반각 가나·명령 ASCII(EP·NMxxxx·MKn·RT·숫자·공백·0x0A)만,
        가나·1수준 한자 2자↑ · «잡음 한자»(2수준) 비율 낮음. 확인한 잡음은 SKIP 에.
  ★제자리: 원래 바이트 안(한글·전각 2B, 반각 1B, \n=RT 2B), 남으면 빌더가 공백/NUL 로 채움
  python tools/extract3.py [--list]
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from extract import lead, decode, DISC, SYS_FILES

FILES = ['0.BIN', 'SCR.BIN'] + [f for f in SYS_FILES if f != '0.BIN']
TOKEN = re.compile(rb'NM[0-9A-Z]{4}|MK[0-9]|RT|EP|PC')
SKIP = set()            # (파일, 시작) — 잡음으로 확인된 것
# 0.BIN 은 코드·표 사이라 잡음이 많다 — 눈으로 확인한 진짜 글만(시작 오프셋). 0x30F33 의 «ﾔ»(0xD4) = 앞 포인터 꼬리 → 0x30F34 부터
ALLOW0 = {0x4970, 0x4A4C, 0x4B7C, 0x8840, 0x92EC, 0x94A4, 0x1F8E4, 0x1F924, 0x1F944, 0x30F34,
          0x31198, 0x311C4, 0x311FC, 0x31258, 0x31288, 0x31314, 0x31700, 0x31A78, 0x31AB0, 0x31AF0, 0x31B34, 0x31BC0,
          0x31FBC, 0x321D8, 0x32678, 0x326BC, 0x32904}


def jis_ku(b1, b2):
    if b1 >= 0xE0:
        b1 -= 0x40
    return (b1 - 0x81) * 2 + 1 + (1 if b2 >= 0x9F else 0)


def body_ok(b):
    """몸통 검사 → (ok, 좋은 글자 수, 2수준 한자 수)"""
    p, good, bad = 0, 0, 0
    while p < len(b):
        c = b[p]
        if lead(c):
            if p + 1 >= len(b) or not (0x40 <= b[p + 1] <= 0xFC and b[p + 1] != 0x7F):
                return False, 0, 0
            ku = jis_ku(c, b[p + 1])
            if ku in (4, 5) or 16 <= ku <= 47:
                good += 1
            elif ku >= 48:
                bad += 1
            p += 2
        elif 0xA1 <= c <= 0xDF:
            good += 1; p += 1
        else:
            m = TOKEN.match(b, p)
            if m:
                p = m.end(); continue
            if 0x30 <= c <= 0x39 or c in (0x20, 0x0A):
                p += 1; continue
            return False, 0, 0
    return True, good, bad


def units(d, cov):
    out, i, n = [], 0, len(d)
    while i < n:
        j = d.find(b'\0', i)
        if j < 0:
            j = n
        # 덩어리 [i, j) 안에서 «마지막으로 텍스트가 아닌 바이트» 뒤부터가 후보(앞쪽 코드·표 바이트 떼기)
        a = i
        k = j
        while k > i:
            # 뒤에서부터 몸통이 유효한 가장 긴 접미사 찾기
            k -= 1
        best = None
        for s in range(i, j):
            if cov[s]:
                continue
            c = d[s]
            if not (lead(c) or 0xA1 <= c <= 0xDF):
                continue
            if s > i and lead(d[s - 1]) and s - 2 >= i and body_ok(d[s - 2:j])[0]:
                continue                                           # 2바이트 글자 중간
            if any(cov[s:j]):
                break
            ok, good, bad = body_ok(d[s:j])
            if ok:
                best = (s, good, bad); break
        if best:
            s, good, bad = best
            t = decode2(d[s:j])
            plain = re.sub(r'\{[^}]*\}', '', t).replace(chr(92) + 'n', '')
            if good >= 2 and bad * 3 <= good and not re.search(r'[A-Za-z]', plain):
                out.append((s, j))
        i = j + 1
    return out


def decode2(b):
    """extract.decode + NM 4자 토큰(NMR 이 아닌 것 → {NM:xxxx})"""
    parts, p = [], 0
    for m in re.finditer(rb'NM(?!R)[0-9A-Z]{4}', b):
        parts.append(decode(b[p:m.start()])); parts.append('{NM:%s}' % m.group(0)[2:].decode()); p = m.end()
    parts.append(decode(b[p:]))
    return ''.join(parts)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    occ = [o for o in json.load(open(os.path.join(ROOT, 'work', 'extract.json'), encoding='utf-8')) if not o['id'].startswith('D')]
    found = []
    for f in FILES:
        p = os.path.join(DISC, f)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read(); cov = bytearray(len(d))
        for o in occ:
            if o['file'] == f:
                cov[o['start']:o['end']] = b'\1' * (o['end'] - o['start'])
        U = units(d, cov)
        if f == '0.BIN':
            U = [(a + 1, e) if a == 0x30F33 else (a, e) for a, e in U]
            U = [(a, e) for a, e in U if a in ALLOW0]
        elif f == 'SCR.BIN':                                     # 살아 있는 스크립트 안만(묶음 마지막 스크립트 뒤 = 이전 버퍼 찌꺼기)
            import scrblk
            live = [(b, b + o[-1]) for b, n, o, e2 in scrblk.blocks(d)]
            U = [(a, e) for a, e in U if any(b <= a < lo for b, lo in live)]
            # 원문 자체가 «{» 대신 «}» 로 연 대사(«KP02081}レッカ「…PC}») — 닫는 «}» 앞까지
            a = d.find('レッカ「神の気まぐれ'.encode('cp932')); assert d[a - 1:a] == b'}'
            U.append((a, d.find(b'}', a)))
        else:
            U = []
        for a, e in U:
            if (f, a) not in SKIP:
                found.append((f, a, e, decode2(d[a:e])))
    if '--list' in sys.argv:
        for f, a, e, t in found:
            print('%s:%X\t%d\t%s' % (f, a, e - a, t))
        print(len(found)); return
    uniq, order = {}, []
    for f, a, e, t in found:
        o = {'file': f, 'start': a, 'end': e, 'kind': '보충:%dB' % (e - a), 'text': t, 'sec': 'scr' if f == 'SCR.BIN' else 'sys'}
        if t not in uniq:
            uniq[t] = []; order.append(t)
        uniq[t].append(o); occ.append(o)
    rows = []
    for k, t in enumerate(order, 1):
        rid = 'D%05d' % k
        for o in uniq[t]:
            o['id'] = rid
        u = uniq[t]
        rows.append('\t'.join([rid, '%s:%X' % (u[0]['file'], u[0]['start']), '보충:%dB' % min(o['end'] - o['start'] for o in u), str(len(u)), t, '']))
    open(os.path.join(ROOT, 'work', 'text', 'sys2.tsv'), 'w', encoding='utf-8', newline='\n').write('ID\t위치\t구분\t공유\t원문\t번역\n' + '\n'.join(rows) + '\n')
    json.dump(occ, open(os.path.join(ROOT, 'work', 'extract.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('sys2.tsv: 출현 %d · 고유 %d' % (len(found), len(order)))


if __name__ == '__main__':
    main()
