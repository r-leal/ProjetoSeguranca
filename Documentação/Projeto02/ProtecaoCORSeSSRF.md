# Projeto02 — Tutorial: protegendo contra CORS mal configurado e SSRF (partindo do Projeto01)

> Tutorial passo a passo, para quem **nunca programou em Python nem usou
> Django**. Mostra o que é CORS e SSRF, por que são frequentemente citados
> juntos (os dois envolvem "de onde vêm/para onde vão as requisições"),
> onde cada um se aplica **de fato** neste repositório, e — para o caso que
> não se aplica hoje (SSRF) — o que fazer no dia em que passar a se
> aplicar. Mesmo formato de [[Projeto02/ProtecaoXSSeCSRF]]: *o que* mudar,
> *onde* mudar, *por quê*.

## 0. Antes de começar: dois conceitos fáceis de confundir

- **CORS (Cross-Origin Resource Sharing)** não é, por si só, uma
  vulnerabilidade — é um **mecanismo de segurança do navegador**. Por
  padrão, JavaScript rodando numa página de `origem-a.com` **não consegue**
  ler a resposta de uma requisição para `origem-b.com` (mesmo que a
  requisição seja enviada). CORS é o conjunto de cabeçalhos HTTP
  (`Access-Control-Allow-Origin` e companhia) que o servidor usa para
  **abrir uma exceção explícita** a essa regra, dizendo "esta outra origem
  pode ler minhas respostas". O problema de segurança aparece quando esse
  mecanismo é configurado de forma **permissiva demais** (liberar
  "qualquer origem" para uma API que usa cookies, por exemplo) — é aí que
  vira vulnerabilidade.
- **SSRF (Server-Side Request Forgery)** é quando um atacante consegue
  fazer o **seu próprio servidor** enviar uma requisição HTTP para um
  destino escolhido por ele — normalmente abusando de alguma funcionalidade
  legítima que aceita uma URL como entrada (buscar uma imagem de um link,
  validar um webhook, importar dados de um link externo, gerar preview de
  link...). O servidor, ao contrário do navegador de um usuário comum, às
  vezes tem acesso de rede a lugares que o atacante não alcançaria
  diretamente de fora (serviços internos, metadata da nuvem, bancos de
  dados administrativos sem autenticação na rede interna).

A diferença chave: **CORS é sobre quem pode *ler a resposta* de uma
chamada feita pelo navegador de um usuário**; **SSRF é sobre convencer *o
seu servidor* a fazer uma chamada para onde o atacante quiser**. Um não
substitui a defesa do outro.

## 1. Parte A — CORS mal configurado

### 1.1 O que já existe neste repositório (e o que mudar)

Diferente de SSRF (seção 2), **CORS mal configurado é uma vulnerabilidade
real e presente** na evolução deste projeto — está documentada em
[[Projeto00/Vulnerabilidades]] e continua sem correção total até o
[[Projeto01]]. Vamos corrigir partindo exatamente do estado do
[[Projeto01]].

**Arquivo**: `api01/api01/settings.py`

```python
# Projeto01 (inseguro de propósito): aceita requisições de qualquer origem.
CORS_ALLOW_ALL_ORIGINS = True
```

Isso diz ao `django-cors-headers` para responder
`Access-Control-Allow-Origin: *` em toda requisição, de qualquer site da
internet. Combinado com `ALLOWED_HOSTS = ['*']`, a API aceita e responde a
requisições vindas de **qualquer origem**, sem distinção.

### 1.2 Por que "liberar tudo" é perigoso — mesmo sendo uma API JSON

Uma objeção comum: "a API só devolve JSON, não tem cookie de sessão nem
nada secreto, então liberar qualquer origem não tem problema". Isso vale
**só enquanto nenhuma rota depende de uma credencial que o navegador manda
automaticamente** (cookie). No momento em que o [[Projeto02]] introduz o
refresh token em cookie `httpOnly` (ver
[[Projeto02/SegurancaAutorizacaoAcesso]], seção 7), `CORS_ALLOW_ALL_ORIGINS
= True` se torna muito mais grave:

- Um site malicioso (`atacante.com`) poderia rodar `fetch()` contra a sua
  API `with credentials: 'include'` (o equivalente, em JS puro, a mandar
  os cookies do usuário).
