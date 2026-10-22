# Projeto02 — Frontend (client02)

Documentação técnica do frontend. Para visão geral do projeto ver
[[Projeto02/Visao|Projeto02 — Visão]]; para o backend ver [[Projeto02/Backend]]. Este
documento assume a arquitetura do [[Projeto01/Frontend|client01]] como base e foca no
que mudou.

## Arquitetura

Mesma base do [[Projeto01/Frontend|client01]] — SPA Angular 18 standalone, "smart
component / service layer", `authInterceptor` anexando o token — com duas mudanças de
bootstrap:

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
core/interceptors/            ← authInterceptor (reescrito: withCredentials + retry em 401)
   │  e
core/models/                    ← interfaces TypeScript (idêntico ao Projeto01)
   │  e
core/api.config.ts                 ← só API_BASE_URL (AUTH_TOKEN_KEY removida)
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
  [[Projeto02/Backend|api02]].
- **`authInterceptor` reescrito**: além de anexar `Authorization: Bearer <token>` (agora
  lido de uma variável em memória do `AuthService`, não mais do `localStorage`), liga
  `withCredentials: true` em toda chamada à API (necessário para o cookie do refresh
  token e o cookie de CSRF trafegarem entre `localhost:4200` e `localhost:8000`), e
  intercepta `401` para tentar `AuthService.refrescarToken()` e repetir a requisição
  original uma única vez, antes de propagar o erro.
- **`AuthService` reescrito**: token em memória (não mais `localStorage`), mais
  `restaurarSessao()`, `refrescarToken()`; `logout()` agora chama o backend
  (`POST /api/logout`) para revogar o refresh token, além de limpar o estado local.
- **`AdminService`/`AppComponent`**: comentários atualizados — a aba "Usuários" segue
  escondida só por UX no cliente, mas a chamada ao backend agora é de fato recusada
  (`403`) para quem não é admin (ver [[Projeto02/Backend]]).

## Organização de pastas

```
client02/src/
├── main.ts
├── index.html
└── app/
    ├── app.component.ts/.html         ← comentário atualizado (papel_required no backend)
    ├── app.config.ts                 ← + APP_INITIALIZER, withXsrfConfiguration
    ├── app.routes.ts                   ← idêntico ao Projeto01
    ├── core/
    │   ├── api.config.ts              ← AUTH_TOKEN_KEY removida
    │   ├── interceptors/
    │   │   └── auth.interceptor.ts     ← reescrito (credentials + retry em 401)
    │   ├── models/
    │   │   ├── usuario.ts               ← comentário atualizado (token em memória)
    │   │   └── tarefa.ts                  ← idêntico
    │   └── services/
    │       ├── auth.service.ts          ← reescrito (token em memória, refresh, logout real)
    │       ├── task.service.ts           ← idêntico (SQLi herdada, sem alteração)
    │       └── admin.service.ts           ← comentário atualizado
    └── pages/
        ├── login/                        ← idêntico ao Projeto01
        ├── cadastro/                      ← idêntico
        ├── kanban/                         ← idêntico (comentários inalterados)
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
continua recebendo `{ token }` do backend, mas agora também recebe (de forma transparente
ao componente, via cookie) o refresh token.

### `KanbanComponent`
`ngOnInit` continua lendo `AuthService.usuarioLogado()` só para o `id` (exibição/
montagem de URL) e chamando `buscarUsuarioLogado()` para o nome exibido no cabeçalho —
funciona do mesmo jeito porque, no momento em que este componente roda, o
`APP_INITIALIZER` já tentou restaurar a sessão (ver "Diferenças", acima). O filtro de
nome continua enviando o termo cru para o backend — vulnerabilidade herdada sem alteração
(ver [[Projeto01/Vulnerabilidades]] item 4). O XSS armazenado via `bypassSecurityTrustHtml`
também permanece sem alteração (herdado do [[Projeto00]]).

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
token em memória, refresh token em cookie `HttpOnly`, papel exigido no backend) em vez do
texto do [[Projeto01]].

## Camada `core`

| Arquivo | Papel |
|---|---|
| `api.config.ts` | Só `API_BASE_URL` — `AUTH_TOKEN_KEY` foi removida (nada mais é salvo no `localStorage`) |
| `interceptors/auth.interceptor.ts` | `authInterceptor` — anexa `Authorization` + `withCredentials`; renova e repete a requisição em `401` |
| `models/usuario.ts` | `Usuario`, `Papel`, `UsuarioToken` — idêntico ao [[Projeto01]], comentário atualizado |
| `models/tarefa.ts` | `Tarefa` (+ `url`/`url_titulo` novos) + `EstadoTarefa` + `PreviewLink` (novo) |
| `services/auth.service.ts` | `login()`, `cadastrar()`, `buscarUsuarioLogado()`, `restaurarSessao()` (novo), `refrescarToken()` (novo), `logout()` (agora revoga no backend), `getToken()`, `usuarioLogado()` |
| `services/task.service.ts` | + `previewLink()` (novo, `POST /api/tarefas/preview-link`) |
| `services/admin.service.ts` | Idêntico ao [[Projeto01]] (comentário atualizado) |

Os `models/*.ts` continuam sendo apenas interfaces TypeScript — nenhuma validação de
runtime foi adicionada.

## Armazenamento de dados local

- **Access token**: variável privada em memória, dentro do `AuthService` — nunca
  `localStorage`/`sessionStorage`. Perdido a cada reload de página; recuperado via
  `restaurarSessao()` no `APP_INITIALIZER`, usando o refresh token.
- **Refresh token**: cookie `HttpOnly` setado pelo backend (`refresh_token`) —
  inacessível a qualquer JavaScript do frontend, inclusive um XSS. O `AuthService` nunca
  lê nem manipula esse valor diretamente; o browser o envia automaticamente (com
  `withCredentials: true`) nas chamadas a `/token/refresh` e `/logout`.
- **Cookie de CSRF** (`XSRF-TOKEN`): legível por JavaScript de propósito — é o próprio
  Angular (via `withXsrfConfiguration`) quem lê e devolve no header `X-XSRF-TOKEN`.
- Isso fecha o item 9 de [[Projeto00/Vulnerabilidades]] (dados sensíveis em
  `localStorage`) e os itens 2/3 de [[Projeto01/Vulnerabilidades]] (token sem expiração /
  token exposto em `localStorage`) — ver [[Projeto02/Melhorias]] para a narrativa
  completa.
- `logout()` chama `POST /api/logout` (revoga o refresh token no backend) e só então
  limpa o access token em memória — diferente do [[Projeto01/Frontend|client01]], que só
  removia a chave do `localStorage` sem avisar o backend.

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
