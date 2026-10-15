# Projeto01 — Ataque A01: Broken Access Control (listagem de usuários sem checar papel)

Guia prático, passo a passo, de como explorar a falha de **A01 Broken Access Control**
(ver [[OWASP Top 10]]) no [[Projeto01]], na variante **falta de autorização baseada em
papel (RBAC)** da aba "Usuários", já catalogada em [[Projeto01/Vulnerabilidades]]
(item 5). Diferente do escalonamento de privilégio no cadastro que existiu neste projeto
(mostrava como se **tornar** admin — já corrigido, ver [[Projeto01/Melhorias]]), este guia
assume que você **nunca** tem papel `admin`, e mesmo assim lê dados que só deveriam ser
visíveis para quem tem.

> Nota de versão: A01 Broken Access Control é a categoria A01 tanto na edição 2021
> quanto na **edição 2025** (vigente) do [[OWASP Top 10]] — continua em 1º lugar.

Público-alvo: iniciante em segurança ofensiva — assume que você sabe usar o DevTools e
consegue fazer login na aplicação com uma conta própria, comum, sem privilégio nenhum.

Este guia tem duas fases: **Parte 0** é reconhecimento em caixa-preta — descobrir que a
rota existe **sem olhar o código-fonte**, como faria um pentest real ou um atacante
externo; Partes 1–4 são a exploração em si, assumindo que você já sabe (pela Parte 0, ou
por já conhecer o projeto) que `GET /api/usuarios` existe.

## Pré-requisitos

- [[Projeto01/Backend|api01]] rodando em `http://localhost:8000`.
- [[Projeto01/Frontend|client01]] rodando em `http://localhost:4200` (ou a porta usada
  no seu ambiente).
- Uma conta **comum** cadastrada pela tela `/cadastro` (nasce sempre com
  `papel: "usuario"` — item 4 de [[Projeto01/Melhorias]]), ex.:
  `atacante@teste.com` / senha `123456`.
- (Opcional, para a Parte 0) **Burp Suite Community Edition** ou **OWASP ZAP**
  instalado, para interceptar/repetir requisições; e/ou **ffuf**, **gobuster** ou
  **dirsearch** para brute-force de rota.

## O que é a vulnerabilidade, em uma frase

A tela "Usuários" só aparece no menu para quem tem `papel: "admin"` — mas essa é uma
checagem que existe **apenas no frontend**
(`app.component.ts:mostrarAbaUsuarios`). A rota que devolve os dados,
`GET /api/usuarios` (`usuarios/views.py:listar_usuarios`), exige só estar autenticado
(`@jwt_required`) e **nunca** confere `request.usuario['papel']` — qualquer conta
logada, inclusive uma `usuario` comum, recebe a lista completa.

---

## Parte 0 — Descoberta em caixa-preta (reconhecimento, sem olhar o código-fonte)

O objetivo aqui é simular alguém que **não** tem acesso ao repositório — só uma conta
comum e o navegador. "Esconder um link no menu" é inútil contra qualquer uma das
técnicas abaixo, porque o código JavaScript da SPA é **enviado para o navegador de
qualquer usuário**, admin ou não; só a decisão de *renderizar* o link é que muda.

### 0.1 — Ler o bundle JS no DevTools (a técnica mais simples e mais eficaz aqui)

1. Faça login com a conta comum e abra o DevTools (**F12**).
2. Vá na aba **Sources** (Chrome) ou **Debugger** (Firefox) e localize o arquivo
   principal do bundle Angular (`main.js` ou similar, listado em
   `localhost:4201` → pasta do domínio).
3. Dentro do arquivo, use `Ctrl+F` (busca dentro do arquivo aberto) e procure por
   `usuarios` e por `papel`.
4. Você vai encontrar, entre outras coisas:
   - A string literal da URL que o `AdminService` monta: `/usuarios` (concatenada com
     `API_BASE_URL`) — revelando que existe um endpoint de listagem.
   - O trecho equivalente a `papel === "admin"`, usado por `mostrarAbaUsuarios` —
     revelando que a UI decide visibilidade com base nesse claim, e te dando a pista de
     que só falta você *ter* esse claim (ou chamar a rota sem precisar dele, que é
     exatamente o que a Parte 2 confirma).
5. Essa é a técnica mais direta porque o bundle **não é minificado o suficiente** para
   esconder nomes de rota — e mesmo quando é (nomes de variável curtos tipo `a`, `b`),
   as *strings* literais de URL (`"/usuarios"`, `"/tarefas"`) sobrevivem à minificação,
   já que não podem ser renomeadas.

### 0.2 — Automatizar a extração de endpoints do JS

Em uma aplicação maior, procurar manualmente fica inviável — existem ferramentas feitas
pra isso:

| Ferramenta | O que faz |
|---|---|
| **LinkFinder** | Aplica regex sobre arquivos JS para listar todos os paths/URLs encontrados — rode contra o `main.js` baixado (`curl http://localhost:4201/main.js -o main.js && python linkfinder.py -i main.js -o cli`). |
| **JSMiner** / **SecretFinder** (extensões de Burp) | Fazem a mesma varredura automaticamente enquanto você navega pela aplicação com o proxy ativo. |

### 0.3 — Proxy de interceptação (Burp Suite / OWASP ZAP)

1. Configure o navegador para passar o tráfego pelo Burp (ou ZAP) e ative a captura.
2. Navegue normalmente pela aplicação logado como a conta comum — o proxy registra
   **todas** as requisições reais (Network passivo).
3. Use o **spider/crawler** da ferramenta para seguir todos os links e formulários
   automaticamente, catalogando rotas que você nem visitou manualmente.