- O navegador, por padrão, **recusa enviar cookies numa requisição
  cross-origin se o servidor responder `Access-Control-Allow-Origin: *`**
  — essa é a única razão pela qual o `CORS_ALLOW_ALL_ORIGINS = True` do
  Projeto01 "só não vira" um desastre maior: o próprio navegador bloqueia
  o envio de credenciais para um `*`. Mas isso é uma salvaguarda do
  navegador, não uma decisão de configuração sua — no instante em que
  alguém "resolver o bloqueio" trocando `*` por uma lista de origens *sem
  pensar* e junto ligar `CORS_ALLOW_CREDENTIALS = True` para qualquer
  origem da lista, a API passa a aceitar chamadas autenticadas por cookie
  de qualquer site que conste ali — inclusive um site de terceiro
  cadastrado por engano ou um subdomínio comprometido.

Resumindo a regra: **`CORS_ALLOW_ALL_ORIGINS`/`Access-Control-Allow-Origin: *`
nunca deve conviver com `CORS_ALLOW_CREDENTIALS = True`** (o Django/
django-cors-headers até impede essa combinação automaticamente, mas o
objetivo aqui é você nunca depender dessa rede de segurança). A lista de
origens permitidas deve ser **exatamente** as origens que de fato servem o
seu frontend — nunca um placeholder amplo "para não ter que configurar de
novo depois".

### 1.3 Passo 1 — Trocar "liberar tudo" por uma lista explícita

**Arquivo**: `api01/api01/settings.py`

```python
# Antes (Projeto01):
CORS_ALLOW_ALL_ORIGINS = True
```

```python
# Depois (Projeto02): só a origem real do frontend em desenvolvimento.
CORS_ALLOWED_ORIGINS = ['http://localhost:4200']
```

Em produção, essa lista teria a URL pública do frontend (ex.:
`https://app.minhaempresa.com`), nunca um domínio genérico nem um
wildcard (`https://*.minhaempresa.com`) a menos que você controle e
confie em **todo** subdomínio coberto pelo wildcard.

### 1.4 Passo 2 — Habilitar credenciais só junto com a lista explícita

Como o [[Projeto02]] passa a depender de cookie (refresh token e, por
consequência, o cookie CSRF — ver
[[Projeto02/ProtecaoXSSeCSRF]]), é necessário também:

```python
CORS_ALLOW_CREDENTIALS = True
```

Isso só é seguro porque já está condicionado à lista explícita do passo
1.3 — nunca ligue `CORS_ALLOW_CREDENTIALS` enquanto
`CORS_ALLOW_ALL_ORIGINS` ainda estiver `True` em qualquer lugar do
arquivo.

### 1.5 Passo 3 — Liberar só os headers que o frontend realmente manda

Por padrão, o `django-cors-headers` só permite um conjunto pequeno de
headers em requisições cross-origin. Como o frontend Angular manda um
header customizado (`X-XSRF-TOKEN`, usado pela defesa de CSRF — ver
[[Projeto02/ProtecaoXSSeCSRF]]), ele precisa ser explicitamente liberado,
senão o navegador bloqueia a requisição no *preflight* (a checagem
`OPTIONS` que o navegador faz antes da chamada real):

**Arquivo**: `api01/api01/settings.py`

```python
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + ['x-xsrf-token']
```

A regra geral: **liberar exatamente os headers usados, nunca "liberar
todos os headers" por conveniência** — cada header liberado é uma
possibilidade a mais de dado chegando de uma origem externa sendo aceito
sem passar pela validação padrão do navegador.

### 1.6 Passo 4 — `ALLOWED_HOSTS`: uma proteção diferente, fácil de confundir com CORS

`ALLOWED_HOSTS` não é CORS (não tem nada a ver com JavaScript de outra
origem lendo respostas) — é a lista de valores aceitos no cabeçalho
`Host` de uma requisição HTTP, usada pelo Django para se proteger de
ataques de **HTTP Host header poisoning** (ex.: um link de redefinição de
senha montado a partir de `request.get_host()`, que um atacante poderia
manipular mandando um `Host` falso). Como está no mesmo bloco de
"configuração de origem" do `settings.py`, vale corrigir junto:

```python
# Antes (Projeto01): qualquer host é aceito.
ALLOWED_HOSTS = ['*']
```

```python
# Depois: só os hosts que de fato servem esta API.
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
# Em produção, o(s) domínio(s) público(s) da API — nunca '*'.
```

### 1.7 Passo 5 — Testar

