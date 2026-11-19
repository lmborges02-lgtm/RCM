"""Local, read-only GordoKore telemetry and NPC valuation."""
import json
import os
import sqlite3
import time
from queue import Empty, SimpleQueue
from threading import Thread
from pathlib import Path
from tkinter import Canvas, PhotoImage, TclError, filedialog, ttk

from kafra_map import load_map, marker
from kafra_sprite import load_sprite, sprite_query
from kafra_sessions import SessionHistory


def read_json(path, limit=250_000):
    try:
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) <= limit:
            result = json.loads(raw)
            if isinstance(result, dict):
                return result
    except (OSError, ValueError):
        pass
    return {}


def integer(value):
    return type(value) is int and 0 <= value <= 10**12


def merge_quotes(store, samples):
    for sample in samples:
        quotes = sample.get('quotes')
        if not isinstance(quotes, dict):
            continue
        for key, quote in quotes.items():
            if (key.isascii() and key.isdecimal() and len(key) <= 10
                    and isinstance(quote, list) and len(quote) == 2
                    and all(integer(v) for v in quote)
                    and quote[1] <= sample['updated_at'] + 5
                    and quote[1] >= store.get(key, [0, -1])[1]):
                store[key] = quote


def valuation(items, reference, quotes):
    rows = []
    for item in items if isinstance(items, list) else []:
        if (not isinstance(item, list) or len(item) < 3
                or not all(isinstance(v, str) for v in item[:2]) or not integer(item[2])):
            continue
        name, kind, qty = item[:3]
        key = str(item[3]) if len(item) > 3 and integer(item[3]) else ''
        confirmed = quotes.get(key)
        base = confirmed[0] if confirmed is not None else reference.get(key)
        unit = base * 124 // 100 if integer(base) else None
        rows.append((name, kind, qty, unit, 'NPC confirmado' if confirmed is not None
                     else 'rAthena' if unit is not None else 'Sem cotação'))
    return rows


def fmt(n):
    return format(n, ',d').replace(',', '.') if integer(n) else '—'


