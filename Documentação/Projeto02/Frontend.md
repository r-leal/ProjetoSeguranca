# Projeto02 — Frontend (client02)

Documentação técnica do frontend. Para visão geral do projeto ver
[[Projeto02/Visao|Projeto02 — Visão]]; para o backend ver [[Projeto02/Backend]]. Este
documento assume a arquitetura do [[Projeto01/Frontend|client01]] como base e foca no
que mudou.

## Arquitetura

Mesma base do [[Projeto01/Frontend|client01]] — SPA Angular 18 standalone, "smart
component / service layer" — com mudanças de bootstrap e, principalmente, na forma como
a sessão é carregada (cookies `HttpOnly`, não mais um token manuseado pelo frontend):

```
main.ts
   │  bootstrapApplication(AppComponent, appConfig)
   ▼
app.config.ts            ← + withXsrfConfiguration + APP_INITIALIZER (restaura sessão)
   │
   ▼
app.routes.ts             ← idêntico ao Projeto01
   │
   ▼
pages/<rota>/              ← um componente "de página" por rota
   │  usa
   ▼
core/services/              ← AuthService (reescrito), TaskService, AdminService
   │  usa
   ▼
core/interceptors/            ← authInterceptor (reescrito: só withCredentials + retry em 401,
   │                             sem anexar nenhum token — vai todo via cookie HttpOnly)
   │  e
core/models/                    ← interfaces TypeScript (UsuarioToken removida)
   │  e
core/api.config.ts                 ← API_BASE_URL agora relativo ('/api'), via proxy do dev server
```

Diferenças em relação ao [[Projeto01/Frontend|client01]]:

- **`APP_INITIALIZER` novo** (`app.config.ts`): chama
  `AuthService.restaurarSessao()` (que usa o refresh token via cookie) antes do Angular
  renderizar qualquer rota. Sem isso, haveria uma corrida entre essa restauração
  (assíncrona) e o `ngOnInit` de componentes como `KanbanComponent`, que leriam "não
  autenticado" antes do refresh terminar. Erro aqui é silenciado — só significa "não
  estava logado".
- **`withXsrfConfiguration` novo** (`app.config.ts`): declara explicitamente o par
  cookie/header (`XSRF-TOKEN` / `X-XSRF-TOKEN`) que o `HttpClient` usa para o fluxo de
  CSRF — tem que bater com `CSRF_COOKIE_NAME`/`CSRF_HEADER_NAME` do
  [[Projeto02/Backend|api02]]. Por padrão, o Angular só anexa esse header
  automaticamente em requisições que a página enxerga como **mesma origem** — daí o
  `proxy.conf.json` descrito abaixo, sem o qual o header nunca seria enviado (ver
  [[Projeto02/Melhorias]]).
- **`authInterceptor` reescrito, duas vezes**: a versão inicial deste projeto anexava
  `Authorization: Bearer <token>` lido de uma variável em memória do `AuthService`
  (substituindo o `localStorage` do [[Projeto01]]). Na versão final, ele não anexa mais
  nenhum header de autenticação — o access token agora vai sozinho, via cookie
  `HttpOnly` setado pelo backend — e só liga `withCredentials: true` em toda chamada à
  API (necessário para os cookies de access/refresh token e o cookie de CSRF
  trafegarem entre `localhost:4200` e `localhost:8000`), além de interceptar `401` para
  tentar `AuthService.refrescarToken()` e repetir a requisição original uma única vez,
  antes de propagar o erro.
- **`AuthService` reescrito**: não guarda mais nenhum token (nem em `localStorage`, nem
  em memória) — só o objeto `Usuario` devolvido já validado pelo backend nas respostas
  de `login()`, `refrescarToken()`/`restaurarSessao()` e `buscarUsuarioLogado()`.
  `logout()` chama o backend (`POST /api/logout`) para revogar o refresh token e limpar
  os cookies, além de limpar o estado local.
- **`proxy.conf.json` novo** (`client02/`), ligado via
  `angular.json:projects.client02.architect.serve.options.proxyConfig`: faz o dev server
  do Angular repassar `/api` para `http://localhost:8000`. `API_BASE_URL`
  (`core/api.config.ts`) passa de uma URL absoluta (`http://localhost:8000/api`) para um
  caminho relativo (`/api`) — sem isso, o `HttpXsrfInterceptor` do Angular (bullet
  acima) nunca anexaria o header CSRF, por tratar a chamada como cross-origin (ver
  [[Projeto02/Melhorias]]).
- **`AdminService`/`AppComponent`**: comentários atualizados — a aba "Usuários" segue
  escondida só por UX no cliente, mas a chamada ao backend agora é de fato recusada
  (`403`) para quem não é admin (ver [[Projeto02/Backend]]).

## Organização de pastas

