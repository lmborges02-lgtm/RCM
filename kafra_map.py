"""Load original Ragnarok minimaps without blocking the monitor."""
import re
import struct
from pathlib import Path
from urllib.request import urlopen

SOURCE = 'https://www.divine-pride.net/img/map/original/'
PNG = b'\x89PNG\r\n\x1a\n'
MAX_IMAGE = 2_000_000


def load_map(cache, name, width, height):
    if not re.fullmatch(r'[a-zA-Z0-9_@-]{1,64}', name):
        return None

    def valid(data):
        return (len(data) <= MAX_IMAGE and len(data) >= 33
                and data.startswith(PNG) and data[12:16] == b'IHDR'
                and struct.unpack('>II', data[16:24]) == (width, height))

    path = cache / f'{name}.png'
    try:
        with path.open('rb') as stream:
            data = stream.read(MAX_IMAGE + 1)
        if valid(data):
            return data
    except OSError:
        pass
    try:
        with urlopen(SOURCE + name, timeout=5) as response:
            data = response.read(MAX_IMAGE + 1)
        if valid(data):
            try:
                cache.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            except OSError:
                pass
            return data
    except (OSError, ValueError):
        pass
    return None


def marker(x, y, map_width, map_height, origin_x, origin_y, width, height):
    return (origin_x + (x + .5) * width / map_width,
            origin_y + (map_height - y - .5) * height / map_height)
