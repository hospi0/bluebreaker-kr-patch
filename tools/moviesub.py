# -*- coding: utf-8 -*-
r"""블루 브레이커 동영상 자막 굽기 (2026-10-02, 유나 리믹스 tools/moviesub.py 에서 — FILM 1.06 · cinepak 304×224 띠 2개)
  자막 표: work/text/movie_sub.tsv — 영상 · 시작 · 끝(hh:mm:ss.sss) · 원문 · 번역(«\n» = 강제 줄바꿈, 없으면 폭 넘칠 때 자동 접기) · 비고
  ★프레임 간격이 고르지 않다(STAB 정보1 = 시각, 기준 30 — 2·3 틱이 섞임) → 프레임 시각은 STAB 에서 읽는다.
  시간: 표의 [시작, 끝] — 읽을 시간(글자×0.15초 + 0.8초, 최소 1.2초)보다 짧으면 다음 자막 앞까지 늘림.
        받아쓰기 구간이 읽을 시간보다 훨씬 길면(첫 줄·빈틈 뒤) 시작이 앞당겨져 있기 쉬워 끝에서 거꾸로 잘라 냄(로그에 «✂»).
  글씨: 나눔고딕 Bold 14px 흰색 + 검은 1px 테두리, 화면 아래 가운데(줄 간격 17px), 부호 뒤 공백 1칸 삭제.
  굽기: 자막 든 키 구간만 cinepak 재굽기(tools/movenc.py) → work/kr/<영상>.CPK (원본 크기 이하, 0 채움 — 디스크 제자리)
  미리보기: work/movie/sub/<영상>_kr.mp4
  python tools/moviesub.py [영상 …] [--nopreview]   (없으면 표의 영상 전부)
"""
import glob, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import filmcpk, movenc

FFBIN = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin'
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
PX, W, H = 14, 304, 224
MAXW = W - 14
TSV = os.path.join(ROOT, 'work', 'text', 'movie_sub.tsv')
SRC = os.path.join(ROOT, 'work', 'movie', 'cpk')
WORK = os.path.join(ROOT, 'work', 'movie')
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')
HANGUL = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


def secs(t):
    h, m, s = t.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def rows():
    out = {}
    for ln in open(TSV, encoding='utf-8'):
        if ln.startswith('#') or not ln.strip():
            continue
        c = ln.rstrip('\n').split('\t')
        t = c[4]
        assert t and not HANGUL.search(t), ('번역 비었거나 가나·한자 남음', c)
        lines = [PUNCT_SP.sub(r'\1', p.strip()) for p in t.split('\\n')]
        out.setdefault(c[0], []).append((secs(c[1]), secs(c[2]), lines))
    return out


def need(lines):
    return max(sum(len(p) for p in lines) * 0.15 + 0.8, 1.2)


def events(rs, dur, log):
    ev = []
    for k, (s, e, lines) in enumerate(rs):
        nd = need(lines)
        prev_end = rs[k - 1][1] if k else None
        if e - s > max(2.5 * nd, 6) and (k == 0 or s - prev_end > 0.3 or s == prev_end):
            s2 = max(s, e - max(1.8 * nd, 4))
            log('   ✂ %.2f‥%.2f → %.2f 부터  %s' % (s, e, s2, ' / '.join(lines)))
            s = s2
        nxt = rs[k + 1][0] if k + 1 < len(rs) else dur
        end = max(e, s + nd)
        end = min(end, nxt - 0.07, dur - 0.05)
        ev.append((s, end, lines))
    return ev


def wrap(lines, F, d):
    out = []
    for ln in lines:
        if d.textlength(ln, font=F) <= MAXW:
            out.append(ln); continue
        ws = ln.split(' '); best = None
        for i in range(1, len(ws)):
            a, b = ' '.join(ws[:i]), ' '.join(ws[i:])
            la, lb = d.textlength(a, font=F), d.textlength(b, font=F)
            if la <= MAXW and lb <= MAXW and (best is None or max(la, lb) < best[0]):
                best = (max(la, lb), a, b)
        assert best, ('줄 넘침', ln)
        out += [best[1], best[2]]
    assert len(out) <= 2, ('세 줄 이상', out)
    return out


