"""Monitor local para Windows. Sem dependências externas."""
import base64
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE = Path(__file__).resolve().parent
CONFIG = BASE / 'config.json'
HIDDEN = 0x08000000
VERSION = '0.1.0'


def load_config(path=CONFIG):
    """Uma instalação nova começa vazia; uma configuração existente é preservada."""
    if not path.exists():
        default = {'clients': [], 'restart_interval': 60}
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding='utf-8')
        return default
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or not isinstance(config.get('clients'), list):
        raise ValueError('config.json inválido: a propriedade clients precisa ser uma lista.')
    return config


def powershell(script):
    script = "$ErrorActionPreference='Stop'; " + script
    encoded = base64.b64encode(script.encode('utf-16le')).decode()
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                             '-EncodedCommand', encoded], capture_output=True,
                            timeout=20, creationflags=HIDDEN)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:250])
    return json.loads(result.stdout.decode('utf-8-sig') or 'null')


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def resolve(path):
    if not Path(path).is_file():
        raise ValueError('Arquivo não encontrado.')
    if Path(path).suffix.lower() == '.exe':
        return {'Target': str(Path(path).resolve()), 'Arguments': ''}
    if Path(path).suffix.lower() != '.lnk':
        raise ValueError('Selecione um atalho .lnk ou um executável .exe.')
    data = powershell("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
                      "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + quote(path) +
                      "); @{Target=$s.TargetPath; Arguments=$s.Arguments} | ConvertTo-Json -Compress")
    if Path(data['Target']).suffix.lower() != '.exe' or not Path(data['Target']).is_file():
        raise ValueError('Nesta versão, o atalho precisa apontar diretamente para um .exe existente.')
    return data


def processes():
    data = powershell("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
                      "@(Get-CimInstance Win32_Process | "
                      "Select-Object ProcessId,Name,ExecutablePath,CommandLine,CreationDate) | ConvertTo-Json -Compress")
    return data or []


def argv(command):
    count = C.c_int()
    shell = C.WinDLL('shell32', use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [W.LPCWSTR, C.POINTER(C.c_int)]
    shell.CommandLineToArgvW.restype = C.POINTER(W.LPWSTR)
    ptr = shell.CommandLineToArgvW(command, C.byref(count))
    if not ptr:
        raise ValueError('Linha de comando indisponível.')
    try:
        return [ptr[i] for i in range(count.value)]
    finally:
        kernel = C.WinDLL('kernel32')
        kernel.LocalFree.argtypes = [C.c_void_p]
        kernel.LocalFree(C.cast(ptr, C.c_void_p))


def matches(proc, target):
    return (bool(proc.get('ExecutablePath')) and os.path.normcase(proc['ExecutablePath']) == os.path.normcase(target['Target'])
            and bool(proc.get('CommandLine'))
            and argv(proc['CommandLine'])[1:] == argv('dummy.exe ' + target['Arguments'])[1:])


def is_crash_title(title):
    return title.strip().casefold() in ('gravity(tm) error handler', 'gravity error handler')


def crash_processes():
    """Somente títulos de janelas visíveis; não envia comandos ao jogo."""
    user = C.WinDLL('user32', use_last_error=True)
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    result = set()
    def enum(hwnd, _):
        if user.IsWindowVisible(hwnd):
            text = C.create_unicode_buffer(512)
            user.GetWindowTextW(hwnd, text, len(text))
            if is_crash_title(text.value):
                pid = W.DWORD(); user.GetWindowThreadProcessId(hwnd, C.byref(pid))
                result.add(pid.value)
        return True
    if not user.EnumWindows(callback_type(enum), 0):
        raise RuntimeError('Não foi possível verificar as janelas de erro.')
    return result


def capture(pid, roi):
    """PrintWindow isolado em subprocesso: nunca bloqueia o monitor principal."""
    user, gdi = C.WinDLL('user32'), C.WinDLL('gdi32')
    user.SetProcessDPIAware()
    user.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.IsIconic.argtypes = [W.HWND]
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.GetDC.argtypes = [W.HWND]; user.GetDC.restype = W.HDC
    user.ReleaseDC.argtypes = [W.HWND, W.HDC]
    user.PrintWindow.argtypes = [W.HWND, W.HDC, W.UINT]
    gdi.CreateCompatibleDC.argtypes = [W.HDC]; gdi.CreateCompatibleDC.restype = W.HDC
    gdi.CreateCompatibleBitmap.argtypes = [W.HDC, C.c_int, C.c_int]; gdi.CreateCompatibleBitmap.restype = W.HBITMAP
    gdi.SelectObject.argtypes = [W.HDC, W.HGDIOBJ]; gdi.SelectObject.restype = W.HGDIOBJ
    gdi.DeleteObject.argtypes = [W.HGDIOBJ]; gdi.DeleteDC.argtypes = [W.HDC]
    gdi.GetDIBits.argtypes = [W.HDC, W.HBITMAP, W.UINT, W.UINT, C.c_void_p, C.c_void_p, W.UINT]
    handles = []
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def enum(hwnd, _):
        window_pid = W.DWORD()
        user.GetWindowThreadProcessId(hwnd, C.byref(window_pid))
        rect = W.RECT(); user.GetClientRect(hwnd, C.byref(rect))
        if window_pid.value == pid and user.IsWindowVisible(hwnd) and rect.right > 150 and rect.bottom > 100:
            handles.append((rect.right * rect.bottom, hwnd, rect))
        return True
    user.EnumWindows(callback_type(enum), 0)
    if not handles:
        raise RuntimeError('Nenhuma janela visível do client.')
    _, hwnd, rect = max(handles, key=lambda item: item[0])
    if user.IsIconic(hwnd):
        raise RuntimeError('Janela minimizada: detecção visual suspensa.')
    width, height = rect.right, rect.bottom
    if width * height > 20000000:
        raise RuntimeError('Janela grande demais para esta captura.')
    dc = user.GetDC(hwnd); memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        if not user.PrintWindow(hwnd, memory, 3):
            raise RuntimeError('O jogo não forneceu uma captura válida.')
        gdi.SelectObject(memory, old)
        # BITMAPINFOHEADER, RGB de 32 bits, orientação de cima para baixo.
        import struct
        info = C.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, 0, 0, 0, 0, 0))
        pixels = C.create_string_buffer(width * height * 4)
        if gdi.GetDIBits(memory, bitmap, 0, height, pixels, info, 0) != height:
            raise RuntimeError('Falha ao ler a imagem.')
        raw = pixels.raw
        x, y, rw, rh = roi
        rgb = bytearray()
        for row in range(180):
            sy = min(height - 1, int((y + rh * row / 180) * height / 100))
            for col in range(320):
                sx = min(width - 1, int((x + rw * col / 320) * width / 100))
                offset = (sy * width + sx) * 4
                rgb.extend((raw[offset + 2], raw[offset + 1], raw[offset]))
        if max(rgb) < 8:
            raise RuntimeError('Captura preta: detecção visual suspensa.')
        return bytes(rgb)
    finally:
        gdi.DeleteObject(bitmap); gdi.DeleteDC(memory); user.ReleaseDC(hwnd, dc)


