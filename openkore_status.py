"""Lê somente o pequeno heartbeat do plugin, nunca o console.txt."""
import json
import math
from pathlib import Path
import time


def read_status(path, now=None):
    now = time.time() if now is None else now
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(4097)
        if len(raw) > 4096: raise ValueError()
        data = json.loads(raw)
        stamp = float(data['updated_at'])
        if not math.isfinite(stamp) or not -5 <= now - stamp <= 15:
            return {'state': 'unknown', 'recoverable': False, 'detail': 'status desatualizado'}
        if data.get('version') != 1 or data.get('state') not in ('online', 'offline', 'unknown'):
            raise ValueError()
        return {'state': data['state'], 'recoverable': data.get('recoverable') is True,
                'detail': 'estado informado pelo OpenKore'}
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return {'state': 'unknown', 'recoverable': False, 'detail': 'arquivo ausente ou inválido'}