def plate(lines, F):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lines = wrap(lines, F, d)
    y = H - 13 - (len(lines) - 1) * 17
    for ln in lines:
        d.text((W / 2, y), ln, font=F, anchor='mm', fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0)); y += 17
    px = im.load()
    for yy in range(H):
        for xx in range(W):
            r, g, b, a = px[xx, yy]
            px[xx, yy] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)     # 반투명 없이(cinepak 번짐 줄임)
    return im, lines


def frames(name):
    fr = os.path.join(WORK, 'frames', name.lower())
    if not glob.glob(os.path.join(fr, 'f*.png')):
        os.makedirs(fr, exist_ok=True)
        subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', os.path.join(SRC, name + '.CPK'),
                        '-fps_mode', 'passthrough', os.path.join(fr, 'f%04d.png')], check=True)
    return fr


def times(name):
    """영상 프레임마다 (시작, 끝) 초 — STAB 정보1(기준 film['base'] 틱)"""
    film = filmcpk.read(open(os.path.join(SRC, name + '.CPK'), 'rb').read())
    v = [e for e in film['stab'] if e[2] != 0xFFFFFFFF]
    return [((e[2] & 0x7FFFFFFF) / film['base'], ((e[2] & 0x7FFFFFFF) + e[3]) / film['base']) for e in v]


def burn(name, ev, log):
    fr = frames(name)
    T = times(name)
    nf = len(glob.glob(os.path.join(fr, 'f*.png')))
    assert nf == len(T), ('프레임 수 불일치', nf, len(T))
    kr = os.path.join(fr, 'kr'); os.makedirs(kr, exist_ok=True)
    for f in glob.glob(os.path.join(kr, 'f*.png')):
        os.remove(f)
    F = ImageFont.truetype(FONT, PX); done = 0
    for a, b, lines in ev:
        pl, _ = plate(lines, F)
        for f, (t0, t1) in enumerate(T):
            if t0 < b and t1 > a and (min(t1, b) - max(t0, a)) >= 0.5 * (t1 - t0):
                p = os.path.join(kr, 'f%04d.png' % (f + 1))
                im = Image.open(p if os.path.exists(p) else os.path.join(fr, 'f%04d.png' % (f + 1))).convert('RGBA')
                im.alpha_composite(pl)
                im.convert('RGB').save(p); done += 1
    src = os.path.join(SRC, name + '.CPK')
    dst = os.path.join(ROOT, 'work', 'kr', name + '.CPK')
    size = os.path.getsize(src)
    movenc.reencode(src, fr, kr, dst, size, log=log)
    d = open(dst, 'rb').read()
    open(dst, 'wb').write(d + bytes(size - len(d)))
    log('%s 프레임 %d/%d 에 자막 → %s' % (name, done, nf, dst))


def preview(name):
    os.makedirs(os.path.join(WORK, 'sub'), exist_ok=True)
    subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', os.path.join(ROOT, 'work', 'kr', name + '.CPK'),
                    '-vf', 'scale=%d:%d:flags=neighbor' % (W * 2, H * 2), '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', os.path.join(WORK, 'sub', name + '_kr.mp4')], check=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    allr = rows()
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    names = args or sorted(allr)
    log = lambda *a: print(*a, flush=True)
    F = ImageFont.truetype(FONT, PX); d = ImageDraw.Draw(Image.new('RGB', (W, H)))
    for name in sorted(allr):                                   # 먼저 전부 폭 검사
        for _, _, lines in allr[name]:
            wrap(lines, F, d)
    for name in names:
        T = times(name)
        ev = events(allr[name], T[-1][1], log)
        log('== %s 자막 %d개' % (name, len(ev)))
        for a, b, t in ev:
            log('   %6.2f‥%6.2f  %s' % (a, b, ' / '.join(t)))
        burn(name, ev, log)
        if '--nopreview' not in sys.argv:
            preview(name)


if __name__ == '__main__':
    main()
