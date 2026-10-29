# Projeto02 — Visão

## Objetivo

Projeto **02** parte de uma cópia exata do [[Projeto01]] (mesmo backend, mesmo
frontend, byte a byte) e evolui especificamente a camada de **autenticação e
autorização**, implementando as recomendações de
[[Projeto02/SegurancaAutorizacaoAcesso]] — um guia didático escrito antes do código,
explicando JWT, papéis, criptografia segura, refresh token, expiração, validação de
backend e persistência em cookie `HttpOnly`. Diferente do [[Projeto01]] (que trocava
algumas vulnerabilidades por outras), o Projeto02 é deliberadamente um passo de
**hardening real**, com foco inicial num eixo específico — quem é o usuário
(autenticação) e o que ele pode fazer (autorização) — mas que também fechou, ao longo do
projeto, a SQL Injection do filtro de tarefas e o XSS armazenado na descrição da tarefa,
duas falhas fora desse eixo que vinham sem alteração desde projetos anteriores. Ver
[[Projeto02/Vulnerabilidades]] para o que continua explorável e [[Projeto02/Melhorias]]
para o detalhamento de cada correção.

O projeto também ganha uma funcionalidade nova — preview de link na tarefa — construída
desde o início com defesas contra **SSRF** (Server-Side Request Forgery), já que é o
próprio backend quem busca a URL informada pelo usuário. Diferente do eixo de
autenticação/autorização (que corrige falhas que já existiam no [[Projeto01]]), esta é
uma funcionalidade nova que nasce protegida, não uma correção de algo pré-existente —
ver [[Projeto02/Backend]] (seção "Preview de link") e
[[Projeto02/Melhorias]].

## Descrição funcional

Mesmo software de acompanhamento de tarefas no estilo Jira do [[Projeto01]]: usuários se
cadastram, fazem login e gerenciam suas próprias tarefas em um quadro Kanban.

### Telas

- **Login** — autenticação do usuário (email + senha).
- **Criação de usuário** — cadastro de um novo usuário (sem campo de papel).
- **Quadro Kanban** — tarefas do usuário logado, organizadas por estado, com nome do
  usuário no cabeçalho e filtro de tarefas por nome.
- **Usuários** — lista todos os usuários cadastrados, com filtro por nome/sobrenome/
  email. Só aparece no menu para quem está logado como `admin` **e**, agora, só é
  realmente servida pelo backend para quem de fato tem esse papel (ver "O que mudou",
  item 4).
- **Sobre** — tela institucional, atualizada para descrever o estado atual do projeto.

### O que mudou em relação ao [[Projeto01]]

1. **Senha com hash seguro (PBKDF2 + salt)** — `Usuario.senha` deixa de guardar
   `md5(senha)` e passa a guardar o resultado de
   `django.contrib.auth.hashers.make_password()`, verificado no login com
   `check_password()`. Fecha a causa raiz que o MD5 sem salt deixava aberta (reversão
   via rainbow table/dicionário). Ver [[Projeto02/Melhorias]].
2. **Access token (JWT) com expiração real** — o payload passa a ter `iat` e `exp`
   (15 minutos, `ACCESS_TOKEN_TTL_SEGUNDOS`), e `verificar_token()` rejeita qualquer
   token sem `exp` ou já expirado. Um token roubado agora tem janela de uso limitada.
3. **Refresh token opaco, revogável e rotacionado** — o login passa a emitir também um
   refresh token (não é um JWT), persistido no backend como hash SHA-256
   (`usuarios.RefreshToken`) e entregue só via cookie `HttpOnly`. `POST
   /api/token/refresh` troca um refresh token válido por um access token novo **e** por
   um refresh token novo, invalidando o anterior (rotação); reuso de um token já
   rotacionado revoga toda a sessão do usuário, por suspeita de roubo. `POST
   /api/logout` revoga o refresh token de verdade no backend.
4. **Papel exigido também no backend** — `GET /api/usuarios` (aba "Usuários") passa a
   exigir `@papel_required(Usuario.PAPEL_ADMIN)`, além de `jwt_required`. A aba
   continua escondida na UI para quem não é admin, mas agora isso também é garantido no
   servidor — chamar a rota direto como usuário comum devolve `403`.
5. **Access token guardado em cookie `HttpOnly`, nunca manuseado pelo frontend** —
   `AuthService` não usa `localStorage` nem mantém o token em memória; tanto o access
   quanto o refresh token vivem só em cookies `HttpOnly` setados pelo backend, fora do
   alcance de JavaScript (inclusive um XSS). Os dados exibidos na UI (nome, papel) vêm de
   um JSON que o próprio backend já devolve validado, nunca de um payload de JWT
   decodificado no cliente.
