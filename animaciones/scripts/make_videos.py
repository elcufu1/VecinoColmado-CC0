"""Monta los MP4 (H.264, 1280x720, 24 fps) a partir de los cuadros renderizados por final.py render.

Uso: python3 make_videos.py reporte_verificacion.json frames_dir videos_dir
"""
import json
import math
import os
import subprocess
import sys

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MIN_LOOP_S = 4.0
HOLD_S = 0.5
SLOW_BELOW_S = 3.0


def esc(t):
    return t.replace(':', r'\:').replace("'", r"\'")


def label(text, y='h-th-24', size=26):
    return (f"drawtext=fontfile={FONT}:text='{esc(text)}':x=24:y={y}:fontsize={size}:fontcolor=white:"
            f"box=1:boxcolor=black@0.45:boxborderw=10")


def run(cmd):
    print(' '.join(cmd))
    subprocess.run(cmd, check=True)


ENC = ['-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', '24',
       '-movflags', '+faststart']


def anim_video(t, frames_dir, out):
    d = os.path.join(frames_dir, t['name'])
    n = len(os.listdir(os.path.join(d, 'main')))
    reps = max(1, math.ceil(MIN_LOOP_S * 24 / n)) if t['loop'] else 1
    title = f"{t['name']}  ·  {t['frames']} cuadros ({t['duracion_s']:.2f} s){'  ·  bucle' if t['loop'] else ''}"
    inp = ['-framerate', '24', '-stream_loop', str(reps - 1), '-i', os.path.join(d, 'main', '%05d.png')]
    filt = '[0:v]'
    tail = '' if t['loop'] else f',tpad=stop_mode=clone:stop_duration={HOLD_S}'
    if os.path.isdir(os.path.join(d, 'inset')):
        inp += ['-framerate', '24', '-stream_loop', str(reps - 1), '-i', os.path.join(d, 'inset', '%05d.png')]
        filt = ('[1:v]pad=iw+6:ih+6:3:3:color=white[ins];'
                '[0:v][ins]overlay=W-w-20:H-h-20:eof_action=repeat' + tail)
    else:
        filt = '[0:v]' + (tail.lstrip(',') or 'null')
    if not t['loop'] and n / 24.0 < SLOW_BELOW_S:
        first = n / 24.0 + HOLD_S
        filt += (f",split[a][b];[b]setpts=2*PTS[bs];[a][bs]concat=n=2:v=1,"
                 + label(title, y='24') + f":enable='lt(t,{first:.3f})',"
                 + label(title + '  ·  cámara lenta ×0.5', y='24') + f":enable='gte(t,{first:.3f})'[v]")
    else:
        filt += ',' + label(title, y='24') + '[v]'
    run(['ffmpeg', '-y', '-loglevel', 'error', *inp, '-filter_complex', filt, '-map', '[v]', *ENC, out])


def full_body(t, frames_dir, out):
    """Prueba de rango con primeros planos (manos y cara) insertados en sus tramos."""
    d = os.path.join(frames_dir, t['name'])
    mk = {n: f - t['start'] for f, n in t['markers']}
    inp = ['-framerate', '24', '-i', os.path.join(d, 'main', '%05d.png'),
           '-framerate', '24', '-i', os.path.join(d, 'manos', '%05d.png'),
           '-framerate', '24', '-i', os.path.join(d, 'cara', '%05d.png')]
    a, c = mk['Dedos'] / 24.0, mk['Cara'] / 24.0
    na = len(os.listdir(os.path.join(d, 'manos'))) / 24.0
    nc = len(os.listdir(os.path.join(d, 'cara'))) / 24.0
    segs = sorted(mk.items(), key=lambda kv: kv[1])
    texts = []
    for i, (nm, f) in enumerate(segs):
        f1 = segs[i + 1][1] if i + 1 < len(segs) else t['frames'] + 1
        texts.append(label(f"Prueba de rango · {nm.replace('_', ' ')}", y='24')
                     + f":enable='between(t,{f / 24.0:.3f},{f1 / 24.0 - 0.001:.3f})'")
    filt = (f"[1:v]scale=640:360,setpts=PTS-STARTPTS+{a:.4f}/TB,pad=iw+6:ih+6:3:3:color=white[m];"
            f"[2:v]scale=640:360,setpts=PTS-STARTPTS+{c:.4f}/TB,pad=iw+6:ih+6:3:3:color=white[c];"
            f"[0:v][m]overlay=W-w-16:H-h-16:eof_action=pass:enable='between(t,{a:.3f},{a + na:.3f})'[x];"
            f"[x][c]overlay=W-w-16:H-h-16:eof_action=pass:enable='between(t,{c:.3f},{c + nc:.3f})',"
            + ','.join(texts) + '[v]')
    run(['ffmpeg', '-y', '-loglevel', 'error', *inp, '-filter_complex', filt, '-map', '[v]', *ENC, out])


CLOSEUPS = ('Agarrar_Ficha_Cerca', 'Colocar_Ficha_Cerca', 'Agarrar_Ficha_Lejos', 'Colocar_Ficha_Lejos',
            'Golpe_Ficha', 'Sostener_Fichas')


def closeup_segment(t, frames_dir, out):
    """Primer plano de la mano (a media velocidad) con la vista completa pequeña en la esquina."""
    d = os.path.join(frames_dir, t['name'])
    inp = ['-framerate', '12', '-i', os.path.join(d, 'primer_plano', '%05d.png'),
           '-framerate', '12', '-i', os.path.join(d, 'main', '%05d.png')]
    filt = ('[1:v]scale=400:225,pad=iw+6:ih+6:3:3:color=white[m];[0:v][m]overlay=W-w-16:H-h-16,'
            'tpad=stop_mode=clone:stop_duration=0.6,'
            + label(f"Primer plano · {t['name'].replace('_', ' ')} · ficha parada · ×0.5", y='24') + '[v]')
    run(['ffmpeg', '-y', '-loglevel', 'error', *inp, '-filter_complex', filt, '-map', '[v]', *ENC, out])


def main(meta, frames_dir, out_dir):
    tl = json.load(open(meta))['timeline']
    os.makedirs(out_dir, exist_ok=True)
    only = set(sys.argv[4:])
    for t in tl:
        if only and t['name'] not in only:
            continue
        if not os.path.isdir(os.path.join(frames_dir, t['name'], 'main')):
            print('FALTAN CUADROS', t['name'])
            continue
        anim_video(t, frames_dir, os.path.join(out_dir, f"{t['name']}.mp4"))
        if t['name'] == 'Prueba_Rango_Completo':
            rng = os.path.join(frames_dir, '_rango.mp4')
            full_body(t, frames_dir, rng)
            parts = [rng]
            for c in tl:
                if c['name'] in CLOSEUPS and os.path.isdir(os.path.join(frames_dir, c['name'], 'primer_plano')):
                    pth = os.path.join(frames_dir, f"_cerca_{c['name']}.mp4")
                    closeup_segment(c, frames_dir, pth)
                    parts.append(pth)
            lst = os.path.join(frames_dir, '_lista.txt')
            with open(lst, 'w') as fh:
                fh.write(''.join(f"file '{os.path.abspath(x)}'\n" for x in parts))
            run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                 '-movflags', '+faststart', os.path.join(out_dir, 'VIDEO_TODO_EL_CUERPO.mp4')])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