```bash
# 1. Origem permitida: deve devolver Access-Control-Allow-Origin igual à
#    origem enviada, e Access-Control-Allow-Credentials: true.
curl -i -X OPTIONS http://localhost:8000/api/login \
  -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

# 2. Origem não permitida: a resposta não deve trazer nenhum cabeçalho
#    Access-Control-Allow-Origin (o navegador real bloquearia a leitura
#    da resposta por JS rodando em atacante.com).
curl -i -X OPTIONS http://localhost:8000/api/login \
  -H "Origin: https://atacante.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```

Se o passo 2 não trouxer `Access-Control-Allow-Origin` nenhum na
resposta, a restrição está funcionando (note que `curl` sozinho, sem ser
um navegador, não é *bloqueado* por CORS — CORS é aplicado pelo
navegador na hora de decidir se entrega a resposta para o JavaScript da
página; por isso o teste é sobre quais cabeçalhos a API devolve, não
sobre se a chamada "funciona").

## 2. Parte B — SSRF

### 2.1 Por que esta seção é diferente das outras

Sendo honesto sobre o estado atual do código: **nenhuma rota deste
projeto (`api01` nem `api02`) faz requisições HTTP de saída** — não há
`requests.get(...)`, `urllib`, nem qualquer chamada de rede partindo do
backend para um destino arbitrário. Não existe, hoje, um vetor de SSRF
real para corrigir, então não há um "antes/depois" de código para mostrar
como nas outras seções.

O valor desta seção é outro: **SSRF é o tipo de vulnerabilidade que
costuma entrar silenciosamente numa feature nova**, bem depois do projeto
já estar em produção — por isso o objetivo aqui é você reconhecer o
padrão de código perigoso *antes* de escrevê-lo, não corrigir algo que já
existe.

### 2.2 Um exemplo concreto de como o SSRF entraria neste projeto

Imagine que, numa versão futura, alguém peça: "deixa o usuário colocar a
URL de uma imagem para usar como foto de perfil, e o backend baixa essa
imagem e guarda". Um jeito ingênuo de implementar isso:

```python
# NÃO FAÇA ISSO — exemplo do que seria uma vulnerabilidade de SSRF:
import requests
from django.http import JsonResponse

def definir_foto_perfil(request):
    url_imagem = request.POST.get('url')
    resposta = requests.get(url_imagem)   # o backend busca QUALQUER url
    # ... salva resposta.content como a foto do usuário ...
    return JsonResponse({'ok': True})
```

**Como isso seria explorado**: em vez de uma URL de imagem pública, o
atacante manda uma URL que aponta para algo que só o **próprio servidor**
consegue alcançar — por exemplo, um endpoint interno sem autenticação
(`http://localhost:8000/admin/`, um serviço interno na rede da empresa que
não está exposto à internet) ou, em ambientes de nuvem, o endereço de
metadata da instância (ex.: `http://169.254.169.254/...` na AWS/GCP/Azure,
que às vezes devolve credenciais temporárias da máquina sem exigir
autenticação, justamente porque assume que só código rodando *dentro* da
instância consegue alcançá-lo). O servidor faz a chamada, recebe a
resposta, e — dependendo do que a view faz com ela (devolve o conteúdo
bruto? salva num campo visível depois?) — o atacante consegue ler dados
que nunca deveriam estar acessíveis publicamente, usando o seu backend
como "proxy" para alcançar uma rede que ele não alcançaria diretamente de
fora.

### 2.3 Mitigações, caso/quando uma feature assim for adicionada

Se o projeto um dia precisar de uma funcionalidade que faz o backend
buscar algo a partir de uma URL fornecida pelo usuário, aplique — nesta
ordem de importância:

1. **Evite a necessidade, se possível.** O jeito mais seguro de não ter
   SSRF é não ter o backend fazendo requisições para URLs escolhidas por
   quem não é de confiança. Se o caso de uso permitir, prefira o upload
   direto do arquivo (o navegador do próprio usuário envia os bytes, o
   backend nunca precisa "ir buscar" nada em nome de ninguém).
2. **Lista de permissão (allowlist) de domínios/esquemas, nunca lista de
   bloqueio.** Se a URL tiver que vir de fora, restrinja a um conjunto
   pequeno e explícito de domínios confiáveis conhecidos — nunca tente
   enumerar "o que bloquear" (listas de bloqueio de SSRF são
   notoriamente fáceis de contornar: redirecionamentos HTTP, DNS que
   resolve para IP interno, IPv6, notações alternativas de IP como
   `0177.0.0.1` para `127.0.0.1`, etc.).
