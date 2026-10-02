# Projeto00 — Frontend (client00)

Documentação técnica do frontend. Para visão geral do projeto ver
[[Projeto00/Visao|Projeto00 — Visão]]; para o backend ver [[Projeto00/Backend]].

## Arquitetura

O `client00` é uma SPA Angular 18 usando **standalone components** (sem `NgModule`),
organizada em dois níveis:

```
main.ts
   │  bootstrapApplication(AppComponent, appConfig)
   ▼
app.config.ts            ← providers globais: Router, HttpClient, change detection
   │
   ▼
app.routes.ts             ← mapa de rotas → componente de página
   │
   ▼
pages/<rota>/              ← um componente "de página" por rota (smart component)
   │  usa
   ▼
core/services/              ← lógica de acesso a dados (HTTP) e estado de sessão
   │  usa
   ▼
core/models/                  ← interfaces TypeScript (contrato de dados)
   │  e
core/api.config.ts             ← URL base da API
```

Isso é uma variação do padrão **"smart component / service layer"**: os componentes em
`pages/` concentram estado da tela e interação do usuário (equivalente a
"controller + view" juntos, já que o Angular acopla template + classe), enquanto toda
comunicação com o backend fica isolada em `core/services/`. Não há camada de
"dumb/presentational components" nem gerenciamento de estado global (NgRx/Signals
store) — cada página busca e guarda seu próprio estado em memória.

Características da arquitetura:

- **Roteamento centralizado**: `app.routes.ts` é a única fonte de verdade de quais URLs
  existem e qual componente cada uma renderiza. Não há *lazy loading* nem *guards* de
  rota — qualquer um pode navegar direto para `/kanban` sem estar "logado" (a página só
  não carrega tarefas se não achar usuário no `localStorage`).
- **Standalone components**: cada componente declara seus próprios `imports`
  (`CommonModule`, `FormsModule`, `RouterLink`, etc.) em vez de depender de um
  `NgModule` compartilhado. Isso é o padrão recomendado a partir do Angular 17+.
- **Comunicação via `HttpClient` + RxJS `Observable`**: todo acesso à API retorna um
  `Observable`, consumido nos componentes via `.subscribe({ next, error })`.
- **Sem interceptor HTTP**: não há `HttpInterceptor` adicionando token/cookie de
  autenticação nas requisições — o backend aceita tudo sem checar identidade.
- **Persistência de sessão em `localStorage`**, não em cookie/token — ver seção
  dedicada abaixo.

## Organização de pastas

```
client00/src/
├── main.ts                      ← bootstrap da aplicação
├── index.html
└── app/
    ├── app.component.ts/.html    ← shell raiz (contém <router-outlet>)
    ├── app.config.ts              ← providers globais (DI)
    ├── app.routes.ts               ← definição de rotas
    ├── core/                        ← código transversal, sem UI própria
    │   ├── api.config.ts
    │   ├── models/
    │   │   ├── usuario.ts
    │   │   └── tarefa.ts
    │   └── services/
    │       ├── auth.service.ts
    │       └── task.service.ts
    └── pages/                        ← um diretório por tela/rota
        ├── login/
        ├── cadastro/
        ├── kanban/
        └── sobre/
```

`core/` = infraestrutura e contratos de dados (reutilizável por qualquer página).
`pages/` = UI e lógica específica de cada tela.

## Rotas e páginas (`app.routes.ts`)

| Rota | Componente | Pasta | Função |
|---|---|---|---|
| `/login` (default) | `LoginComponent` | `pages/login/` | Autenticação (email + senha) |
| `/cadastro` | `CadastroComponent` | `pages/cadastro/` | Criação de novo usuário |
| `/kanban` | `KanbanComponent` | `pages/kanban/` | Quadro de tarefas do usuário logado |
| `/sobre` | `SobreComponent` | `pages/sobre/` | Tela institucional, sem lógica |
| `**` | — | — | Qualquer rota desconhecida redireciona para `/login` |

### `LoginComponent`
- Estado local: `email`, `senha`, `erro`.
- `entrar()` → `AuthService.login(email, senha)` → sucesso navega para `/kanban`; erro
  seta mensagem genérica (`erro`), sem detalhar motivo (mas a senha trafega e é
  armazenada em texto puro — ver abaixo).

### `CadastroComponent`
- Estado local: objeto `usuario: Usuario` (nome, sobrenome, data_nascimento, email,
  senha) ligado ao form via `ngModel` (`FormsModule`).
