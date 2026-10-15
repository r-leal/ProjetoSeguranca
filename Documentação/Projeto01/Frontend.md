# Projeto01 — Frontend (client01)

Documentação técnica do frontend. Para visão geral do projeto ver
[[Projeto01/Visao|Projeto01 — Visão]]; para o backend ver [[Projeto01/Backend]]. Este
documento assume a arquitetura do [[Projeto00/Frontend|client00]] como base e foca no
que mudou.

## Arquitetura

Mesma base do [[Projeto00/Frontend|client00]] — SPA Angular 18 com standalone
components, "smart component / service layer", sem NgRx/Signals store — com uma camada
nova:

```
main.ts
   │  bootstrapApplication(AppComponent, appConfig)
   ▼
app.config.ts            ← + withInterceptors([authInterceptor])
   │
   ▼
app.routes.ts             ← mapa de rotas → componente de página (idêntico ao Projeto00)
   │
   ▼
pages/<rota>/              ← um componente "de página" por rota
   │  usa
   ▼
core/services/              ← AuthService, TaskService, AdminService
   │  usa
   ▼
core/interceptors/            ← (novo) authInterceptor — anexa o JWT em toda requisição
   │  e
core/models/                    ← interfaces TypeScript, incluindo UsuarioToken
   │  e
core/api.config.ts                 ← URL base da API + chave do token no localStorage
```

Diferenças em relação ao [[Projeto00/Frontend|client00]]:

- **Interceptor HTTP** (`core/interceptors/auth.interceptor.ts`): o [[Projeto00/Frontend|client00]]
  não tinha nenhum; aqui, `authInterceptor` lê o JWT do `localStorage` e anexa
  `Authorization: Bearer <token>` em toda requisição automaticamente, antes de chegar ao
  backend.
- **Sessão como JWT, não como objeto cru**: `AuthService` guarda só a string do token
  (chave `auth_token`), não mais o `Usuario` inteiro.
- **Dupla fonte de identidade no `KanbanComponent`**: o `id` do usuário (usado só para
  montar a URL `/usuarios/<id>/tarefas`) vem de decodificar o payload do token sem
  verificar assinatura (`AuthService.usuarioLogado()`); o **nome exibido** no cabeçalho
  vem de uma chamada real ao backend (`AuthService.buscarUsuarioLogado()` →
  `GET /api/usuarios/me`), validada por `jwt_required` — ver
  [[Projeto01/Vulnerabilidades]] item 3 e [[Projeto01/Melhorias]].
- **Aba "Usuários" visível só para admin, mas só na UI**: `AppComponent` decide mostrar
  o link de navegação com base no `papel` decodificado do token
  (`mostrarAbaUsuarios`), mas não há guard de rota nem checagem de papel no backend —
  ver [[Projeto01/Vulnerabilidades]] item 5.

## Organização de pastas

```
client01/src/
├── main.ts
├── index.html
└── app/
    ├── app.component.ts/.html         ← + mostrarAbaUsuarios (lê papel do token)
    ├── app.config.ts                 ← + authInterceptor
    ├── app.routes.ts                   ← + rota /usuarios
    ├── core/
    │   ├── api.config.ts              ← + AUTH_TOKEN_KEY
    │   ├── interceptors/                ← novo
    │   │   └── auth.interceptor.ts
    │   ├── models/
    │   │   ├── usuario.ts               ← + Papel, UsuarioToken
    │   │   └── tarefa.ts
    │   └── services/
    │       ├── auth.service.ts          ← + buscarUsuarioLogado(), getToken()
    │       ├── task.service.ts           ← + filtrarPorNome()
    │       └── admin.service.ts           ← novo
    └── pages/
        ├── login/
        ├── cadastro/                     ← idêntico ao Projeto00 (sem seletor de papel)
        ├── kanban/                        ← + nome do usuário, filtro de tarefas
        ├── usuarios/                        ← novo (listagem + filtro, só para admin na UI)
        └── sobre/
```

## Rotas e páginas (`app.routes.ts`)

Mesmas rotas do [[Projeto00/Frontend|client00]] (`/login` default, `/cadastro`,
`/kanban`, `/sobre`, `**` → `/login`), **mais** `/usuarios` (nova). Nenhuma rota tem
guard — `/usuarios` é alcançável digitando a URL direto, independente do papel de quem
está logado (ver ⚠️ na seção `UsuariosComponent`, abaixo).

### `LoginComponent`
Igual ao [[Projeto00/Frontend|client00]] na interação (`email`, `senha`, `erro`,
`entrar()`), mas `AuthService.login()` agora recebe `{ token }` da API em vez do objeto
`Usuario`, e salva só o token.

### `CadastroComponent`
Mesmo formulário do [[Projeto00/Frontend|client00]] — `nome`, `sobrenome`,
`data_nascimento`, `email`, `senha`. Não há campo de papel: o formulário já teve um
`<select name="papel">` que permitia escolher `admin`/`gerente` livremente, mas essa
falha foi corrigida (campo removido do template e do componente) — ver
[[Projeto01/Melhorias]].

### `KanbanComponent`
- No `ngOnInit`: lê `usuarioToken` de `AuthService.usuarioLogado()` (decodificação local,
  não verificada) só para obter o `id` e montar a URL de tarefas; em paralelo, chama
  `AuthService.buscarUsuarioLogado()` (`GET /api/usuarios/me`, validado pelo backend) para
  preencher `usuarioNome`, exibido no cabeçalho ("Olá, `<nome>`").
- Estado local: igual ao [[Projeto00/Frontend|client00]] (`tarefas`, `novaTarefa`,
  `usuarioId`), **mais** `usuarioNome` e `filtroNome`.