3. **Nunca aceitar `localhost`, IPs de rede privada
   (`127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`,
   `169.254.0.0/16`) nem o esquema `file://`** como destino — valide isso
   depois de resolver o DNS (não só olhando a string da URL), porque um
   atacante pode usar um domínio público que resolve para um IP privado.
4. **Desabilitar redirecionamentos automáticos** na biblioteca de
   requisição (`requests.get(url, allow_redirects=False)`), e reaplicar a
   validação do passo 2/3 em cada redirecionamento manualmente seguido —
   um destino inicial válido pode redirecionar para um destino interno.
5. **Timeout curto e limite de tamanho de resposta**, para reduzir o
   impacto de abuso mesmo que algum destino inesperado seja alcançado
   (evita, por exemplo, que a funcionalidade seja usada para escanear
   portas internas lentamente ou para exaurir memória/tempo do worker).
6. **Nunca devolver o corpo bruto da resposta buscada para o usuário que
   pediu a busca** sem revalidar o que é (ex.: confirmar `Content-Type`
   de imagem antes de tratar como imagem) — isso evita que o SSRF seja
   usado como um "proxy de leitura" genérico de qualquer conteúdo
   interno.

### 2.4 Checklist para revisar antes de aceitar uma feature nova

Ao revisar uma Pull Request que adiciona qualquer funcionalidade que
recebe uma **URL como entrada do usuário** e o **backend** (não o
navegador do usuário) faz uma requisição a partir dela, confirme:

- [ ] Existe uma allowlist explícita de domínios/esquemas permitidos — não
      apenas uma blocklist.
- [ ] IPs de rede privada e `localhost` são rejeitados após resolver o
      DNS, não só por comparação de string na URL original.
- [ ] Redirecionamentos HTTP não são seguidos automaticamente sem
      revalidação.
- [ ] Existe timeout e limite de tamanho na requisição de saída.
- [ ] O conteúdo buscado não é devolvido ao usuário como um "proxy" cru.

## 3. Resumo: arquivos tocados (CORS)

| Arquivo | O que muda | Proteção |
|---|---|---|
| `api01/api01/settings.py` | Troca `CORS_ALLOW_ALL_ORIGINS = True` por `CORS_ALLOWED_ORIGINS = [...]`; adiciona `CORS_ALLOW_CREDENTIALS = True`; restringe `CORS_ALLOW_HEADERS` à lista padrão + `x-xsrf-token`; troca `ALLOWED_HOSTS = ['*']` por hosts explícitos | CORS / Host header poisoning |

SSRF não tem arquivo a tocar hoje neste repositório (seção 2.1) — a
seção 2 é um guia preventivo para quando/se uma funcionalidade desse tipo
for proposta.

## 4. Checklist final (CORS)

- [ ] `CORS_ALLOW_ALL_ORIGINS` não existe mais em nenhum ambiente (dev,
      homologação, produção).
- [ ] `CORS_ALLOWED_ORIGINS` lista só as origens reais do(s) frontend(s),
      sem wildcard amplo.
- [ ] `CORS_ALLOW_CREDENTIALS = True` só coexiste com a lista explícita do
      item anterior, nunca com `*`.
- [ ] `CORS_ALLOW_HEADERS` lista só os headers de fato usados pelo
      frontend.
- [ ] `ALLOWED_HOSTS` lista hosts explícitos, nunca `['*']`, em qualquer
      ambiente que não seja um experimento local descartável.

## Ver também

- [[Projeto00/Vulnerabilidades]] — onde o CORS liberado para qualquer
  origem foi introduzido como vulnerabilidade proposital, junto com
  `ALLOWED_HOSTS = ['*']`.
- [[Projeto01/Vulnerabilidades]] — confirma que essas falhas de CORS
  continuam sem correção no [[Projeto01]].
- [[Projeto02/ProtecaoXSSeCSRF]] — explica por que CORS com credenciais e
  CSRF precisam ser configurados juntos (o mesmo cookie XSRF-TOKEN/header
  X-XSRF-TOKEN depende de ambos).
- [[Projeto02/SegurancaAutorizacaoAcesso]] (seção 7) — contexto de por que
  o refresh token em cookie torna a configuração de CORS mais sensível do
  que era no [[Projeto00]]/[[Projeto01]].
- `Documentação/OWASP Top 10/` — SSRF é a categoria **A10 Server-Side
  Request Forgery** na edição vigente; CORS mal configurado costuma ser
  classificado dentro de **A01 Broken Access Control**.