6. **CORS restrito à origem do frontend** — `CORS_ALLOW_ALL_ORIGINS = True` (herdado sem
   alteração do [[Projeto00]] e do [[Projeto01]]) dá lugar a
   `CORS_ALLOWED_ORIGINS = ['http://localhost:4200']` + `CORS_ALLOW_CREDENTIALS = True`,
   necessário para o cookie do refresh token funcionar entre origens — e que também fecha
   o item 6 de [[Projeto00/Vulnerabilidades]].
7. **`CsrfViewMiddleware` ativado, protegendo toda rota que autentica por cookie** —
   como o access token também passou a viver num cookie `HttpOnly` (item 5), toda rota
   que depende de `jwt_required` (tarefas, `/usuarios/me`, `listar_usuarios`), não só
   `/token/refresh`/`/logout`, exige o header `X-XSRF-TOKEN`. `login` e o cadastro
   público continuam isentos, de propósito, por não lerem nenhum cookie de autenticação
   (ver [[Projeto02/Melhorias]]).
8. **`JWT_SECRET_KEY` independente do `SECRET_KEY` do Django** — no [[Projeto01]], a
   mesma `SECRET_KEY` insegura e commitada assinava tanto o Django quanto os JWTs; agora
   são chaves separadas (ainda lidas de variável de ambiente com fallback de
   desenvolvimento).
9. **SQL Injection no filtro de tarefas corrigida** (item 4 de
   [[Projeto01/Vulnerabilidades]]) — a consulta por f-string em
   `listar_tarefas_por_usuario` dá lugar a
   `Tarefa.objects.filter(nome__icontains=nome_filtro)`, parametrizado pelo ORM do
   Django. Esta falha era, de propósito, independente do eixo de autenticação/
   autorização deste projeto, mas foi corrigida mesmo assim — ver [[Projeto02/Melhorias]].
10. **XSS armazenado na descrição da tarefa corrigido** (item 10 de
    [[Projeto00/Vulnerabilidades]], herdado sem alteração até o [[Projeto01]]) — o
    `bypassSecurityTrustHtml`/`[innerHTML]` do Kanban dá lugar a uma interpolação de
    texto padrão (`{{ tarefa.descricao }}`), que o Angular escapa automaticamente. Ver
    [[Projeto02/Melhorias]].
11. **Preview de link na tarefa (novo, não existia no [[Projeto01]])** — campo opcional
    de URL na tarefa; o backend busca o HTML dessa URL e extrai o `<title>` para exibir
    no card do Kanban. Como é o próprio servidor quem faz essa requisição de saída a
    partir de um valor controlado pelo usuário, é um vetor clássico de SSRF — por isso a
    busca (`tarefas/link_preview.py`) só aceita `http`/`https`, resolve e valida que
    **todos** os IPs do host são públicos antes de conectar, conecta direto no IP já
    validado (evita DNS rebinding), revalida cada redirecionamento, e limita tempo e
    tamanho da resposta. Ver [[Projeto02/Backend]].

### Usuário

Campos de cadastro: Nome, Sobrenome, Data de nascimento (opcional), Email, Senha. O
papel não é um campo do formulário — toda conta nasce com `papel: "usuario"` (herdado do
[[Projeto01]]).

### Tarefas

Idêntico ao [[Projeto01]]: nome, descrição, data de prazo, estado (`esperando`,
`em_andamento`, `concluido`), associada a um usuário.

## Stack

- **Frontend**: Angular + TypeScript (`client02`)
- **Backend**: Django + Python (`api02`)

## Modelo de dados (alto nível)

**Usuário**

| Campo           | Tipo                                 |
| --------------- | ------------------------------------ |
| id              | inteiro                              |
| nome            | texto                                |
| sobrenome       | texto                                |
| data_nascimento | data (opcional)                      |
| email           | texto                                |
| senha           | texto (hash PBKDF2 + salt)           |
| papel           | enum (`usuario`, `admin`, `gerente`) |
´´´

**RefreshToken** (novo)

| Campo | Tipo |
|---|---|
| id | inteiro |
| usuario_id | referência ao usuário |
| token_hash | texto (SHA-256 do token, não o token em si) |
| criado_em | data/hora |
| expira_em | data/hora |
| revogado_em | data/hora (opcional) |

**Tarefa**

| Campo | Tipo |
|---|---|
| id | inteiro |
| usuario_id | referência ao usuário |
| nome | texto |
| descricao | texto |
| data_prazo | data |
| estado | enum (`esperando`, `em_andamento`, `concluido`) |
| url | texto (opcional, link de referência) |
| url_titulo | texto (opcional, título obtido pelo backend — nunca pelo cliente) |

## Aviso

Este projeto é exclusivamente educacional. As vulnerabilidades aqui presentes (as que
permanecem — ver [[Projeto02/Vulnerabilidades]]) são intencionais e **não devem** ser
replicadas em sistemas reais/produção.