class KafraTab(ttk.Frame):
    def __init__(self, parent, base):
        super().__init__(parent, padding=16, style='Surface.TFrame')
        self.base = base
        self.preferences = base / 'kafra-local.json'
        self.logs = None
        self.quotes = {}
        self.reference = read_json(base / 'data' / 'npc-renewal.json')
        self.samples = {}
        self.segments = {}
        self.session_error = ''
        try:
            self.history = SessionHistory(base / 'kafra-sessions.sqlite3')
        except (OSError, sqlite3.Error):
            self.history = None
            self.session_error = ' · Histórico indisponível: não foi possível abrir o banco local.'
        self.profile_labels = {}
        self.output_error = ''
        self.map_cache = base / 'map-cache'
        self.map_results = SimpleQueue()
        self.map_pending = None
        self.map_picture = None
        self.map_image_key = None
        self.map_retry = {}
        self.sprite_results = SimpleQueue()
        self.sprite_pending = None
        self.sprite_key = None
        self.sprite_picture = None
        self.sprite_retry = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        header = ttk.Frame(self, style='Surface.TFrame')
        header.grid(row=0, column=0, columnspan=3, sticky='ew')
        ttk.Label(header, text='Kafra Watch', style='Section.TLabel').pack(side='left')
        ttk.Button(header, text='Pasta do GordoKore…', command=self.choose).pack(side='right')
        self.reset_button = ttk.Button(header, text='Resetar sessão', command=self.reset_session, state='disabled')
        self.reset_button.pack(side='right', padx=8)
        self.feed = ttk.Label(self, wraplength=850, style='SurfaceMuted.TLabel')
        self.feed.grid(row=1, column=0, columnspan=3, sticky='w', pady=5)
        controls = ttk.Frame(self, style='Surface.TFrame')
        controls.grid(row=2, column=0, columnspan=3, sticky='ew')
        ttk.Label(controls, text='Personagem', style='SurfaceMuted.TLabel').grid(row=0, column=0, sticky='w')
        self.profile = ttk.Combobox(controls, state='readonly', width=34, height=10)
        self.profile.grid(row=1, column=0, sticky='ew', padx=(0, 15))
        self.profile.bind('<<ComboboxSelected>>', lambda _: self.render())
        ttk.Label(controls, text='Mostrar na lista', style='SurfaceMuted.TLabel').grid(row=0, column=1, sticky='w')
        self.loot_filter = ttk.Combobox(controls, state='readonly', width=18,
                                        values=('Todas as coletas', 'Só itens', 'Só cartas', 'Sem cotação'))
        self.loot_filter.current(0)
        self.loot_filter.grid(row=1, column=1, sticky='ew', padx=(0, 15))
        self.loot_filter.bind('<<ComboboxSelected>>', lambda _: self.render())
        self.detail = ttk.Label(controls, wraplength=380, justify='left', style='SurfaceMuted.TLabel')
        self.detail.grid(row=0, column=2, rowspan=2, sticky='w')
        controls.columnconfigure(2, weight=1)
        self.map = Canvas(self, width=272, height=272, background='#173639', highlightthickness=0)
        self.map.grid(row=3, column=2, rowspan=2, sticky='n', padx=(8, 0))
        self.portrait = Canvas(self, width=156, height=222, background='#E7F0F2', highlightthickness=0)
        self.portrait.grid(row=3, column=1, rowspan=2, sticky='n', padx=(12, 0))
        self.metrics = ttk.Label(self, font=('Segoe UI', 11, 'bold'), wraplength=475, style='Surface.TLabel')
        self.metrics.grid(row=3, column=0, sticky='w', pady=10)
        pane = ttk.Frame(self)
        pane.grid(row=4, column=0, sticky='nsew')
        self.session_tabs = ttk.Notebook(pane)
        self.session_tabs.pack(fill='both', expand=True)
        self.session_tabs.enable_traversal()
        loot_panel = ttk.Frame(self.session_tabs)
        history_panel = ttk.Frame(self.session_tabs)
        self.session_tabs.add(loot_panel, text='Coletas atuais')
        self.session_tabs.add(history_panel, text='Histórico de sessões')
        self.history_summary = ttk.Label(history_panel, wraplength=470, style='SurfaceMuted.TLabel')
        self.history_summary.pack(anchor='w', padx=8, pady=8)
        history_list = ttk.Frame(history_panel)
        history_list.pack(fill='both', expand=True)
        self.history_table = ttk.Treeview(history_list, columns=('date', 'duration', 'loot', 'rate', 'coverage', 'state'),
                                         show='headings', height=6)
        for key, title, width in zip(('date', 'duration', 'loot', 'rate', 'coverage', 'state'),
                                     ('Início', 'Duração', 'Loot NPC', 'Zeny/h', 'Cotados', 'Encerramento'),
                                     (135, 85, 100, 100, 75, 165)):
            self.history_table.heading(key, text=title)
            self.history_table.column(key, width=width, minwidth=60)
        hs = ttk.Scrollbar(history_list, orient='vertical', command=self.history_table.yview)
        hs.pack(side='right', fill='y')
        hx = ttk.Scrollbar(history_list, orient='horizontal', command=self.history_table.xview)
        hx.pack(side='bottom', fill='x')
        self.history_table.configure(yscrollcommand=hs.set, xscrollcommand=hx.set)
        self.history_table.pack(fill='both', expand=True)
        columns = ('name', 'kind', 'qty', 'unit', 'total', 'source')
        self.table = ttk.Treeview(loot_panel, columns=columns, show='headings', height=7)
        for col, title, width in zip(columns, ('Item', 'Tipo', 'Qtd.', 'NPC / un.', 'Total NPC', 'Preço-base'), (170, 66, 48, 85, 91, 120)):
            self.table.heading(col, text=title)
            self.table.column(col, width=width, minwidth=45, stretch=col == 'name')
        scroll = ttk.Scrollbar(loot_panel, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        hscroll = ttk.Scrollbar(loot_panel, orient='horizontal', command=self.table.xview)
        self.table.configure(xscrollcommand=hscroll.set)
        hscroll.pack(side='bottom', fill='x')
        self.table.pack(fill='both', expand=True)
        ttk.Label(self, text='Superfaturar 10 (+24%) · Valor hipotético de venda das entradas no inventário. Não representa saldo nem lucro líquido.',
                  wraplength=850).grid(row=5, column=0, columnspan=3, sticky='w', pady=(7, 0))
        saved = read_json(self.preferences).get('logs')
        if isinstance(saved, str) and saved:
            self.set_logs(Path(saved))
        self.after(50, self.poll)

    def set_logs(self, path):
        self.logs = path
        self.quotes = {}
        self.samples.clear()
        self.segments.clear()
        saved = read_json(self.preferences)
        if saved.get('logs') == str(path):
            merge_quotes(self.quotes, [{'quotes': saved.get('quotes'), 'updated_at': int(time.time())}])

    def save(self):
        tmp = self.preferences.with_suffix('.tmp')
        tmp.write_text(json.dumps({'logs': str(self.logs), 'quotes': self.quotes}), encoding='utf-8')
        tmp.replace(self.preferences)

    def choose(self):
        folder = filedialog.askdirectory(parent=self, title='Pasta do GordoKore (ou a subpasta logs)')
        if folder:
            path = Path(folder)
            self.set_logs(path / 'logs' if (path / 'logs').is_dir() else path)
            try:
                self.save()
                self.output_error = ''
            except OSError:
                self.output_error = ' · Não foi possível salvar as preferências.'
            self.refresh()

    def poll(self):
        try:
            self.refresh()
        finally:
            self.after(3000, self.poll)

    def refresh(self):
        now = int(time.time())
        grouped = {}
        original = self.quotes.copy()
        if self.logs:
            for path in self.logs.glob('kafra-watch-*.json'):
                data = read_json(path)
                key, stamp = data.get('profile'), data.get('updated_at')
                if isinstance(key, str) and key and integer(stamp) and -5 <= now - stamp <= 30:
                    grouped.setdefault(key, []).append(data)
            for key, rows in grouped.items():
                if len({r.get('pid') for r in rows if integer(r.get('pid'))}) > 1:
                    self.samples[key] = {'state': 'Profile duplicado', 'name': self.samples.get(key, {}).get('name')}
                    continue
                row = max(rows, key=lambda r: r['updated_at'])
                if not row.get('name') and self.samples.get(key, {}).get('name'):
                    row = dict(row, name=self.samples[key]['name'])
                merge_quotes(self.quotes, [row])
                self.samples[key] = row
        for key in self.samples.keys() - grouped.keys():
            self.samples[key] = {'state': 'Sem sinal', 'name': self.samples[key].get('name')}
        if self.quotes != original:
            try:
                self.save()
                self.output_error = ''
            except OSError:
                self.output_error = ' · Não foi possível salvar as cotações.'
        if self.history and self.logs:
            try:
                for key, name in self.history.known_profiles(self.source_id()):
                    self.samples.setdefault(key, {'state': 'Sem sinal', 'name': name})
            except (OSError, sqlite3.Error):
                pass
        selected = self.profile_labels.get(self.profile.get())
        self.profile_labels = {}
        for key, sample in sorted(self.samples.items()):
            name = sample.get('name')
            label = f'{name} · {key}' if name and name != key else key
            self.profile_labels[label] = key
        options = tuple(self.profile_labels)
        if tuple(self.profile['values']) != options:
            self.profile['values'] = options
        self.profile.configure(state='readonly' if options else 'disabled')
        label = next((label for label, key in self.profile_labels.items() if key == selected),
                     options[0] if options else '')
        if self.profile.get() != label:
            self.profile.set(label)
        self.segments.clear()
        if self.history and self.logs:
            try:
                online = set()
                for key, sample in self.samples.items():
                    segment = self.history.observe(self.source_id(), key, sample, self.value_items)
                    if segment is not None:
                        online.add(key)
                        self.segments[key] = segment
                self.history.close_missing(self.source_id(), online)
                self.session_error = ''
            except (OSError, sqlite3.Error):
                self.session_error = ' · Falha ao salvar histórico; reset indisponível.'
        self.feed.configure(text=(f'{len(grouped)} profile(s) com sinal · {self.logs}' if self.logs else
                                  'Escolha a pasta do GordoKore e carregue o plugin kafra_watch em um profile.') + self.output_error + self.session_error)
        self.render()

    def source_id(self):
        return os.path.normcase(str(self.logs.resolve())) if self.logs else ''

    def value_items(self, items):
        return valuation(items, self.reference, self.quotes)

    def reset_session(self):
        # Re-read the latest file so items already recorded before the click are not counted twice.
        self.refresh()
        key = self.profile_labels.get(self.profile.get())
        sample = self.samples.get(key, {})
        if not self.history or self.session_error or sample.get('state') != 'online':
            return
        try:
            self.history.reset(self.source_id(), key, sample, self.value_items)
            self.refresh()
        except (OSError, sqlite3.Error):
            self.session_error = ' · Reset não salvo. Confira o acesso ao banco de sessões.'
            self.reset_button.configure(state='disabled')
            self.feed.configure(text=self.session_error)

    def render_history(self, key, name):
        self.history_table.delete(*self.history_table.get_children())
        if not self.history or not key or not self.logs:
            self.history_summary.configure(text=self.session_error or 'Histórico salvo localmente a partir desta atualização.')
            return
        try:
            rows = self.history.rows(self.source_id(), key, name)
            totals = self.history.summary(self.source_id(), key, name)
            if not rows:
                self.history_summary.configure(text='Ainda não há sessões registradas para este personagem.')
            else:
                self.history_summary.configure(text=f"{totals['sessions']} sessões · Média histórica: {fmt(totals['rate'])} z/h\n"
                                                f"{fmt(totals['loot'])} z / {totals['seconds']//3600}h {totals['seconds']%3600//60:02d}min"
                                                f" · {totals['priced']}/{totals['units']} unidades cotadas · inclui sessão atual")
            for r in rows:
                seconds = max(0, r['last'] - r['start'])
                self.history_table.insert('', 'end', values=(
                    time.strftime('%d/%m %H:%M', time.localtime(r['start'])),
                    f'{seconds//3600}h {seconds%3600//60:02d}m {seconds%60:02d}s', fmt(r['loot']),
                    fmt(round(r['loot']*3600/seconds)) if seconds else '—',
                    f"{r['priced']}/{r['units']}", r['closed'] or 'Em andamento'))
        except (OSError, sqlite3.Error):
            self.history_summary.configure(text='Não foi possível consultar o histórico.')

    def render(self):
        key = self.profile_labels.get(self.profile.get())
        raw = self.samples.get(key, {})
        row = self.segments.get(key, raw)
        state = row.get('state')
        self.reset_button.configure(state='normal' if self.history and not self.session_error and key in self.segments else 'disabled')
        self.render_history(key, raw.get('name') or key)
        self.map.delete('all')
        self.draw_sprite(row.get('appearance') if state == 'online' else None, state)
        self.table.delete(*self.table.get_children())
        if state != 'online':
            self.map.create_text(136, 136, text='Sem posição ao vivo', fill='white')
            self.detail.configure(text='Offline' if state == 'offline' else state or 'Aguardando telemetria')
            self.metrics.configure(text='Sem dados de uma sessão ativa.')
            return
        x, y, w, h = (row.get(k) for k in ('x', 'y', 'width', 'height'))
        self.detail.configure(text=f"{row.get('name', '')} · {row.get('job', '')} · {row.get('map', '')} ({fmt(x)}, {fmt(y)})\n"
                              f"HP {fmt(row.get('hp'))}/{fmt(row.get('maxhp'))}   SP {fmt(row.get('sp'))}/{fmt(row.get('maxsp'))}")
        self.draw_map(row.get('map'), x, y, w, h)
        rows = valuation(row.get('items'), self.reference, self.quotes)
        total = sum(qty * unit for _, _, qty, unit, _ in rows if unit is not None)
        priced = sum(qty for _, _, qty, unit, _ in rows if unit is not None)
        units = sum(r[2] for r in rows)
        cards = sum(r[2] for r in rows if r[1] == 'Carta')
        first, last = row.get('started_at'), row.get('updated_at')
        seconds = max(0, last-first) if integer(first) and integer(last) else 0
        rate = fmt(round(total*3600/seconds)) if seconds and priced else '—'
        self.metrics.configure(text=f'Sessão: {seconds//3600}h {seconds%3600//60:02d}min  •  Loot NPC/h: {rate} z  •  '
                               f'Loot: {fmt(total) if priced else "—"} z  •  {priced}/{units} cotados ({cards} cartas)  •  '
                               f"Ganhos no saldo: {fmt(row.get('gains'))} z")
        mode = self.loot_filter.current()
        for name, kind, qty, unit, source in rows:
            if (mode == 1 and kind == 'Carta') or (mode == 2 and kind != 'Carta') or (mode == 3 and unit is not None):
                continue
            self.table.insert('', 'end', values=(name, kind, fmt(qty), fmt(unit), fmt(qty*unit) if unit is not None else '—', source))
        if not self.table.get_children():
            self.table.insert('', 'end', values=('Nenhuma coleta neste filtro',))

    def draw_sprite(self, appearance, state):
        panel = self.portrait
        panel.delete('all')
        panel.create_text(78, 20, text='VISUAL DO PERSONAGEM', fill='#274149', font=('Segoe UI', 8, 'bold'))
        query = sprite_query(appearance)
        try:
            finished, data = self.sprite_results.get_nowait()
            self.sprite_pending = None
            if data and finished == query:
                try:
                    self.sprite_picture = PhotoImage(master=self, data=data, format='png')
                    self.sprite_key = query
                except TclError:
                    self.sprite_retry[finished] = time.monotonic() + 120
            elif not data:
                self.sprite_retry[finished] = time.monotonic() + 120
        except Empty:
            pass
        if query is None:
            msg = 'Aguardando aparência.\nRecarregue o plugin.' if state == 'online' else 'Sem visual ao vivo'
        elif self.sprite_key == query:
            panel.create_image(0, 28, anchor='nw', image=self.sprite_picture)
            return
        else:
            if self.sprite_pending is None and self.sprite_retry.get(query, 0) <= time.monotonic():
                self.sprite_pending = query
                cache = self.base / 'sprite-cache'
                Thread(target=lambda: self.sprite_results.put((query, load_sprite(cache, query))), daemon=True).start()
            msg = 'Montando sprite…' if self.sprite_pending == query else 'Sprite indisponível'
        panel.create_text(78, 112, text=msg, width=138, justify='center', fill='#274149')

    def draw_map(self, name, x, y, w, h):
        if not (isinstance(name, str) and all(integer(v) for v in (w, h)) and 0 < w <= 2048 and 0 < h <= 2048):
            self.map.create_text(136, 136, text='Mapa não informado', fill='white')
            return
        key = name, w, h
        try:
            finished, data = self.map_results.get_nowait()
            self.map_pending = None
            if data and finished == key:
                try:
                    picture = PhotoImage(master=self, data=data, format='png')
                    factor = (max(w, h) + 259) // 260
                    self.map_picture = picture.subsample(factor, factor) if factor > 1 else picture
                    self.map_image_key = key
                except TclError:
                    self.map_retry[finished] = time.monotonic() + 120
            elif not data:
                self.map_retry[finished] = time.monotonic() + 120
        except Empty:
            pass
        if self.map_image_key != key:
            if self.map_pending is None and self.map_retry.get(key, 0) <= time.monotonic():
                self.map_pending = key
                Thread(target=lambda: self.map_results.put((key, load_map(self.map_cache, *key))), daemon=True).start()
            msg = 'Carregando minimapa…' if self.map_pending == key else 'Imagem do mapa indisponível'
            self.map.create_text(136, 136, text=msg, fill='white')
            return
        image = self.map_picture
        iw, ih = image.width(), image.height()
        left, top = (272-iw)/2, (272-ih)/2
        self.map.create_image(left, top, anchor='nw', image=image)
        if all(integer(v) for v in (x, y)) and 0 <= x < w and 0 <= y < h:
            px, py = marker(x, y, w, h, left, top, iw, ih)
            self.map.create_oval(px-7, py-7, px+7, py+7, fill='#152026', outline='white', width=2)
            self.map.create_oval(px-3, py-3, px+3, py+3, fill='#a4edbf', outline='')
