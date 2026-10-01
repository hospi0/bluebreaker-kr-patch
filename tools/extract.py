# -*- coding: utf-8 -*-
r"""원문 추출 (2026-10-01) → work/text/scr.tsv(대사) · work/text/sys.tsv(메뉴·아이템·기술·도움말) · work/extract.json(전체 출현)
  대사 = SCR.BIN(평문 SJIS + ASCII 명령, NUL 구분). 글 단위:
    · «{» … «}» 사이(SJIS 를 2바이트로 건너뛰며 찾음) — 안의 명령: RT 줄바꿈 → \n · PC 쪽 넘김 → {PC} · MK0‥3 → {MKn} · EP → {EP}
      · TC → {TC} · NMRxxx(이름 변수 추정) → {NMR:xxx} · 반각 공백 → {sp} · 그 밖 ASCII 는 {a:XX}
    · 나레이션 «TC» 뒤 ~ NUL(중괄호 밖) — 같은 토큰
  메뉴 쪽 = 0.BIN 외 작은 실행 파일: NUL 로 끝나는 SJIS 덩어리(가나·한자 2자↑, 전부 SJIS 로 풀림) — 포인터 미확정이라 «제자리 예산» 바이트를 «구분» 열에.
  열: ID · 위치 · 구분 · 공유 · 원문 · 번역  (같은 원문은 한 줄, 공유 = 나오는 자리 수)
  python tools/extract.py
"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DISC = os.path.join(ROOT, 'work', 'disc')
SYS_FILES = ['0.BIN', 'ST.BIN', 'SYS.BIN', 'MAP.BIN', 'GLD.BIN', 'END.BIN', 'KAI.BIN', 'NIKKI.BIN', 'EV101.BIN']


def lead(c):
    return 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF


def decode(b):
    """중괄호 안 / 나레이션 바이트 → 토큰 문자열"""
    out, i, n = [], 0, len(b)
    while i < n:
        c = b[i]
        if lead(c) and i + 1 < n:
            out.append(b[i:i + 2].decode('cp932', errors='replace')); i += 2
        elif 0xA1 <= c <= 0xDF:
            out.append(bytes([c]).decode('cp932')); i += 1
        elif b[i:i + 2] == b'RT':
            out.append('\\n'); i += 2
        elif b[i:i + 2] in (b'PC', b'EP', b'TC'):
            out.append('{%s}' % b[i:i + 2].decode()); i += 2
        elif b[i:i + 2] == b'MK' and i + 2 < n and 0x30 <= b[i + 2] <= 0x39:
            out.append('{MK%c}' % b[i + 2]); i += 3
        elif b[i:i + 3] == b'NMR' and i + 6 <= n:
            out.append('{NMR:%s}' % b[i + 3:i + 6].decode()); i += 6
        elif c == 0x20:
            out.append('{sp}'); i += 1
        else:
            out.append(chr(c) if 0x21 <= c < 0x7F and chr(c) not in '{}' else '{a:%02X}' % c); i += 1
    return ''.join(out)


def scr_units(d):
    """[(시작, 끝, 종류)] — 시작·끝은 본문 바이트 범위(중괄호·TC 제외)"""
    units, i, n = [], 0, len(d)
    while i < n:
        c = d[i]
        if lead(c) and i + 1 < n:
            i += 2; continue
        if c == 0x7B:                                            # {
            j = i + 1
            while j < n:
                c2 = d[j]
                if lead(c2) and j + 1 < n:
                    j += 2; continue
                if c2 in (0x7D, 0x7B, 0):
                    break
                j += 1
            if j < n and d[j] == 0x7D and any(lead(x) or 0xA1 <= x <= 0xDF for x in d[i + 1:j]):
                units.append((i + 1, j, '대사'))
            i = j; continue
        if d[i:i + 2] == b'TC' and i + 2 < n and (lead(d[i + 2]) or d[i + 2] == 0x81):
            j = i + 2
            while j < n and d[j] != 0:
                j += 2 if lead(d[j]) else 1
            units.append((i + 2, j, '나레이션')); i = j; continue
        i += 1
    return units


def sys_units(d):
    """NUL 로 끝나는 SJIS 덩어리(앞도 NUL·비SJIS 경계)"""
    units, i, n = [], 0, len(d)
    while i < n:
        j, cnt, ok = i, 0, True
        while j < n and d[j] != 0:
            c = d[j]
            if lead(c) and j + 1 < n and (0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F):
                j += 2; cnt += 1
            elif 0xA1 <= c <= 0xDF:
                j += 1; cnt += 1
            elif 0x20 <= c < 0x7F or c == 0x0A:                   # ASCII(명령 EP·NMR·MK·RT·숫자)와 0x0A(기술 설명 줄 구분)만
                j += 1
            else:
                ok = False; break
        if ok and j < n and cnt >= 2 and not (i == 0 or d[i - 1] < 0x20 or d[i - 1] >= 0xF0):
            k = i                                                # 경계가 애매(앞이 코드·데이터) → 앞쪽 ASCII 를 떼고 첫 SJIS 글자부터
            while k < j and d[k] < 0x80:
                k += 1
            if k < j and k > i:
                i = k
            else:
                ok = False
        if ok and j < n and cnt >= 2:
            try:
                t = ''.join(ch for ch in d[i:j].decode('cp932') if ord(ch) >= 0x20)
                jp = sum(1 for ch in t if '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿' or '｡' <= ch <= 'ﾟ')
                fw = sum(1 for ch in t if '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
                letters = re.sub(r'EP|NMR\w{3}|MK\d|RT|PC', '', ''.join(ch for ch in t if ch.isascii()))
                if (fw >= 2 or jp >= 3) and jp >= len(t) * 0.5 and not re.search(r'[A-Za-z]', letters):
                    units.append((i, j, t))
            except UnicodeDecodeError:
                pass
        i = max(j, i) + 1
    return units


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    occ = []
    d = open(os.path.join(DISC, 'SCR.BIN'), 'rb').read()
    for a, e, k in scr_units(d):
        occ.append({'file': 'SCR.BIN', 'start': a, 'end': e, 'kind': k, 'text': decode(d[a:e]), 'sec': 'scr'})
    for f in SYS_FILES:
        p = os.path.join(DISC, f)
        if not os.path.exists(p):
            continue
        b = open(p, 'rb').read()
        for a, e, t in sys_units(b):
            occ.append({'file': f, 'start': a, 'end': e, 'kind': '메뉴:%dB' % (e - a), 'text': decode(b[a:e]), 'sec': 'sys'})
    out = os.path.join(ROOT, 'work', 'text'); os.makedirs(out, exist_ok=True)
    head = 'ID\t위치\t구분\t공유\t원문\t번역\n'
    for sec, pre, name in (('scr', 'B', 'scr.tsv'), ('sys', 'S', 'sys.tsv')):
        uniq, order = {}, []
        for o in occ:
            if o['sec'] != sec:
                continue
            if o['text'] not in uniq:
                uniq[o['text']] = []; order.append(o['text'])
            uniq[o['text']].append(o)
        rows = []
        for k, t in enumerate(order, 1):
            os_ = uniq[t]; rid = '%s%05d' % (pre, k)
            for x in os_:
                x['id'] = rid
            kind = os_[0]['kind'] if sec == 'scr' else '메뉴:%dB' % min(x['end'] - x['start'] for x in os_)
            if sec == 'sys' and len(t) <= 4 and not re.search('[぀-ヿｦ-ﾟ]', t):
                kind = '잡음?:%dB' % min(x['end'] - x['start'] for x in os_)      # 가나 없는 짧은 한자 조각(대개 표 데이터) — 뜻 안 되면 비움
            rows.append('\t'.join([rid, '%s:%X' % (os_[0]['file'], os_[0]['start']), kind, str(len(os_)), t, '']))
        open(os.path.join(out, name), 'w', encoding='utf-8', newline='\n').write(head + '\n'.join(rows) + '\n')
        chars = sum(len(re.sub(r'\{[^}]*\}|\\n', '', t)) for t in order)
        print('%s: 출현 %d · 고유 %d · 글자 %d' % (name, sum(len(v) for v in uniq.values()), len(order), chars))
    json.dump(occ, open(os.path.join(ROOT, 'work', 'extract.json'), 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