- Ações novas: `filtrarTarefas()` (chama `TaskService.filtrarPorNome`, enviando o texto
  digitado cru para o backend) e `limparFiltro()`.
- `tratarErroAutenticacao()`: se qualquer chamada de tarefas devolver `401` (token
  ausente/inválido), faz logout e redireciona para `/login` — tratamento que não existia
  no [[Projeto00/Frontend|client00]], necessário agora que o backend de fato rejeita
  requisições sem token válido.
- **Vulnerabilidades propositais mantidas do [[Projeto00]]**: `descricaoHtml()` continua
  usando `bypassSecurityTrustHtml()` sem sanitização (XSS armazenado, item 10 de
  [[Projeto00/Vulnerabilidades]], guia em [[Projeto00/Ataque-A05-StoredXSS]] — ainda
  válido aqui, sem alteração).
- **Vulnerabilidade proposital nova**: o campo de filtro (`filtroNome`) é enviado cru
  para `GET /api/usuarios/<id>/tarefas?nome=...`, que o backend concatena numa query SQL
  sem parametrização. Ver [[Projeto01/Vulnerabilidades]] item 4 e
  [[Projeto01/Ataque-A05-SQLInjectionFiltro]].

### `UsuariosComponent` (novo)
- Tela só acessível (na prática) via o link "Usuários" do menu, que `AppComponent` só
  renderiza quando `authService.usuarioLogado()?.papel === 'admin'`.
- `ngOnInit()` já carrega a lista completa via `AdminService.listarUsuarios()`
  (`GET /api/usuarios`); um campo de filtro (`filtro`, ligado a `AdminService.listarUsuarios(termo)`)
  permite buscar por nome, sobrenome ou email (`?q=<termo>` no backend).
- Tabela simples com id, nome, sobrenome, email e papel de cada usuário.
- ⚠️ **Vulnerabilidade proposital (Broken Access Control)**: a tela não tem nenhum
  guard de rota, e a chamada ao backend não é diferente da de qualquer outra tela — é a
  mesma `GET /api/usuarios` que qualquer usuário autenticado pode chamar direto. Ver
  [[Projeto01/Vulnerabilidades]] item 5 e
  [[Projeto01/Ataque-A01-ListagemUsuariosSemChecarPapel]].

### `SobreComponent`
Sem estado nem lógica — texto institucional atualizado mencionando as mudanças do
Projeto01 em relação ao [[Projeto00]].

## Camada `core`

| Arquivo | Papel |
|---|---|
| `api.config.ts` | `API_BASE_URL` + `AUTH_TOKEN_KEY` (chave do token no `localStorage`) |
| `interceptors/auth.interceptor.ts` | `authInterceptor` — anexa `Authorization: Bearer <token>` em toda requisição HTTP |
| `models/usuario.ts` | `Usuario` (inclui `papel`), `Papel`, `UsuarioToken` (claims decodificadas do JWT) |
| `models/tarefa.ts` | `Tarefa` + `EstadoTarefa` (idêntico ao Projeto00) |
| `services/auth.service.ts` | `login()`, `cadastrar()`, `logout()`, `getToken()`, `usuarioLogado()` (decodifica sem verificar), `buscarUsuarioLogado()` (via backend, verificado) |
| `services/task.service.ts` | `listarPorUsuario()`, `filtrarPorNome()` (vulnerável a SQLi no backend), `criar()`, `atualizar()`, `remover()` |
| `services/admin.service.ts` | `listarUsuarios(termo?)` — chama `GET /api/usuarios`; nenhuma checagem de papel no cliente nem no backend |

## Armazenamento de dados local

- `AuthService` usa **`localStorage`**, chave `auth_token` (era `usuario_logado` no
  [[Projeto00/Frontend|client00]]).
- Conteúdo salvo: **só a string do JWT** — não mais o objeto `Usuario` completo. Isso
  resolve parcialmente o item 9 de [[Projeto00/Vulnerabilidades]] (não há mais senha em
  claro guardada no navegador), mas o token em si ainda é legível por qualquer
  JavaScript da página (incluindo um XSS) e **nunca expira** — ver
  [[Projeto01/Vulnerabilidades]] itens 2 e 3.
- `usuarioLogado()` decodifica o payload do JWT (`atob` no segmento do meio) **sem
  verificar a assinatura** — usado só para dados de exibição não sensíveis/para montar
  URLs; nenhuma decisão de autorização real depende dele no backend.
- `logout()` apenas remove a chave (`localStorage.removeItem('auth_token')`).

## Bibliotecas (`package.json`)

Idêntico ao [[Projeto00/Frontend|client00]] — nenhuma dependência nova foi adicionada; o
interceptor usa só a API padrão do `@angular/common/http`.

| Pacote | Versão | Uso |
|---|---|---|
| `@angular/core`, `common`, `forms`, `router`, `platform-browser*`, `animations`, `compiler` | ^18.2.0 | Framework Angular |
| `rxjs` | ~7.8.0 | Observables usados pelo `HttpClient` e pelos services |
| `zone.js` | ~0.14.10 | Detecção de mudanças do Angular |
| `tslib` | ^2.3.0 | Helpers de compilação TypeScript |
| `@angular/cli`, `@angular-devkit/build-angular`, `@angular/compiler-cli` (dev) | ^18.2.x | Build e CLI |
| `karma`, `jasmine-core`, `@types/jasmine` (dev) | — | Testes unitários — esqueleto gerado pelo `ng generate`, sem asserções de negócio |
| `typescript` (dev) | ~5.5.2 | Linguagem |
