"""生成秘匣的 PNG / ICO 图标，仅依赖 Python 标准库。"""

import math
import os
import struct
import zlib

SS = 4
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src-tauri", "icons")


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def inside_rrect(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    dx = x - cx
    dy = y - cy
    return dx * dx + dy * dy <= r * r


def render(size):
    s = size * SS
    buf = bytearray(s * s * 4)

    icon_r = 0.22 * s
    body_x0, body_x1 = 0.300 * s, 0.700 * s
    body_y0, body_y1 = 0.505 * s, 0.800 * s
    body_r = 0.055 * s
    ring_cx, ring_cy = 0.500 * s, 0.485 * s
    ring_ro, ring_ri = 0.155 * s, 0.098 * s
    key_cx, key_cy, key_r = 0.500 * s, 0.625 * s, 0.032 * s
    key_x0, key_x1 = 0.486 * s, 0.514 * s
    key_y1 = 0.735 * s

    for y in range(s):
        t = y / max(1, s - 1)
        base = lerp((201, 92, 38), (150, 58, 10), t)
        for x in range(s):
            i = (y * s + x) * 4
            if not inside_rrect(x, y, 0, 0, s, s, icon_r):
                continue

            glow = math.exp(
                -(((x - 0.28 * s) ** 2 + (y - 0.16 * s) ** 2) / (2 * (0.34 * s) ** 2))
            )
            color = tuple(min(255, round(c + 24 * glow)) for c in base)

            dx = x - ring_cx
            dy = y - ring_cy
            dist2 = dx * dx + dy * dy
            if ring_ri * ring_ri <= dist2 <= ring_ro * ring_ro:
                color = (250, 250, 255)

            if inside_rrect(x, y, body_x0, body_y0, body_x1, body_y1, body_r):
                color = (250, 250, 255)
                kdx = x - key_cx
                kdy = y - key_cy
                in_key = kdx * kdx + kdy * kdy <= key_r * key_r
                if key_x0 <= x <= key_x1 and key_cy <= y <= key_y1:
                    in_key = True
                if in_key:
                    color = (104, 36, 4)

            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]
            buf[i + 3] = 255

    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            r = g = b = a = 0
            for sy in range(SS):
                for sx in range(SS):
                    j = ((y * SS + sy) * s + (x * SS + sx)) * 4
                    r += buf[j]
                    g += buf[j + 1]
                    b += buf[j + 2]
                    a += buf[j + 3]
            k = SS * SS
            o = (y * size + x) * 4
            out[o] = r // k
            out[o + 1] = g // k
            out[o + 2] = b // k
            out[o + 3] = a // k
    return bytes(out)


def png_bytes(size, rgba):
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def ico_bytes(images):
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = bytearray()
    payload = bytearray()
    offset = 6 + 16 * len(images)

    for size, rgba in images:
        xor_rows = bytearray()
        for y in range(size - 1, -1, -1):
            for x in range(size):
                i = (y * size + x) * 4
                xor_rows += bytes((rgba[i + 2], rgba[i + 1], rgba[i], rgba[i + 3]))
        mask_row = ((size + 31) // 32) * 4
        mask = b"\x00" * (mask_row * size)
        xor_size = size * size * 4
        bmp = (
            struct.pack(
                "<IiiHHIIiiII",
                40,
                size,
                size * 2,
                1,
                32,
                0,
                xor_size + len(mask),
                0,
                0,
                0,
                0,
            )
            + bytes(xor_rows)
            + mask
        )
        dim = 0 if size == 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(bmp), offset)
        payload += bmp
        offset += len(bmp)

    return bytes(header + entries + payload)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rendered = {}

    for size in (256, 128, 32):
        rgba = render(size)
        rendered[size] = rgba
        with open(os.path.join(OUT_DIR, f"{size}x{size}.png"), "wb") as fh:
            fh.write(png_bytes(size, rgba))

    with open(os.path.join(OUT_DIR, "icon.ico"), "wb") as fh:
        fh.write(ico_bytes([(256, rendered[256]), (128, rendered[128]), (32, rendered[32])]))

    print("icons written to", os.path.abspath(OUT_DIR))


if __name__ == "__main__":
    main()