```
client02/
├── proxy.conf.json                     ← novo: dev server repassa /api para :8000
├── angular.json                         ← serve.options.proxyConfig aponta pro arquivo acima
└── src/
    ├── main.ts
    ├── index.html
    └── app/
        ├── app.component.ts/.html         ← comentário atualizado (papel_required no backend)
        ├── app.config.ts                 ← + APP_INITIALIZER, withXsrfConfiguration
        ├── app.routes.ts                   ← idêntico ao Projeto01
        ├── core/
        │   ├── api.config.ts              ← API_BASE_URL relativo ('/api', via proxy)
        │   ├── interceptors/
        │   │   └── auth.interceptor.ts     ← reescrito (só credentials + retry em 401,
        │   │                                  sem anexar token)
        │   ├── models/
        │   │   ├── usuario.ts               ← UsuarioToken removida (não há mais JWT
        │   │   │                               decodificado no cliente)
        │   │   └── tarefa.ts                  ← idêntico
        │   └── services/
        │       ├── auth.service.ts          ← reescrito (nenhum token em memória; usuário
        │       │                               validado pelo backend, refresh, logout real)
        │       ├── task.service.ts           ← filtro por nome corrigido (SQLi fechada no
        │       │                               backend, nada muda no client)
        │       └── admin.service.ts           ← comentário atualizado
        └── pages/
            ├── login/                        ← idêntico ao Projeto01
            ├── cadastro/                      ← idêntico
            ├── kanban/                         ← descricaoHtml()/DomSanitizer removidos
            │                                      (correção de XSS); ngOnInit simplificado
            ├── usuarios/                        ← idêntico
            └── sobre/                            ← texto atualizado para o estado do Projeto02
```

## Rotas e páginas (`app.routes.ts`)

Mesmas rotas do [[Projeto01/Frontend|client01]] (`/login` default, `/cadastro`,
`/kanban`, `/usuarios`, `/sobre`, `**` → `/login`), sem alteração. Nenhuma rota tem
guard — isso continua sendo decidido só pelo backend (401/403) e tratado reativamente
pelos componentes.

### `LoginComponent` / `CadastroComponent`
Sem alteração de interação em relação ao [[Projeto01/Frontend|client01]]. `AuthService.login()`
recebe do backend o `Usuario` autenticado (não mais um token) — o access token e o
refresh token chegam só via `Set-Cookie`, de forma transparente ao componente.

### `KanbanComponent`
`ngOnInit` lê `AuthService.usuarioLogado()` uma única vez, para `id` **e** `nome` — já
que os dois vêm validados pelo backend (login/refresh/`usuarios/me`), não é mais preciso
uma segunda chamada a `buscarUsuarioLogado()` só para exibir o nome (como numa versão
anterior deste projeto). Isso funciona porque, no momento em que este componente roda, o
`APP_INITIALIZER` já tentou restaurar a sessão (ver "Diferenças", acima).

A descrição da tarefa é renderizada com interpolação de texto padrão
(`{{ tarefa.descricao }}`) — o método `descricaoHtml()`, o `DomSanitizer` injetado e o
binding `[innerHTML]` que existiam (herdados desde o [[Projeto00]]) foram removidos: o
Angular escapa HTML automaticamente nessa interpolação, fechando o XSS armazenado que
existia nesse ponto (ver [[Projeto02/Melhorias]]; a falha original está em
[[Projeto00/Vulnerabilidades]] item 10). O filtro de nome
(`TaskService.filtrarPorNome`) continua enviando o termo digitado como query string —
isso em si não mudou —, mas o que o backend faz com esse valor mudou: a SQL Injection que
existia no filtro foi corrigida (ver [[Projeto02/Melhorias]]; a falha original está em
[[Projeto01/Vulnerabilidades]] item 4).

**Novo**: o formulário de criação de tarefa ganha um campo `url` opcional e um botão
"Pré-visualizar" (`previsualizarLink()`), que chama `TaskService.previewLink()`
(`POST /api/tarefas/preview-link`) só para feedback imediato na tela — o título
realmente salvo na tarefa é sempre recalculado pelo backend no momento de
criar/editar (`tarefas/views.py:_resolver_url_titulo`), nunca aceito do que este
preview devolveu ao cliente (ver [[Projeto02/Backend]], seção "Preview de link"). O
card do Kanban exibe `tarefa.url_titulo || tarefa.url` como link (`<a [href]>`,
sanitizado pelo Angular por padrão), quando a tarefa tem `url`.

### `UsuariosComponent`
Sem alteração de template/lógica. A diferença real está no backend: a mesma chamada
(`GET /api/usuarios`) que antes qualquer usuário autenticado conseguia ler agora devolve
`403` para quem não é admin — ver [[Projeto02/Backend]] e [[Projeto02/Melhorias]].

### `SobreComponent`
Texto atualizado (`sobre.component.html`) para descrever o estado atual (hash PBKDF2,
access **e** refresh token em cookies `HttpOnly`, proteção CSRF cobrindo toda rota
autenticada por cookie, papel exigido no backend, SQL Injection e XSS armazenado
corrigidos) em vez do texto do [[Projeto01]].

