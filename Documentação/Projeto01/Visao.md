# Projeto01 — Visão

## Objetivo

Projeto **01** parte de um clone do [[Projeto00]] (mesma stack, mesmas telas, mesma
descrição funcional) e evolui algumas decisões de implementação — trocando algumas
vulnerabilidades por outras, de forma deliberada, para servir de segundo ponto de
comparação no laboratório de evolução de segurança. **Não é uma versão totalmente
segura** do Projeto00: algumas falhas mudam de forma, outras são mantidas, e novas são
introduzidas — mas vulnerabilidades reais também foram corrigidas. Ver
[[Projeto01/Vulnerabilidades]] para o que continua explorável e [[Projeto01/Melhorias]]
para o que foi corrigido.

## Descrição funcional

Mesmo software de acompanhamento de tarefas no estilo Jira do [[Projeto00]]: usuários se
cadastram, fazem login e gerenciam suas próprias tarefas em um quadro Kanban.

### Telas

- **Login** — autenticação do usuário (email + senha).
- **Criação de usuário** — cadastro de um novo usuário; o papel (role) não é
  selecionável nesta tela (sempre nasce `usuario`, ver item 4 abaixo).
- **Quadro Kanban** — tarefas do usuário logado, organizadas por estado, com o nome do
  usuário logado exibido no cabeçalho e uma aba de filtro de tarefas por nome.
- **Usuários** (nova) — lista todos os usuários cadastrados, com filtro por nome/
  sobrenome/email. Só aparece no menu para quem está logado como `admin`.
- **Sobre** — tela institucional/informativa sobre o projeto.

### O que mudou em relação ao [[Projeto00]]

1. **Senha com hash MD5 sem salt** — em vez de texto puro, `Usuario.senha` agora guarda
   `md5(senha)`. Ainda inseguro (MD5 é rápido de quebrar via rainbow tables/força bruta,
   e sem salt hashes repetidos revelam senhas reutilizadas), mas uma camada acima do
   Projeto00.
2. **Sessão via JWT no `localStorage`** — o login devolve um JWT (HS256, assinado com a
   mesma `SECRET_KEY` do Django) em vez do objeto `Usuario` cru. O frontend guarda só o
   token (chave `auth_token`) e decodifica o payload (sem verificar assinatura) para
   exibir dados do usuário logado.
3. **Nome do usuário logado no Kanban** — o cabeçalho do quadro mostra "Olá, `<nome>`",
   lido do payload do token.
4. **Papéis de usuário** — `Usuario.papel` agora existe, com três valores: `usuario`,
   `admin`, `gerente`. Todo cadastro público nasce com `usuario`, sempre — o formulário
   não oferece (nem o backend aceita) escolher outro papel. Ver [[Projeto01/Melhorias]].
5. **Token sem expiração** — o JWT emitido não tem claim `exp` e o backend nunca o
   invalida ou verifica nas demais rotas.
6. **Filtro de tarefas por nome no Kanban** — nova aba de busca que filtra as tarefas do
   usuário logado pelo nome digitado, implementada no backend com SQL concatenado sem
   parametrização.
7. **IDOR corrigido nas rotas de tarefas e usuários** — todas as rotas de `tarefas`, e a
   nova rota `GET /api/usuarios/me`, agora exigem um JWT válido
   (`Authorization: Bearer <token>`, verificado por assinatura) e usam o `id` do
   token — nunca um valor vindo da URL ou do corpo da requisição — para decidir de quem
   são os dados lidos/criados/editados/apagados. O nome exibido no Kanban passou a vir
   dessa rota validada, em vez do payload do JWT decodificado sem verificação. Ver
   [[Projeto01/Melhorias]].
8. **Aba "Usuários" (admin) sem checagem de papel no backend** — nova tela lista todos
   os usuários cadastrados, com filtro. Só aparece no menu para quem está logado como
   `admin` — mas isso é decidido só no frontend; a rota `GET /api/usuarios` exige
   apenas estar autenticado (`jwt_required`), sem conferir o papel. Qualquer usuário
   comum que chame a rota direto lê a lista completa. Ver
   [[Projeto01/Vulnerabilidades]] item 5.

### Usuário

Campos de cadastro:
- Nome
- Sobrenome
- Data de nascimento (opcional)
- Email
- Senha

O papel não é um campo do formulário — toda conta nasce com `papel: "usuario"` (ver
item 4 de "O que mudou", acima).

### Tarefas

Idêntico ao [[Projeto00]]: nome, descrição, data de prazo, estado (`esperando`,
`em_andamento`, `concluido`), associada a um usuário.

## Stack

- **Frontend**: Angular + TypeScript (`client01`)
- **Backend**: Django + Python (`api01`)

## Modelo de dados (alto nível)

**Usuário**
| Campo | Tipo |
|---|---|
| id | inteiro |
| nome | texto |
| sobrenome | texto |
| data_nascimento | data (opcional) |
| email | texto |
| senha | texto (hash MD5, sem salt) |
| papel | enum (`usuario`, `admin`, `gerente`) |

**Tarefa**
| Campo | Tipo |
|---|---|
| id | inteiro |
| usuario_id | referência ao usuário |
| nome | texto |
| descricao | texto |
| data_prazo | data |
| estado | enum (`esperando`, `em_andamento`, `concluido`) |

## Aviso

Este projeto é exclusivamente educacional. As vulnerabilidades aqui presentes são
intencionais e **não devem** ser replicadas em sistemas reais/produção.
