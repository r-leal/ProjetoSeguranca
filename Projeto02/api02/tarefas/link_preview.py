"""Busca metadados (título) de uma URL informada pelo usuário, para a
funcionalidade de preview de link na tarefa — com defesas contra SSRF
(Server-Side Request Forgery), já que é o próprio backend quem faz a
requisição de saída a partir de uma URL que não controlamos.

Sem essas defesas, um atacante poderia usar este recurso para fazer o
servidor requisitar endereços internos da rede onde a API roda (ex.:
`http://169.254.169.254/...`, o endereço de metadados de nuvem AWS/GCP/Azure,
ou `http://localhost:<porta-interna>/...`), usando o backend como proxy para
alcançar serviços que não deveriam ser expostos à internet.

Defesas aplicadas:
1. Só esquema `http`/`https` é aceito (bloqueia `file://`, `gopher://`, etc.).
2. O hostname é resolvido via DNS e **todos** os IPs retornados são
   validados como públicos antes de qualquer conexão (bloqueia loopback,
   redes privadas, link-local — que já cobre o IP de metadados de nuvem,
   169.254.169.254/16).
3. A conexão TCP real é aberta direto no IP já validado (nunca deixamos a
   biblioteca HTTP resolver o hostname de novo no momento de conectar) —
   isso fecha a janela de **DNS rebinding**: sem essa técnica, seria
   possível validar um IP público e, no instante da conexão real (uma
   segunda resolução DNS), o DNS já responder com um IP interno diferente.
4. Redirecionamentos (`3xx`) são seguidos manualmente, com a mesma validação
   completa reaplicada a cada hop, até um limite — um servidor externo
   "confiável" poderia redirecionar para um endereço interno.
5. Timeout de conexão/leitura curto e limite de bytes lidos — evita que o
   recurso seja usado para prender conexões ou baixar respostas enormes.
"""

import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit

TIMEOUT_SEGUNDOS = 3
MAX_BYTES_RESPOSTA = 200_000
MAX_REDIRECIONAMENTOS = 3

_TITLE_RE = re.compile(rb'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)


class LinkPreviewError(Exception):
    """Levantado quando a URL é inválida, aponta para um host não permitido,
    ou a requisição falha/é bloqueada por qualquer uma das defesas acima."""


class _ConexaoHTTPPorIP(http.client.HTTPConnection):
    """HTTPConnection que conecta no IP já validado, não no hostname —
    evita uma segunda resolução DNS (e a janela de rebinding) no connect()."""

    def __init__(self, ip, hostname, port, timeout):
        super().__init__(hostname, port, timeout=timeout)
        self._ip_validado = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip_validado, self.port), self.timeout)


class _ConexaoHTTPSPorIP(http.client.HTTPSConnection):
    """Mesma ideia da acima, mas preservando SNI e validação de certificado
    pelo hostname original (``server_hostname=self.host``) — a conexão TCP
    vai para o IP validado, só o TLS "acha" que está falando com o domínio."""

    def __init__(self, ip, hostname, port, timeout, context):
        super().__init__(hostname, port, timeout=timeout, context=context)
        self._ip_validado = ip

    def connect(self):
        sock = socket.create_connection((self._ip_validado, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _resolver_ip_publico(hostname: str) -> str:
    try:
        enderecos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise LinkPreviewError('Não foi possível resolver o host.')

    ips = {info[4][0] for info in enderecos}
    if not ips:
        raise LinkPreviewError('Não foi possível resolver o host.')

    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise LinkPreviewError('Este host não pode ser consultado.')

    # Qualquer um dos IPs públicos resolvidos serve — é só esse valor que a
    # conexão real vai usar, nunca uma resolução nova.
    return next(iter(ips))


def _requisitar(url: str, redirecionamentos_restantes: int):
    partes = urlsplit(url)

    if partes.scheme not in ('http', 'https'):
        raise LinkPreviewError('Só URLs http/https são permitidas.')
    if not partes.hostname:
        raise LinkPreviewError('URL inválida.')

    ip_validado = _resolver_ip_publico(partes.hostname)
    porta = partes.port or (443 if partes.scheme == 'https' else 80)
    caminho = partes.path or '/'
    if partes.query:
        caminho += f'?{partes.query}'

    if partes.scheme == 'https':
        contexto = ssl.create_default_context()
        conexao = _ConexaoHTTPSPorIP(ip_validado, partes.hostname, porta, TIMEOUT_SEGUNDOS, contexto)
    else:
        conexao = _ConexaoHTTPPorIP(ip_validado, partes.hostname, porta, TIMEOUT_SEGUNDOS)

    try:
        conexao.putrequest('GET', caminho, skip_host=True)
        conexao.putheader('Host', partes.hostname)
        conexao.putheader('User-Agent', 'Projeto02-LinkPreview/1.0')
        conexao.putheader('Accept', 'text/html')
        conexao.endheaders()

        try:
            resposta = conexao.getresponse()
        except (TimeoutError, OSError) as erro:
            raise LinkPreviewError('Não foi possível conectar ao host.') from erro

        if resposta.status in (301, 302, 303, 307, 308):
            local = resposta.getheader('Location')
            if not local or redirecionamentos_restantes <= 0:
                raise LinkPreviewError('Redirecionamento inválido ou excessivo.')
            proxima_url = urljoin(url, local)
            conexao.close()
            return _requisitar(proxima_url, redirecionamentos_restantes - 1)

        if resposta.status != 200:
            raise LinkPreviewError(f'O host respondeu com status {resposta.status}.')

        corpo = resposta.read(MAX_BYTES_RESPOSTA)
    finally:
        conexao.close()

    return url, corpo


def buscar_preview_link(url: str) -> dict:
    """Ponto de entrada público: valida e busca ``url``, devolvendo
    ``{'url': <url final, após redirecionamentos>, 'titulo': <str>}``.

    Levanta ``LinkPreviewError`` para qualquer URL inválida, bloqueada pelas
    defesas de SSRF, ou que falhe na requisição."""
    url_final, corpo = _requisitar(url, MAX_REDIRECIONAMENTOS)

    match = _TITLE_RE.search(corpo)
    titulo = url_final
    if match:
        texto = match.group(1).decode('utf-8', errors='replace').strip()
        texto = re.sub(r'\s+', ' ', texto)
        if texto:
            titulo = texto[:200]

    return {'url': url_final, 'titulo': titulo}