## Camada `core`

| Arquivo | Papel |
|---|---|
| `api.config.ts` | Só `API_BASE_URL`, agora `/api` (caminho relativo, via `proxy.conf.json`) — `AUTH_TOKEN_KEY` foi removida (nada é salvo no `localStorage`) |
| `interceptors/auth.interceptor.ts` | `authInterceptor` — liga `withCredentials`; renova (`refrescarToken()`) e repete a requisição em `401`. Não anexa nenhum token: access/refresh token vão via cookie `HttpOnly`, automático |
| `models/usuario.ts` | `Usuario`, `Papel` — `UsuarioToken` foi removida (não há mais payload de JWT decodificado no cliente) |
| `models/tarefa.ts` | `Tarefa` (+ `url`/`url_titulo` novos) + `EstadoTarefa` + `PreviewLink` (novo) |
| `services/auth.service.ts` | `login()`, `cadastrar()`, `buscarUsuarioLogado()`, `restaurarSessao()`, `refrescarToken()`, `logout()` (revoga no backend), `usuarioLogado()` — todos devolvem/guardam o `Usuario` já validado pelo backend, nunca um token |
| `services/task.service.ts` | + `previewLink()` (novo, `POST /api/tarefas/preview-link`) |
| `services/admin.service.ts` | Idêntico ao [[Projeto01]] (comentário atualizado) |

Os `models/*.ts` continuam sendo apenas interfaces TypeScript — nenhuma validação de
runtime foi adicionada.

## Armazenamento de dados local

- **Access token**: cookie `HttpOnly` setado pelo backend (`access_token`) — não fica em
  nenhum *storage* do browser nem em memória do `AuthService`. Inacessível a qualquer
  JavaScript do frontend, inclusive um XSS. O `AuthService` nunca lê, decodifica nem
  anexa esse valor; o browser o envia automaticamente (com `withCredentials: true`) em
  toda chamada a `/api`.
- **Refresh token**: cookie `HttpOnly` setado pelo backend (`refresh_token`) — mesma
  proteção do access token. O `AuthService` nunca lê nem manipula esse valor diretamente;
  o browser o envia automaticamente nas chamadas a `/token/refresh` e `/logout`.
- **Dados do usuário para exibição** (nome, papel): variável privada em memória, dentro
  do `AuthService` (`usuarioAtual`) — preenchida com o JSON que o próprio backend já
  devolve validado nas respostas de `login()`, `refrescarToken()`/`restaurarSessao()` e
  `buscarUsuarioLogado()`. Diferente de uma versão anterior deste projeto, não é mais um
  payload de JWT decodificado no cliente sem checar assinatura — é sempre o que o
  backend confirmou. Perdido a cada reload de página (como qualquer variável em memória);
  recuperado via `restaurarSessao()` no `APP_INITIALIZER`.
- **Cookie de CSRF** (`XSRF-TOKEN`): legível por JavaScript de propósito — é o próprio
  Angular (via `withXsrfConfiguration`) quem lê e devolve no header `X-XSRF-TOKEN`. Só
  funciona para chamadas que a página enxerga como mesma origem, daí o
  `proxy.conf.json` (ver "Diferenças", acima).
- Isso fecha o item 9 de [[Projeto00/Vulnerabilidades]] (dados sensíveis em
  `localStorage`) e os itens 2/3 de [[Projeto01/Vulnerabilidades]] (token sem expiração /
  token exposto em `localStorage`) — ver [[Projeto02/Melhorias]] para a narrativa
  completa.
- `logout()` chama `POST /api/logout` (revoga o refresh token no backend e limpa os dois
  cookies) e só então limpa o `usuarioAtual` em memória — diferente do
  [[Projeto01/Frontend|client01]], que só removia a chave do `localStorage` sem avisar o
  backend.

## Bibliotecas (`package.json`)

Idêntico ao [[Projeto01/Frontend|client01]] — nenhuma dependência nova; o fluxo de
refresh/CSRF usa só a API padrão do `@angular/common/http`.

| Pacote | Versão | Uso |
|---|---|---|
| `@angular/core`, `common`, `forms`, `router`, `platform-browser*`, `animations`, `compiler` | ^18.2.0 | Framework Angular |
| `rxjs` | ~7.8.0 | Observables do `HttpClient` e dos services |
| `zone.js` | ~0.14.10 | Detecção de mudanças do Angular |
| `tslib` | ^2.3.0 | Helpers de compilação TypeScript |
| `@angular/cli`, `@angular-devkit/build-angular`, `@angular/compiler-cli` (dev) | ^18.2.x | Build e CLI |
| `karma`, `jasmine-core`, `@types/jasmine` (dev) | — | Testes unitários — esqueleto gerado, sem asserções de negócio |
| `typescript` (dev) | ~5.5.2 | Linguagem |
