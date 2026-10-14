"""Entrega assíncrona de avisos; sem dependências externas."""
import json
import math
import queue
import re
import threading
from urllib import error, parse, request


def validate_webhook(url):
    url = url.strip()
    parts = parse.urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc != 'discord.com' or parts.query or parts.fragment
            or not re.fullmatch(r'/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', parts.path)):
        raise ValueError('Use a URL HTTPS de um webhook de canal do Discord, sem parâmetros extras.')
    return url


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_webhook(url, content, opener=None):
    url = validate_webhook(url)
    payload = json.dumps({'content': content[:1900], 'username': 'Guardião dos clients',
                          'allowed_mentions': {'parse': []}}, ensure_ascii=False).encode('utf-8')
    req = request.Request(url + '?wait=true', data=payload, method='POST',
                          headers={'Content-Type': 'application/json', 'User-Agent': 'RCM/0.2'})
    opener = opener or request.build_opener(NoRedirect())
    with opener.open(req, timeout=10) as response:
        response.read(1024)


class DiscordNotifier:
    def __init__(self, log):
        self.log = log
        self.url = ''
        self.enabled = False
        self.lock = threading.Lock()
        self.messages = queue.Queue(maxsize=100)
        self.stop = threading.Event()
        self.worker = threading.Thread(target=self.run, daemon=True)
        self.worker.start()

    def configure(self, enabled, url):
        url = validate_webhook(url) if url.strip() else ''
        if enabled and not url:
            raise ValueError('Preencha o webhook antes de habilitar os avisos.')
        with self.lock:
            self.enabled, self.url = bool(enabled), url

    def notify(self, content, test=False):
        if self.stop.is_set(): return False
        with self.lock:
            if not self.url or (not self.enabled and not test): return False
            job = (self.url, content, test)
        try:
            self.messages.put_nowait(job)
            return True
        except queue.Full:
            self.log('Discord: fila cheia; aviso descartado.')
            return False

    def run(self):
        while not self.stop.is_set():
            try: url, content, test = self.messages.get(timeout=0.5)
            except queue.Empty: continue
            with self.lock:
                permitted = self.url == url and (self.enabled or test)
            if not permitted: continue
            try:
                send_webhook(url, content)
                if test: self.log('Discord: mensagem de teste enviada.')
                self.stop.wait(1)
            except error.HTTPError as exc:
                if exc.code == 429:
                    # Não repete antes do Retry-After; descarta este aviso para evitar duplicação.
                    try: delay = float(json.loads(exc.read(2048)).get('retry_after', 5))
                    except (ValueError, TypeError): delay = 5
                    if not math.isfinite(delay): delay = 5
                    if delay > 300:
                        with self.lock: self.enabled = False
                        self.log('Discord: limite prolongado; salve a configuração novamente para reativar os avisos após o prazo.')
                    self.log('Discord: limite de envio atingido; aviso descartado.')
                    self.stop.wait(min(300, max(1, delay)))
                else:
                    self.log(f'Discord: falha HTTP {exc.code}. Verifique o webhook.')
            except Exception:
                # Não imprime URL, token nem exceções de rede com credenciais.
                self.log('Discord: envio falhou. Verifique conexão e webhook; o monitor continua ativo.')

    def close(self):
        self.stop.set()


def notification_state(status):
    """Apenas estados do client; jamais infere conexão do personagem."""
    if status.startswith('OpenKore — online'): return 'online no mapa, conforme informado pelo OpenKore'
    if status.startswith('OpenKore — offline'): return 'offline, conforme informado pelo OpenKore'
    if status.startswith('OpenKore — desconhecido'): return 'conexão desconhecida: status do OpenKore indisponível ou desatualizado'
    if status.startswith('Aguardando abertura'): return 'client fechado'
    if status.startswith('Falha do Ragnarok'): return 'falha do Ragnarok detectada'
    if status.startswith('Reaberto'): return 'client reaberto; conexão do personagem ainda não confirmada'
    if status.startswith('Erro no reinício'): return 'falha ao reiniciar o client'
    if status.startswith('Limite'): return 'limite de tentativas atingido'
    if status.startswith('Sem acesso') or status.startswith('Parâmetros bloqueados') or status.startswith('Sem leitura'): return 'verificação suspensa por falta de acesso'
    if status.startswith('Aberto'): return 'processo aberto; conexão do personagem ainda não confirmada'
    return None
