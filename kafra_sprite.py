"""Fetch a composited sprite using only numeric game appearance IDs."""
from hashlib import sha256
from urllib.parse import urlencode
from urllib.request import urlopen

ENDPOINT = 'https://assets.latam-tools.com.br/image?'
PNG = b'\x89PNG\r\n\x1a\n'
LIMIT = 1_000_000


def sprite_query(look):
    if not isinstance(look, dict):
        return None

    def value(key):
        v = look.get(key)
        return v if type(v) is int and 0 <= v <= 2**31-1 else None

    job, sex, head = (value(k) for k in ('job', 'sex', 'head'))
    if job is None or sex not in (0, 1) or not head:
        return None
    params = dict(job=job, gender='male' if sex else 'female', head=head,
                  action=0, frame=0, canvas='156x192+78+147')
    gears = dict.fromkeys(value(k) for k in ('low', 'mid', 'top'))
    layers = ','.join(str(v) for v in gears if v)
    if layers:
        params['headgear'] = layers
    for k in ('headPalette', 'bodyPalette', 'weapon', 'shield', 'garment'):
        v = value(k)
        if v:
            params[k] = v
    return urlencode(params)


def load_sprite(cache, query):
    path = cache / (sha256(query.encode('ascii')).hexdigest() + '.png')

    def valid(data):
        return (32 < len(data) <= LIMIT and data.startswith(PNG)
                and data[12:16] == b'IHDR'
                and data[16:24] == b'\0\0\0\x9c\0\0\0\xc0')

    try:
        with path.open('rb') as stream:
            data = stream.read(LIMIT+1)
        if valid(data):
            return data
    except OSError:
        pass
    try:
        with urlopen(ENDPOINT + query, timeout=6) as response:
            data = response.read(LIMIT+1)
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