- `cadastrar()` → `AuthService.cadastrar(usuario)` → sucesso navega para `/login`.

### `KanbanComponent`
- No `ngOnInit`, lê o usuário "logado" do `localStorage`
  (`AuthService.usuarioLogado()`) e, se existir, carrega as tarefas dele.
- Estado local: `tarefas: Tarefa[]`, `novaTarefa` (form de criação), `usuarioId`, lista
  fixa de `estados` (`esperando`, `em_andamento`, `concluido`) usada para desenhar as
  três colunas do Kanban.
- Ações: `criarTarefa()` (`POST`), `moverTarefa()` (muda `estado` e salva via `PUT`),
  `removerTarefa()` (`DELETE`), `sair()` (logout + redireciona para `/login`).
- **Vulnerabilidade proposital**: a descrição da tarefa é renderizada via
  `[innerHTML]="descricaoHtml(tarefa)"`, e `descricaoHtml()` usa
  `DomSanitizer.bypassSecurityTrustHtml()` — desligando o sanitizador padrão do Angular.
  Isso abre um XSS armazenado via campo `descricao`. Ver
  [[Projeto00/Vulnerabilidades]] (item 10) e o passo a passo em
  [[Projeto00/Ataque-A05-StoredXSS]].

### `SobreComponent`
- Sem estado nem lógica — apenas template estático institucional.

## Camada `core`

| Arquivo | Papel |
|---|---|
| `api.config.ts` | Constante `API_BASE_URL = 'http://localhost:8000/api'` |
| `models/usuario.ts` | Interface `Usuario` — espelha o JSON do backend, **incluindo `senha`** |
| `models/tarefa.ts` | Interface `Tarefa` + tipo `EstadoTarefa` |
| `services/auth.service.ts` | `login()`, `cadastrar()`, `logout()`, `usuarioLogado()` |
| `services/task.service.ts` | `listarPorUsuario()`, `criar()`, `atualizar()`, `remover()` |

Os `models/*.ts` são apenas **interfaces TypeScript** (contrato de tipos em tempo de
compilação) — não existe validação de runtime (ex.: `zod`/`class-validator`); se o
backend mudar o formato do JSON, o TypeScript não vai detectar isso em tempo de
execução.

## Armazenamento de dados local

- `AuthService` usa **`localStorage`** do navegador, chave fixa `'usuario_logado'`.
- Conteúdo salvo: o objeto `Usuario` **completo** retornado pelo login, incluindo a
  `senha` em texto puro, serializado com `JSON.stringify` (método `salvarSessao`) e lido
  de volta com `JSON.parse` (`usuarioLogado()`).
- Não há expiração, criptografia, nem flag `httpOnly` (que nem existiria para
  `localStorage` — é sempre acessível via JavaScript). Qualquer script executado na
  página (ex.: o XSS armazenado do `KanbanComponent`, ver acima) consegue ler essa
  chave.
- `logout()` apenas remove a chave (`localStorage.removeItem('usuario_logado')`).
- Esse é o único mecanismo de "sessão" do app — não existe cookie de sessão do Django
  nem JWT.

## Bibliotecas (`package.json`)

| Pacote | Versão | Uso |
|---|---|---|
| `@angular/core`, `common`, `forms`, `router`, `platform-browser*`, `animations`, `compiler` | ^18.2.0 | Framework Angular |
| `rxjs` | ~7.8.0 | Observables usados pelo `HttpClient` e pelos services |
| `zone.js` | ~0.14.10 | Detecção de mudanças (change detection) do Angular |
| `tslib` | ^2.3.0 | Helpers de compilação TypeScript |
| `@angular/cli`, `@angular-devkit/build-angular`, `@angular/compiler-cli` (dev) | ^18.2.x | Build e CLI |
| `karma`, `jasmine-core`, `@types/jasmine` (dev) | — | Testes unitários — existe um `*.spec.ts` por componente/serviço, mas sem asserções de negócio implementadas (esqueleto gerado pelo `ng generate`) |
| `typescript` (dev) | ~5.5.2 | Linguagem |

Não há biblioteca de UI (Bootstrap/Angular Material) nem de gerenciamento de estado
(NgRx/Signals store) — toda a estilização é CSS próprio por componente
(`*.component.css`) e todo o estado é local aos componentes + `localStorage`.