def read_capture(pid, roi):
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--capture',
                             str(pid), json.dumps(roi)], capture_output=True,
                            timeout=5, creationflags=HIDDEN)
    data = json.loads(result.stdout)
    if 'error' in data:
        raise RuntimeError(data['error'])
    return base64.b64decode(data['rgb'])


class Activity:
    def __init__(self):
        self.previous = None
        self.last_change = time.monotonic()
        self.armed = False

    def observe(self, rgb, now):
        if self.previous is None:
            self.last_change = now
        if self.previous is not None:
            changed = sum(abs(a - b) > 8 for a, b in zip(rgb, self.previous)) / len(rgb)
            if changed > 0.001:
                self.last_change = now
                self.armed = True
        self.previous = rgb
        return now - self.last_change


class App:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        saved_config = load_config()
        self.items = saved_config['clients']
        self.settings = {'restart_interval': saved_config.get('restart_interval', 60)}
        root.title('Ragnarok • Guardião dos clients')
        root.geometry(f"{min(1160, root.winfo_screenwidth() - 80)}x{min(900, root.winfo_screenheight() - 100)}")
        root.minsize(min(1000, root.winfo_screenwidth() - 60), min(690, root.winfo_screenheight() - 60))
        self.colors = {'paper': '#F3EDDF', 'surface': '#FFFCF4', 'ink': '#263E41',
                       'muted': '#58645C', 'gold': '#CDA86B', 'line': '#C5B99E', 'teal': '#234C50'}
        self.apply_theme()
        root.configure(background=self.colors['paper'])
        header = tk.Frame(root, bg='#19383D', padx=24, pady=18); header.pack(fill='x')
        crest = tk.Canvas(header, width=86, height=86, bg='#19383D', highlightthickness=0)
        crest.pack(side='left', padx=(0, 18)); self.draw_crest(crest)
        title = tk.Frame(header, bg='#19383D'); title.pack(side='left')
        tk.Label(title, text='R A G N A R O K', font=('Georgia', 12, 'bold'), bg='#19383D', fg='#E6C78C').pack(anchor='w')
        tk.Label(title, text='Guardião dos clients', font=('Georgia', 26, 'bold'), bg='#19383D', fg='#FFF8E8').pack(anchor='w', pady=3)
        tk.Label(title, text='Seus aventureiros, sob vigilância.', font=('Segoe UI', 11), bg='#19383D', fg='#C5D8D4').pack(anchor='w')
        self.phase = tk.Label(header, text='MONITOR PAUSADO', font=('Segoe UI', 10, 'bold'),
                              bg='#2C4A4D', fg='#E9D5AB', padx=16, pady=10)
        self.phase.pack(side='right')
        tk.Frame(root, bg='#CDA86B', height=3).pack(fill='x')
        frame = ttk.Frame(root, padding=(24, 16)); frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        overview = ttk.Frame(frame); overview.grid(row=0, column=0, sticky='ew', pady=(0, 16))
        self.counts = {}
        for key, label in [('total', 'Clients cadastrados'), ('active', 'Ativos na lista'), ('visual', 'Com detecção visual')]:
            group = ttk.Frame(overview); group.pack(side='left', padx=(0, 40))
            value = ttk.Label(group, text='0', font=('Georgia', 22, 'bold'), foreground='#234C50')
            value.pack(side='left', padx=(0, 10)); ttk.Label(group, text=label, style='Muted.TLabel').pack(side='left')
            self.counts[key] = value
        self.is_admin = bool(C.WinDLL('shell32').IsUserAnAdmin())
        ttk.Label(overview, text='Acesso: administrador' if self.is_admin else 'Acesso: normal',
                  style='Muted.TLabel').pack(side='right')
        self.tabs = ttk.Notebook(frame); self.tabs.grid(row=1, column=0, sticky='nsew')
        clients_panel = ttk.Frame(self.tabs, style='Surface.TFrame', padding=16)
        history_panel = ttk.Frame(self.tabs, style='Surface.TFrame', padding=16)
        self.tabs.add(clients_panel, text='  Clients  '); self.tabs.add(history_panel, text='  Diário de eventos  ')
        clients_panel.columnconfigure(0, weight=1); clients_panel.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(clients_panel, style='Surface.TFrame'); toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 14))
        self.edit_buttons = []
        for label, action in [('Adicionar arquivo', self.add), ('Editar selecionado', self.edit),
                              ('Ativar / desativar', self.toggle), ('Remover', self.remove),
                              ('Testar captura', self.preview)]:
            button = ttk.Button(toolbar, text=label, command=action, cursor='hand2'); button.pack(side='left', padx=(0, 8))
            self.edit_buttons.append(button)
        table_frame = ttk.Frame(clients_panel, style='Surface.TFrame'); table_frame.grid(row=1, column=0, sticky='nsew')
        self.table = ttk.Treeview(table_frame, columns=('name', 'active', 'visual', 'status'), show='headings', selectmode='browse')
        for key, title, width, minimum in [('name', 'AVENTUREIRO / CLIENT', 285, 220), ('active', 'ATIVO', 85, 80),
                                          ('visual', 'CONGELAMENTO', 175, 160), ('status', 'ESTADO DO CLIENT', 360, 230)]:
            self.table.heading(key, text=title); self.table.column(key, width=width, minwidth=minimum, stretch=key in ('name', 'status'))
        self.table.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        scroll.pack(side='right', fill='y'); self.table.configure(yscrollcommand=scroll.set)
        for tag, bg, fg in [('even', '#FFFCF4', '#263E41'), ('odd', '#F4EEDC', '#263E41'),
                            ('healthy', '#EBF4ED', '#244E3D'), ('warning', '#FFF0D4', '#744809'),
                            ('inactive', '#EEEAE1', '#59635C')]:
            self.table.tag_configure(tag, background=bg, foreground=fg)
        self.table.bind('<<TreeviewSelect>>', self.show_selection)
        self.table.bind('<Double-1>', lambda _: self.edit() if not self.worker or not self.worker.is_alive() else None)
        self.selection_info = ttk.Label(clients_panel, text='Selecione um client para consultar seu atalho e tempo de tolerância.',
                                         style='SurfaceMuted.TLabel', wraplength=940)
        self.selection_info.grid(row=2, column=0, sticky='w', pady=(12, 0))
        ttk.Label(history_panel, text='Diário de eventos', style='Section.TLabel').pack(anchor='w')
        ttk.Label(history_panel, text='Falhas e reinícios desta sessão. O histórico completo é salvo em monitor.log.',
                  style='SurfaceMuted.TLabel').pack(anchor='w', pady=(4, 12))
        log_frame = ttk.Frame(history_panel, style='Surface.TFrame'); log_frame.pack(fill='both', expand=True)
        self.log = tk.Text(log_frame, height=5, font=('Consolas', 11), state='disabled', wrap='word',
                           background='#F5EFDF', foreground='#263E41', relief='flat', padx=12, pady=12,
                           highlightthickness=1, highlightbackground='#C5B99E', selectbackground='#234C50', selectforeground='white')
        self.log.pack(side='left', fill='both', expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log.yview); log_scroll.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=log_scroll.set)
        actions = ttk.Frame(frame); actions.grid(row=2, column=0, sticky='ew', pady=(18, 8))
        self.start_button = ttk.Button(actions, text='Iniciar monitoramento', command=self.start, style='Primary.TButton', cursor='hand2')
        self.start_button.pack(side='left')
        self.pause_button = ttk.Button(actions, text='Pausar', command=self.pause, state='disabled', cursor='hand2')
        self.pause_button.pack(side='left', padx=8)
        self.summary = ttk.Label(actions, text='Pausado. Nenhum client será encerrado.', wraplength=610, style='Muted.TLabel')
        self.summary.pack(side='left', padx=12)
        settings_row = ttk.Frame(frame); settings_row.grid(row=3, column=0, sticky='ew', pady=(0, 8))
        ttk.Label(settings_row, text='Intervalo entre reinícios:').pack(side='left', padx=(0, 8))
        self.restart_interval = tk.StringVar(value=str(self.settings['restart_interval']))
        interval_input = ttk.Spinbox(settings_row, from_=15, to=3600, increment=15,
                                    textvariable=self.restart_interval, width=6)
        interval_input.pack(side='left')
        self.edit_buttons.append(interval_input)
        ttk.Label(settings_row, text='segundos  •  Um client por vez.', style='Muted.TLabel').pack(side='left', padx=8)
        ttk.Label(frame, text='Para detectar congelamento, valide uma região com movimento contínuo em “Testar captura”.',
                  style='Muted.TLabel', wraplength=940).grid(row=4, column=0, sticky='w')
        if not self.is_admin:
            ttk.Label(frame, text='Parâmetros sem acesso? Reabra usando “Iniciar como administrador.cmd”.',
                      style='Muted.TLabel').grid(row=5, column=0, sticky='w', pady=(4, 0))
        self.refresh(); root.after(150, self.drain)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def apply_theme(self):
        c = self.colors
        style = ttk.Style(); style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10), background=c['paper'], foreground=c['ink'])
        style.configure('TFrame', background=c['paper'])
        style.configure('Surface.TFrame', background=c['surface'])
        style.configure('TLabel', background=c['paper'], foreground=c['ink'])
        style.configure('Muted.TLabel', foreground=c['muted'])
        style.configure('SurfaceMuted.TLabel', background=c['surface'], foreground=c['muted'])
        style.configure('Section.TLabel', font=('Georgia', 18, 'bold'), background=c['surface'])
        style.configure('TButton', background='#EEE3CA', foreground=c['ink'], bordercolor='#A89773',
                         lightcolor='#FFF8E6', darkcolor='#A89773', padding=(12, 9), focuscolor=c['teal'])
        style.map('TButton', background=[('disabled', '#E9E3D7'), ('pressed', '#DDCCAA'), ('active', '#F8EBCF')],
                  foreground=[('disabled', '#787A70')])
        style.configure('Primary.TButton', background=c['teal'], foreground='#FFF8E8', bordercolor=c['teal'],
                         lightcolor=c['teal'], darkcolor=c['teal'], font=('Segoe UI', 10, 'bold'), focuscolor='#E6C78C')
        style.map('Primary.TButton', background=[('disabled', '#E9E3D7'), ('pressed', '#163B40'), ('active', '#326269')],
                  foreground=[('disabled', '#787A70'), ('!disabled', '#FFF8E8')])
        style.configure('Treeview', background=c['surface'], fieldbackground=c['surface'], foreground=c['ink'],
                         rowheight=46, bordercolor=c['line'], lightcolor=c['line'], darkcolor=c['line'], font=('Segoe UI', 11))
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'), background='#E8DCC2', foreground='#384C43',
                         padding=(10, 10), bordercolor=c['line'], relief='flat')
        style.map('Treeview', background=[('selected', c['teal'])], foreground=[('selected', '#FFF8E8')])
        style.map('Treeview.Heading', background=[('active', '#E8DCC2')])
        style.configure('TNotebook', background=c['paper'], bordercolor=c['line'], tabmargins=(0, 0, 0, 0))
        style.configure('TNotebook.Tab', padding=(14, 9), background='#E5D9BF', foreground='#46564D', font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', c['surface'])], foreground=[('selected', c['ink'])])
        style.configure('TEntry', fieldbackground=c['surface'], bordercolor=c['line'], padding=7)
        style.map('TEntry', bordercolor=[('focus', c['teal'])])
        style.configure('TCheckbutton', padding=6)
        style.configure('Vertical.TScrollbar', background='#D5C5A5', troughcolor='#F3EDDF', bordercolor=c['line'], arrowsize=14)

    @staticmethod
    def draw_crest(canvas):
        # Emblema desenhado localmente: asas e uma criatura rosada inspirada nos Porings.
        canvas.create_polygon(43, 3, 80, 20, 76, 61, 43, 83, 10, 61, 6, 20, fill='#234C50', outline='#CDA86B', width=2)
        for side in (-1, 1):
            canvas.create_polygon(43 + side * 12, 42, 43 + side * 34, 24,
                                  43 + side * 27, 43, 43 + side * 18, 51,
                                  fill='#F1E6CC', outline='#CDA86B')
        canvas.create_oval(23, 32, 63, 66, fill='#ECADB6', outline='#FFE3E6', width=2)
        canvas.create_oval(29, 37, 39, 42, fill='#FFD7DD', outline='')
        canvas.create_oval(34, 47, 37, 53, fill='#493D43', outline='')
        canvas.create_oval(49, 47, 52, 53, fill='#493D43', outline='')
        canvas.create_arc(39, 50, 47, 58, start=180, extent=180, style='arc', outline='#6C4250', width=2)
        canvas.create_polygon(43, 13, 47, 19, 43, 25, 39, 19, fill='#E6C78C', outline='')

    def show_selection(self, _=None):
        selection = self.table.selection()
        if not selection: return
        item = self.items[int(selection[0])]
        self.selection_info.configure(text=f"{item['path']}\nTolerância visual: {item['timeout']} s  •  Região: {', '.join(map(str, item['roi']))}%")

    def row_tag(self, i, status):
        if not self.items[i]['enabled']: return 'inactive'
        if any(word in status.lower() for word in ('erro', 'suspenso', 'bloquead', 'sem acesso', 'limite', 'inválida', 'indisponível')): return 'warning'
        if status.startswith('Aberto'): return 'healthy'
        return 'even' if i % 2 == 0 else 'odd'

    def refresh(self):
        self.table.delete(*self.table.get_children())
        for i, item in enumerate(self.items):
            self.table.insert('', 'end', iid=str(i), values=(item['name'], 'Sim' if item['enabled'] else 'Não',
                              'Habilitado' if item['visual'] else 'Desativado', 'Pausado'), tags=(self.row_tag(i, 'Pausado'),))
        self.counts['total'].configure(text=str(len(self.items)))
        self.counts['active'].configure(text=str(sum(item['enabled'] for item in self.items)))
        self.counts['visual'].configure(text=str(sum(item['enabled'] and item['visual'] for item in self.items)))
        self.selection_info.configure(text='Selecione um client para consultar seu atalho e tempo de tolerância.')

    def save(self):
        temporary = CONFIG.with_suffix('.tmp')
        temporary.write_text(json.dumps({'clients': self.items, **self.settings}, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(CONFIG); self.refresh()

    def selected(self):
        ids = self.table.selection()
        if not ids:
            messagebox.showinfo('Seleção', 'Selecione um client na lista.'); return None
        return int(ids[0])

    def add(self):
        path = filedialog.askopenfilename(title='Adicionar client', initialdir=str(Path.home() / 'Desktop'),
                                         filetypes=[('Atalhos e executáveis', '*.lnk *.exe')])
        if not path: return
        if any(os.path.normcase(item['path']) == os.path.normcase(path) for item in self.items):
            messagebox.showerror('Arquivo repetido', 'Esse arquivo já está cadastrado.'); return
        try: resolve(path)
        except Exception as exc: messagebox.showerror('Arquivo inválido', str(exc)); return
        self.items.append({'name': Path(path).stem, 'path': path, 'enabled': True,
                           'visual': False, 'timeout': 120, 'roi': [0, 0, 100, 100]})
        self.save()

    def toggle(self):
        i = self.selected()
        if i is not None: self.items[i]['enabled'] = not self.items[i]['enabled']; self.save()

    def remove(self):
        i = self.selected()
        if i is not None and messagebox.askyesno('Remover', 'Remover da lista? O arquivo original será preservado.'):
            del self.items[i]; self.save()

    def edit(self):
        i = self.selected()
        if i is None: return
        item = self.items[i]; dialog = tk.Toplevel(self.root); dialog.title('Configurar client')
        dialog.configure(background=self.colors['paper'])
        dialog.transient(self.root); dialog.grab_set()
        dialog.bind('<Escape>', lambda _: dialog.destroy())
        panel = ttk.Frame(dialog, padding=20); panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='Configurar aventureiro', font=('Georgia', 19, 'bold')).grid(row=0, column=0, sticky='w', pady=(0, 12))
        variables = {}
        for row, (key, label, value) in enumerate([
                ('name', 'Nome', item['name']), ('path', 'Caminho do atalho ou .exe', item['path']),
                ('timeout', 'Tempo sem movimento (segundos, mínimo 30)', item['timeout']),
                ('roi', 'Região em %: esquerda, topo, largura, altura', ', '.join(map(str, item['roi'])))]):
            ttk.Label(panel, text=label).grid(row=row * 2 + 1, column=0, sticky='w', pady=(8, 2))
            variables[key] = tk.StringVar(value=str(value))
            ttk.Entry(panel, textvariable=variables[key], width=65).grid(row=row * 2 + 2, column=0, sticky='ew')
        visual = tk.BooleanVar(value=item['visual'])
        ttk.Checkbutton(panel, text='Detectar congelamento: confirme antes a captura e o movimento contínuo', variable=visual).grid(row=9, column=0, pady=12)
        def commit():
            try:
                path = variables['path'].get().strip().strip('"'); resolve(path)
                timeout = int(variables['timeout'].get()); roi = [float(v.strip()) for v in variables['roi'].get().split(',')]
                import math
                if len(roi) != 4 or timeout < 30 or any(not math.isfinite(v) or v < 0 for v in roi) or roi[2] <= 0 or roi[3] <= 0 or roi[0] + roi[2] > 100 or roi[1] + roi[3] > 100:
                    raise ValueError('Tempo mínimo de 30 s. A região deve ficar dentro de 0–100%, com largura e altura positivas.')
                if any(j != i and os.path.normcase(c['path']) == os.path.normcase(path) for j, c in enumerate(self.items)):
                    raise ValueError('Esse arquivo já está cadastrado.')
                item.update(name=variables['name'].get().strip() or Path(path).stem, path=path,
                            timeout=timeout, roi=roi, visual=visual.get())
                self.save(); dialog.destroy()
            except Exception as exc: messagebox.showerror('Configuração inválida', str(exc), parent=dialog)
        dialog_actions = ttk.Frame(panel); dialog_actions.grid(row=10, column=0, sticky='e')
        ttk.Button(dialog_actions, text='Cancelar', command=dialog.destroy).pack(side='left', padx=8)
        ttk.Button(dialog_actions, text='Salvar configuração', command=commit, style='Primary.TButton').pack(side='left')

    def preview(self):
        i = self.selected()
        if i is None: return
        item = dict(self.items[i]); self.summary.config(text='Capturando janela…')
        def work():
            try:
                target = resolve(item['path']); found = [p for p in processes() if matches(p, target)]
                if len(found) != 1: raise RuntimeError('É preciso exatamente um processo correspondente aberto.')
                rgb = read_capture(found[0]['ProcessId'], item['roi'])
                self.events.put(('preview', item['name'], rgb))
            except Exception as exc: self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def drain(self):
        while not self.events.empty():
            event = self.events.get()
            if event[0] == 'status':
                if self.table.exists(str(event[1])):
                    self.table.set(str(event[1]), 'status', event[2])
                    self.table.item(str(event[1]), tags=(self.row_tag(event[1], event[2]),))
            elif event[0] == 'log':
                line = time.strftime('%H:%M:%S') + '  ' + event[1] + '\n'
                self.log.config(state='normal'); self.log.insert('end', line); self.log.see('end'); self.log.config(state='disabled')
                with (BASE / 'monitor.log').open('a', encoding='utf-8') as stream: stream.write(time.strftime('%Y-%m-%d ') + line)
            elif event[0] == 'error':
                messagebox.showerror('Falha', event[1]); self.summary.config(text='Pausado.')
            elif event[0] == 'preview':
                window = tk.Toplevel(self.root); window.title('Captura — ' + event[1])
                window.configure(background=self.colors['paper'])
                window.bind('<Escape>', lambda _: window.destroy())
                photo = tk.PhotoImage(data=b'P6\n320 180\n255\n' + event[2]).zoom(2, 2)
                label = ttk.Label(window, image=photo); label.image = photo; label.pack(padx=12, pady=12)
                ttk.Label(window, text='Confira a imagem. Repita o teste após alguns segundos para verificar movimento.').pack(padx=12, pady=12)
                self.summary.config(text='Captura concluída.')
            elif event[0] == 'stopped':
                self.start_button.config(state='normal'); self.pause_button.config(state='disabled')
                for button in self.edit_buttons: button.config(state='normal')
                self.summary.config(text='Pausado. Nenhum client será encerrado.')
                self.phase.configure(text='MONITOR PAUSADO', bg='#2C4A4D', fg='#E9D5AB')
        self.root.after(150, self.drain)

    def start(self):
        if self.worker and self.worker.is_alive(): return
        try:
            interval = int(self.restart_interval.get())
            if not 15 <= interval <= 3600: raise ValueError()
        except ValueError:
            messagebox.showerror('Intervalo inválido', 'Informe entre 15 e 3600 segundos para espaçar os reinícios.'); return
        if not any(item['enabled'] for item in self.items):
            messagebox.showinfo('Lista vazia', 'Ative ou adicione pelo menos um client.'); return
        self.settings['restart_interval'] = interval
        self.save()
        self.stop.clear(); self.start_button.config(state='disabled'); self.pause_button.config(state='normal')
        for button in self.edit_buttons: button.config(state='disabled')
        self.summary.config(text='Monitorando. Fechar o monitor interrompe as verificações.')
        self.phase.configure(text='MONITORANDO', bg='#31584B', fg='#E3F1D9')
        self.worker = threading.Thread(target=self.run, daemon=True); self.worker.start()

    def pause(self):
        self.stop.set(); self.summary.config(text='Pausando…'); self.pause_button.config(state='disabled')
        self.phase.configure(text='PAUSANDO…', bg='#2C4A4D', fg='#E9D5AB')

    def close(self):
        self.stop.set(); self.root.destroy()

    def run(self):
        states = {}; targets = {}
        next_restart = 0
        def status(i, value): self.events.put(('status', i, value))
        try:
            for i, item in enumerate(self.items):
                if not item['enabled']: continue
                try:
                    target = resolve(item['path'])
                    if any(os.path.normcase(t['Target']) == os.path.normcase(target['Target']) and argv('dummy ' + t['Arguments']) == argv('dummy ' + target['Arguments']) for t in targets.values()):
                        raise ValueError('Atalhos com parâmetros idênticos: não é possível distinguir os clients.')
                    targets[i] = target
                    states[i] = {'activity': Activity(), 'identity': None, 'grace': time.monotonic() + 90,
                                 'attempts': [], 'crash_seen': None}
                except Exception as exc: status(i, 'Configuração inválida'); self.events.put(('log', item['name'] + ': ' + str(exc)))
            while not self.stop.is_set():
                try:
                    inventory = processes()
                    crash_pids = crash_processes()
                except Exception as exc:
                    self.events.put(('log', 'Falha na leitura de processos: ' + str(exc)))
                    for i in states:
                        states[i]['activity'] = Activity(); status(i, 'Sem leitura de processos — suspenso')
                    self.stop.wait(5); continue
                proposals = []
                for i, state in states.items():
                    if self.stop.is_set(): break
                    item, target = self.items[i], targets[i]
                    try:
                        found = [p for p in inventory if matches(p, target)]
                        now = time.monotonic()
                        if len(found) > 1:
                            state['activity'] = Activity(); status(i, 'Mais de um processo correspondente — suspenso'); continue
                        proc = found[0] if found else None
                        if proc is None and any(str(p.get('Name', '')).lower() == Path(target['Target']).name.lower() and (not p.get('ExecutablePath') or not p.get('CommandLine')) for p in inventory):
                            state['activity'] = Activity()
                            status(i, 'Parâmetros bloqueados mesmo como admin' if self.is_admin else 'Sem acesso — abra o monitor como administrador')
                            if not state.get('access_warning'):
                                self.events.put(('log', item['name'] + ': parâmetros inacessíveis. ' +
                                                 ('Mesmo com elevação; requer outro método de identificação.' if self.is_admin else
                                                  'Feche o monitor e abra Iniciar como administrador.cmd.')))
                            state['access_warning'] = True
                            continue
                        state['access_warning'] = False
                        identity = (proc['ProcessId'], proc['CreationDate']) if proc else None
                        if identity != state['identity']:
                            state['identity'] = identity; state['activity'] = Activity(); state['grace'] = now + 90
                            state['crash_seen'] = None
                        state['attempts'] = [t for t in state['attempts'] if now - t < 900]
                        if len(state['attempts']) >= 3:
                            status(i, 'Limite: 3 reinícios em 15 min'); continue
                        reason = None
                        if not proc:
                            if now < state['grace']: status(i, 'Aguardando abertura (até 90 s)'); continue
                            reason = 'processo fechado'
                        elif proc['ProcessId'] in crash_pids:
                            if state['crash_seen'] is None:
                                state['crash_seen'] = now
                                self.events.put(('log', item['name'] + ': janela Gravity Error Handler detectada.'))
                            status(i, 'Falha do Ragnarok — confirmando janela de erro')
                            if now - state['crash_seen'] >= 10:
                                reason = 'janela Gravity Error Handler'
                            else:
                                continue
                        elif not item['visual']:
                            state['crash_seen'] = None
                            status(i, 'Aberto — detecção visual desativada'); continue
                        elif now < state['grace']:
                            state['crash_seen'] = None
                            status(i, 'Aguardando carregamento (90 s)'); continue
                        else:
                            state['crash_seen'] = None
                            try: rgb = read_capture(proc['ProcessId'], item['roi'])
                            except Exception as exc:
                                state['activity'] = Activity(); status(i, 'Captura indisponível — suspenso');
                                if not state.get('capture_error'): self.events.put(('log', item['name'] + ': ' + str(exc)))
                                state['capture_error'] = True; continue
                            state['capture_error'] = False
                            elapsed = state['activity'].observe(rgb, time.monotonic())
                            if not state['activity'].armed:
                                status(i, 'Aguardando movimento para validar captura'); continue
                            status(i, f'Aberto — sem mudança há {int(elapsed)} s')
                            if elapsed >= item['timeout']: reason = 'imagem congelada'
                        if reason:
                            proposals.append((i, proc, reason))
                    except Exception as exc:
                        state['activity'] = Activity(); status(i, 'Erro — verifique o histórico')
                        state['grace'] = time.monotonic() + 90
                        self.events.put(('log', item['name'] + ': ' + str(exc)))
                # Só uma tentativa por ciclo; pendências são reavaliadas nos ciclos seguintes.
                # Alterna a prioridade pelos clientes há mais tempo sem tentativa.
                proposals.sort(key=lambda p: (states[p[0]]['attempts'][-1] if states[p[0]]['attempts'] else 0, p[0]))
                for i, proc, reason in proposals:
                    if self.stop.is_set(): break
                    if time.monotonic() < next_restart:
                        status(i, f'Na fila — próximo reinício em {max(1, int(next_restart - time.monotonic()))} s'); continue
                    state, item, target = states[i], self.items[i], targets[i]
                    try:
                        fresh_inventory = processes()
                        if self.stop.is_set(): break
                        if proc:
                            fresh = [p for p in fresh_inventory if p['ProcessId'] == proc['ProcessId'] and p['CreationDate'] == proc['CreationDate'] and matches(p, target)]
                            if not fresh: continue
                            # Confirma que o diálogo continua presente no processo identificado.
                            if reason == 'janela Gravity Error Handler' and proc['ProcessId'] not in crash_processes():
                                state['crash_seen'] = None; continue
                        else:
                            if any(matches(p, target) for p in fresh_inventory): continue
                            if any(str(p.get('Name', '')).lower() == Path(target['Target']).name.lower() and
                                   (not p.get('ExecutablePath') or not p.get('CommandLine')) for p in fresh_inventory):
                                status(i, 'Sem acesso — reinício suspenso'); continue
                        if self.stop.is_set(): break
                        state['attempts'].append(time.monotonic())
                        next_restart = time.monotonic() + self.settings['restart_interval']
                        self.events.put(('log', item['name'] + ': iniciando reinício por ' + reason))
                        if proc: terminate_checked(proc)
                        if self.stop.is_set(): break
                        os.startfile(item['path'])
                        next_restart = time.monotonic() + self.settings['restart_interval']
                        state['grace'] = time.monotonic() + 90; state['identity'] = None
                        state['activity'] = Activity(); state['crash_seen'] = None
                        status(i, 'Reaberto — aguardando carregamento')
                        self.events.put(('log', item['name'] + ': reaberto por ' + reason))
                    except Exception as exc:
                        state['activity'] = Activity(); state['grace'] = time.monotonic() + 90
                        status(i, 'Erro no reinício — verifique o histórico')
                        self.events.put(('log', item['name'] + ': ' + str(exc)))
                self.stop.wait(5)
        finally: self.events.put(('stopped',))


def terminate_checked(proc):
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]; kernel.OpenProcess.restype = W.HANDLE
    kernel.GetProcessTimes.argtypes = [W.HANDLE] + [C.POINTER(W.FILETIME)] * 4
    kernel.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
    kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    handle = kernel.OpenProcess(0x1000 | 0x0001 | 0x100000, False, proc['ProcessId'])
    if not handle: raise RuntimeError('Sem permissão para encerrar o client.')
    try:
        created, exited, kernel_time, user_time = (W.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, C.byref(created), C.byref(exited), C.byref(kernel_time), C.byref(user_time)):
            raise RuntimeError('Não foi possível verificar a identidade do processo.')
        ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
        # PowerShell serializa DateTime como /Date(milissegundos)/.
        import re
        match = re.search(r'/Date\((\d+)', str(proc['CreationDate']))
        if not match or abs((ticks - 116444736000000000) // 10000 - int(match.group(1))) > 1:
            raise RuntimeError('A identidade do processo mudou; reinício cancelado.')
        if not kernel.TerminateProcess(handle, 1): raise RuntimeError('Falha ao encerrar o client.')
        if kernel.WaitForSingleObject(handle, 5000) != 0: raise RuntimeError('Client ainda encerrando; nova abertura adiada.')
    finally: kernel.CloseHandle(handle)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--capture':
        try: print(json.dumps({'rgb': base64.b64encode(capture(int(sys.argv[2]), json.loads(sys.argv[3]))).decode()}))
        except Exception as exc: print(json.dumps({'error': str(exc)}))
    else:
        # Mutex evita dois monitores reiniciando os mesmos clients simultaneamente.
        kernel = C.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [C.c_void_p, W.BOOL, W.LPCWSTR]; kernel.CreateMutexW.restype = W.HANDLE
        mutex = kernel.CreateMutexW(None, False, 'Local\\RagnarokClientMonitor')
        already_running = C.get_last_error() == 183
        C.WinDLL('user32').SetProcessDPIAware()
        root = tk.Tk()
        if already_running:
            root.withdraw(); messagebox.showinfo('Monitor já aberto', 'Já existe um monitor aberto nesta sessão.'); root.destroy()
        else:
            try: App(root); root.mainloop()
            except Exception as exc: messagebox.showerror('Falha ao iniciar', str(exc))
