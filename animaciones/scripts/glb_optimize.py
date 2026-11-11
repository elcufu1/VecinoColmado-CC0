"""Optimiza texturas de un GLB para teléfono: PNG opacos -> JPEG (mismo tamaño o reducido).
No toca mallas, pesos, huesos, morfos ni animaciones.

Uso: python3 glb_optimize.py entrada.glb salida.glb
"""
import io
import json
import struct
import sys

from PIL import Image

# nombre de imagen -> (lado máximo, calidad JPEG)
PLAN = {
    'middleage_lightskinned_male_diffuse': (2048, 88),
    'teeth': (1024, 85),
    'brown_eye': (1024, 88),
    'tongue01_diffuse': (512, 85),
}


def read_glb(path):
    data = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF'
    off = 12
    js, binc = None, b''
    while off < total:
        ln, typ = struct.unpack('<I4s', data[off:off + 8])
        chunk = data[off + 8:off + 8 + ln]
        if typ == b'JSON':
            js = json.loads(chunk)
        elif typ == b'BIN\x00':
            binc = chunk
        off += 8 + ln
    return js, binc


def write_glb(path, js, binc):
    jb = json.dumps(js, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    jb += b' ' * ((4 - len(jb) % 4) % 4)
    binc += b'\x00' * ((4 - len(binc) % 4) % 4)
    total = 12 + 8 + len(jb) + 8 + len(binc)
    with open(path, 'wb') as fh:
        fh.write(struct.pack('<4sII', b'glTF', 2, total))
        fh.write(struct.pack('<I4s', len(jb), b'JSON'))
        fh.write(jb)
        fh.write(struct.pack('<I4s', len(binc), b'BIN\x00'))
        fh.write(binc)


def main(src, dst):
    js, binc = read_glb(src)
    views = js['bufferViews']
    payload = [binc[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']] for v in views]
    log = []
    for im in js.get('images', []):
        name = im.get('name', '')
        if name not in PLAN or 'bufferView' not in im:
            continue
        side, q = PLAN[name]
        raw = payload[im['bufferView']]
        img = Image.open(io.BytesIO(raw))
        if img.mode in ('RGBA', 'LA'):
            a = img.getchannel('A')
            if a.getextrema()[0] < 250:
                log.append((name, 'conserva PNG (alfa real)'))
                continue
        img = img.convert('RGB')
        if max(img.size) > side:
            img = img.resize((side, side * img.size[1] // img.size[0]), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, 'JPEG', quality=q, optimize=True, progressive=False)
        payload[im['bufferView']] = out.getvalue()
        im['mimeType'] = 'image/jpeg'
        log.append((name, f'{len(raw) / 1e6:.2f} MB -> {len(out.getvalue()) / 1e6:.2f} MB, {img.size[0]}px'))
    new = bytearray()
    for v, p in zip(views, payload):
        new += b'\x00' * ((4 - len(new) % 4) % 4)
        v['byteOffset'] = len(new)
        v['byteLength'] = len(p)
        new += p
    js['buffers'][0]['byteLength'] = len(new)
    write_glb(dst, js, bytes(new))
    for row in log:
        print('TEXTURA', *row)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
