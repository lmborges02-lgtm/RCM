"""Persistent local session segments. Never changes OpenKore or game state."""
import json
import sqlite3
from contextlib import contextmanager


def nonnegative(value):
    return type(value) is int and value >= 0


def item_counts(items):
    counts = {}
    for item in items if isinstance(items, list) else []:
        if (isinstance(item, list) and len(item) >= 4 and nonnegative(item[3])
                and nonnegative(item[2]) and all(isinstance(v, str) for v in item[:2])):
            key = str(item[3])
            counts[key] = counts.get(key, 0) + item[2]
    return counts


def since_baseline(sample, baseline):
    row = dict(sample)
    items = []
    remaining = dict(baseline.get('items', {}))
    for item in sample.get('items', []):
        if not isinstance(item, list) or len(item) < 4 or not nonnegative(item[2]) or not nonnegative(item[3]):
            continue
        key = str(item[3])
        count = min(item[2], remaining.get(key, 0))
        remaining[key] = max(0, remaining.get(key, 0) - count)
        if item[2] > count:
            items.append([*item[:2], item[2] - count, item[3]])
    row['items'] = items
    gains = sample.get('gains')
    row['gains'] = max(0, gains - baseline.get('gains', 0)) if nonnegative(gains) else 0
    row['started_at'] = baseline['start']
    return row


def baseline_for(sample):
    return {'start': sample['updated_at'], 'items': item_counts(sample.get('items')),
            'gains': sample.get('gains', 0) if nonnegative(sample.get('gains')) else 0}


class SessionHistory:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY, source TEXT NOT NULL, profile TEXT NOT NULL,
                character TEXT NOT NULL, token TEXT NOT NULL, start INTEGER NOT NULL,
                last INTEGER NOT NULL, closed TEXT, baseline TEXT NOT NULL,
                payload TEXT NOT NULL, loot INTEGER NOT NULL DEFAULT 0,
                units INTEGER NOT NULL DEFAULT 0, priced INTEGER NOT NULL DEFAULT 0)''')
            db.execute('CREATE INDEX IF NOT EXISTS by_profile ON sessions(source, profile, character, id)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def totals(row, value_items):
        rows = value_items(row.get('items', []))
        return (sum(qty * unit for _, _, qty, unit, _ in rows if unit is not None),
                sum(qty for _, _, qty, _, _ in rows),
                sum(qty for _, _, qty, unit, _ in rows if unit is not None))

    def observe(self, source, profile, sample, value_items):
        if (sample.get('state') != 'online' or not isinstance(sample.get('session'), str)
                or not sample['session'] or not nonnegative(sample.get('updated_at'))
                or not nonnegative(sample.get('started_at'))):
            return None
        name = sample.get('name') or profile
        token, stamp = sample['session'], sample['updated_at']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT * FROM sessions WHERE source=? AND profile=? AND closed IS NULL ORDER BY id DESC LIMIT 1',
                                 (source, profile)).fetchone()
            if current and stamp < current['last']:
                return since_baseline(json.loads(current['payload']), json.loads(current['baseline']))
            if current and (current['token'] != token or current['character'] != name or stamp-current['last'] > 30):
                db.execute('UPDATE sessions SET closed=? WHERE id=?',
                           ('Reconexão' if current['token'] != token else 'Intervalo sem sinal', current['id']))
                current = None
            if current:
                baseline = json.loads(current['baseline'])
            else:
                seen = db.execute('SELECT 1 FROM sessions WHERE source=? AND profile=? AND token=? LIMIT 1',
                                  (source, profile, token)).fetchone()
                baseline = baseline_for(sample) if seen else {'start': min(stamp, sample['started_at']), 'items': {}, 'gains': 0}
            segment = since_baseline(sample, baseline)
            loot, units, priced = self.totals(segment, value_items)
            if current:
                db.execute('UPDATE sessions SET last=?, payload=?, loot=?, units=?, priced=? WHERE id=?',
                           (stamp, json.dumps(sample), loot, units, priced, current['id']))
            else:
                db.execute('INSERT INTO sessions(source,profile,character,token,start,last,baseline,payload,loot,units,priced) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           (source, profile, name, token, baseline['start'], stamp, json.dumps(baseline), json.dumps(sample), loot, units, priced))
            return segment

    def reset(self, source, profile, sample, value_items):
        if self.observe(source, profile, sample, value_items) is None:
            return False
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT * FROM sessions WHERE source=? AND profile=? AND closed IS NULL ORDER BY id DESC LIMIT 1',
                                 (source, profile)).fetchone()
            if not current:
                return False
            # A repeated click on the same sample must not overwrite an archive.
            base = baseline_for(sample)
            if current['last'] == current['start'] and json.loads(current['baseline']) == base:
                return False
            db.execute("UPDATE sessions SET closed='Reset manual' WHERE id=?", (current['id'],))
            db.execute('INSERT INTO sessions(source,profile,character,token,start,last,baseline,payload) VALUES(?,?,?,?,?,?,?,?)',
                       (source, profile, current['character'], sample['session'], base['start'], base['start'],
                        json.dumps(base), json.dumps(sample)))
        return True

    def close_missing(self, source, online_profiles, reason='Sem sinal / desconectado'):
        with self.connect() as db:
            active = db.execute('SELECT id,profile FROM sessions WHERE source=? AND closed IS NULL', (source,)).fetchall()
            for row in active:
                if row['profile'] not in online_profiles:
                    db.execute('UPDATE sessions SET closed=? WHERE id=?', (reason, row['id']))

    def rows(self, source, profile, character):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                'SELECT * FROM sessions WHERE source=? AND profile=? AND character=? ORDER BY id DESC',
                (source, profile, character))]

    def known_profiles(self, source):
        with self.connect() as db:
            return [(r['profile'], r['character']) for r in db.execute(
                'SELECT profile,character FROM sessions WHERE source=? GROUP BY profile HAVING id=MAX(id)', (source,))]

    def summary(self, source, profile, character):
        rows = self.rows(source, profile, character)
        seconds = sum(max(0, r['last']-r['start']) for r in rows)
        loot = sum(r['loot'] for r in rows)
        units = sum(r['units'] for r in rows)
        priced = sum(r['priced'] for r in rows)
        return {'sessions': len(rows), 'seconds': seconds, 'loot': loot, 'priced': priced, 'units': units,
                'rate': round(loot*3600/seconds) if seconds else None}