4. No histórico (Burp: aba *HTTP history*; ZAP: *Sites*), procure por padrões
   `/api/...` e note quais já foram chamados pela UI (`/api/login`, `/api/tarefas`,
   `/api/usuarios/me`) — qualquer rota do mesmo prefixo que você **não** viu sendo
   chamada (como `/api/usuarios` sem `/me`) é candidata a testar manualmente, igual à
   Parte 2.

### 0.4 — Brute-force de rota (quando não há bundle JS legível, ex. API pura sem SPA)

Mesmo sem conseguir ler um bundle, dá para *adivinhar* rotas plausíveis testando uma
wordlist contra o prefixo conhecido:

```bash
ffuf -u http://localhost:8000/api/FUZZ -w caminho/para/wordlist-api.txt \
  -H "Authorization: Bearer <seu-token>"
```

Wordlists como as do **SecLists** (`Discovery/Web-Content/api/`) já têm nomes comuns
(`users`, `admin`, `accounts`...) que, em português, mapeiam para o que este projeto usa
(`usuarios`). Ferramentas equivalentes: **gobuster** (`gobuster dir`), **dirsearch**,
**wfuzz**.

### 0.5 — Postman/Insomnia

Depois de identificar candidatos (por qualquer um dos métodos acima), organize-os numa
coleção do Postman/Insomnia com seu token salvo numa variável de ambiente — facilita
repetir e documentar os testes da Parte 2 em diante sem reescrever o `curl` toda vez.

---

## Parte 1 — Confirmar que a aba está escondida

1. Acesse `/cadastro` e crie uma conta comum (`atacante@teste.com` / `123456`).
2. Faça login com ela.
3. Observe o menu de navegação: **não há** link "Usuários" — só Login, Criar usuário,
   Kanban e Sobre. Até aqui, parece que o acesso está de fato restrito.

## Parte 2 — Pegar o próprio token e chamar a API direto

1. Com a conta comum logada, abra o Console do DevTools (**F12** → **Console**) e rode:
   ```js
   localStorage.getItem('auth_token')
   ```
2. Copie o token retornado.
3. No terminal (ou no próprio Console, via `fetch`), chame a rota que alimenta a tela
   de admin:
   ```bash
   curl http://localhost:8000/api/usuarios \
     -H "Authorization: Bearer <token-copiado>"
   ```
   ou, direto no Console do navegador (reaproveitando a sessão já logada):
   ```js
   fetch('http://localhost:8000/api/usuarios', {
     headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` }
   }).then(r => r.json()).then(console.log)
   ```
4. **Resultado**: `200`, com a lista completa de usuários cadastrados no sistema —
   incluindo contas com `"papel": "admin"` — mesmo logado como uma conta sem nenhum
   privilégio.

## Parte 3 — Usar o filtro para reconhecimento direcionado

A mesma rota aceita `?q=<termo>`, útil para um atacante que já sabe o que procura:

```bash
curl "http://localhost:8000/api/usuarios?q=admin" \
  -H "Authorization: Bearer <token-copiado>"
```

Isso devolve só as contas cujo nome, sobrenome ou email contenham "admin" —
reconhecimento rápido de quais contas valem mais a pena atacar primeiro (ex.: tentar
quebrar o hash MD5 dessas contas específicas, reforçando
[[Projeto01/Ataque-A04-MD5SemSalt]], ou tentar credenciais fracas/reutilizadas contra o
email encontrado).

## Parte 4 — Confirmando que a UI nunca foi a barreira real

Para deixar claro que remover o link do menu nunca teria sido suficiente: navegue
manualmente para `http://localhost:4201/usuarios` (ou a porta do seu `client01`) ainda
logado como a conta comum. A tela carrega normalmente e mostra a tabela completa de
usuários — não existe nenhum guard de rota no Angular que bloqueie o acesso à página em
si, só a visibilidade do link no menu.

## Passo final — Documentar o achado

- **Vulnerabilidade**: ausência de checagem de papel (RBAC) em `GET /api/usuarios`
  (`usuarios/views.py:listar_usuarios`); controle de acesso implementado só no frontend
  (`app.component.ts:mostrarAbaUsuarios`).
- **Passos para reproduzir**: Partes 1–4 acima.
- **Evidência**: print do menu sem o link "Usuários" (Parte 1) vs. print da resposta
  completa da API usando o token da mesma conta (Parte 2).
- **Impacto**: qualquer usuário autenticado (mesmo recém-cadastrado, sem privilégio
  algum) enumera todos os usuários do sistema, incluindo quais contas têm papel `admin`
  — informação de reconhecimento valiosa para direcionar outros ataques (cracking de
  senha, engenharia social, tentativa de credential stuffing contra o email encontrado).
- **Causa raiz**: a decisão de "quem pode ver isso" foi tomada só na camada de
  apresentação (esconder um link), nunca replicada na camada que efetivamente processa
  e devolve o dado sensível.

## Mitigação

Já detalhado em [[Projeto01/Vulnerabilidades]] (item 5):

1. Em `listar_usuarios`, depois de `jwt_required`, checar explicitamente
   `request.usuario['papel'] == 'admin'` e devolver `403` caso contrário:
   ```python
   @jwt_required
   def listar_usuarios(request):
       if request.usuario['papel'] != 'admin':
           return JsonResponse({'erro': 'Acesso restrito a administradores.'}, status=403)
       ...
   ```
2. Nunca confiar em "esconder um elemento de UI" como controle de acesso — regra geral,
   não só deste caso: toda autorização real precisa ser reforçada no backend.
3. Opcionalmente, adicionar um guard de rota no Angular (`CanActivateFn` em
   `app.routes.ts`) que redirecione não-admins para fora de `/usuarios` — melhora a
   experiência (evita carregar uma tela vazia/com erro), mas não substitui o item 1.
