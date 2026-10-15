# Projeto01 — Melhorias em relação ao [[Projeto00]]

Este documento cobre **só** o que melhorou de [[Projeto00]] para [[Projeto01]] — a
contrapartida de [[Projeto01/Vulnerabilidades]], que cobre o que continua (ou passou a
ser) explorável. A base de comparação é sempre o [[Projeto00]] (o único projeto anterior
ao [[Projeto01]]); nenhuma melhoria aqui é comparada com algo além dele.

---

## 1. Vulnerabilidades corrigidas

### IDOR nas rotas de tarefas (item 3 de [[Projeto00/Vulnerabilidades]])

**Corrigida nas rotas de `tarefas`.** O [[Projeto00/Backend|api00]] nunca checava quem
fazia a requisição — qualquer `usuario_id`/`tarefa_id` na URL era aceito sem dono
verificado. No [[Projeto01/Backend|api01]]:

- `listar_tarefas_por_usuario`: `403` se o `usuario_id` da URL não bater com o `id` do
  JWT autenticado.
- `tarefa_detalhe` (`PUT`/`DELETE`): `404` se `tarefa.usuario_id` não bater com o `id`
  do JWT.
- `criar_tarefa`: o `usuario_id` da tarefa criada vem sempre do JWT, nunca do corpo da
  requisição.

Implementado em `usuarios/decorators.py:jwt_required` +
`usuarios/jwt_utils.py:verificar_token` (valida a assinatura HMAC antes de confiar em
qualquer claim) + checagens de posse em `tarefas/views.py`. Veja a exploração original
(ainda documentada como referência histórica) em
[[Projeto00/Ataque-A01-BrokenAccessControl]] — os passos daquele guia **não funcionam
mais** contra o [[Projeto01/Backend|api01]].

**Ressalva**: a correção fecha o vetor "trocar o id na URL/corpo". Ela **não** fecha o
SQL Injection do filtro por nome (item 4 de [[Projeto01/Vulnerabilidades]]), que consegue
contornar essa mesma checagem de posse por uma causa raiz diferente — ver
[[Projeto01/Ataque-A05-SQLInjectionFiltro]].

### Escalonamento de privilégio no cadastro (vulnerabilidade própria do [[Projeto01]], não herdada do [[Projeto00]])

**Corrigida.** Diferente dos demais itens desta seção, esta falha não existia no
[[Projeto00]] (que não tinha papéis de usuário) — foi introduzida e corrigida dentro do
próprio [[Projeto01]]. O formulário de cadastro (`cadastro.component.html`) deixava a
pessoa escolher livremente seu `papel` (`usuario`/`admin`/`gerente`), e
`usuarios/views.py:cadastrar_usuario` aceitava esse valor do corpo da requisição sem
nenhuma checagem. Agora:
- O `<select name="papel">` foi removido do formulário de cadastro.
- `cadastrar_usuario` grava sempre `papel=Usuario.PAPEL_USUARIO`, ignorando qualquer
  `papel` enviado no corpo da requisição.

Não há mais um guia de ataque dedicado para esta falha (removido do vault): como ela não
é mais exploravel contra o [[Projeto01/Backend|api01]] atual, não há passo a passo a
manter.

### Ausência de autenticação (item 4 de [[Projeto00/Vulnerabilidades]])

**Corrigida nas rotas de `tarefas` e em `GET /api/usuarios/me`.** O
[[Projeto00/Backend|api00]] não tinha nenhum conceito de sessão/token no backend — "estar
logado" só existia no frontend. O [[Projeto01/Backend|api01]] agora emite um JWT no login
(`usuarios/views.py:login` → `jwt_utils.py:gerar_token`) e exige
`Authorization: Bearer <token>` válido em toda rota de `tarefas` e na nova rota
`GET /api/usuarios/me`, via `jwt_required`.

**Ressalva**: a autenticação em si não expira (item 2 de [[Projeto01/Vulnerabilidades]])
e as rotas públicas (`cadastrar_usuario`, `login`) continuam sem exigir token, de
propósito — são o ponto de entrada de quem ainda não tem um.

### Senha nunca mais devolvida em resposta JSON (recomendação pendente do item 1 de [[Projeto00/Vulnerabilidades]])

**Corrigida.** O [[Projeto00/Backend|api00]] devolvia o campo `senha` (em texto puro) em
toda resposta de `cadastrar_usuario`/`login` — já apontado como mitigação pendente no
próprio guia [[Projeto00/Ataque-A04-CryptographicFailures]]. `usuarios/views.py:usuario_para_json`
no [[Projeto01/Backend|api01]] não inclui mais o campo `senha`/hash em nenhuma resposta.

### Armazenamento de dados sensíveis no `localStorage` (item 9 de [[Projeto00/Vulnerabilidades]])

**Melhorada, não totalmente corrigida.** O [[Projeto00/Frontend|client00]] guardava o
objeto `Usuario` completo em `localStorage`, **incluindo a senha em texto puro**. O
[[Projeto01/Frontend|client01]] guarda só a string do JWT (`AuthService`, chave
`auth_token`) — a senha não é mais persistida no navegador em nenhum formato.

**O que ainda falta**: o token continua acessível a qualquer JavaScript da página
(inclusive um XSS, item 10 de [[Projeto00/Vulnerabilidades]], ainda presente sem
alteração) e nunca expira — ver itens 2 e 3 de [[Projeto01/Vulnerabilidades]] e o guia
[[Projeto01/Ataque-A07-TokenSemExpiracao]]. Mover para cookie `httpOnly` resolveria o
que falta.

### Senha em texto puro no banco (item 1 de [[Projeto00/Vulnerabilidades]])

**Melhorada, não corrigida — substituída por uma vulnerabilidade mais fraca, não
eliminada.** O [[Projeto00/Backend|api00]] gravava `Usuario.senha` exatamente como
digitada. O [[Projeto01/Backend|api01]] agora grava `hash_md5(senha)`
(`usuarios/views.py:hash_md5`) — um acesso ao banco não revela mais a senha
**instantaneamente e sem esforço**, como no [[Projeto00]]. Mas MD5 sem salt ainda é
quebrável em segundos/minutos contra senhas comuns (rainbow table/dicionário) — não é uma
correção da causa raiz "senha recuperável a partir do que está no banco", só um
obstáculo adicional. Continua catalogada como vulnerabilidade própria do
[[Projeto01]] — ver item 1 de [[Projeto01/Vulnerabilidades]] e
[[Projeto01/Ataque-A04-MD5SemSalt]].

---

## 2. Hardening e qualidade (sem ser correção direta de um item numerado)

- **`authInterceptor`** (`client01/src/app/core/interceptors/auth.interceptor.ts`, novo):
  anexa `Authorization: Bearer <token>` automaticamente em toda requisição HTTP — o
  [[Projeto00/Frontend|client00]] não tinha nenhum interceptor, e não precisava, por não
  haver token.
- **`GET /api/usuarios/me`** (`usuarios/views.py:usuario_logado`, novo): dá ao frontend
  uma forma de obter dados do usuário logado **validados pelo backend** em vez de só
  confiar no payload do JWT decodificado sem verificação no cliente. O
  [[Projeto01/Frontend|client01]] já usa essa rota para exibir o nome no cabeçalho do
  Kanban, em vez do payload cru.
- **Tratamento de erro de autenticação no Kanban** (`kanban.component.ts:tratarErroAutenticacao`,
  novo): em qualquer `401` de `tarefas`, desloga e redireciona para `/login` — não
  existia no [[Projeto00/Frontend|client00]] porque não havia nada que pudesse devolver
  `401`.
- **Validação de assinatura centralizada** (`usuarios/jwt_utils.py:verificar_token` +
  `usuarios/decorators.py:jwt_required`, novos): um único ponto de verificação
  reutilizado por `tarefas` e por `usuarios`, em vez de cada view reimplementar sua
  própria checagem.

---

## Resumo

| #   | Melhoria                                                                                 | Categoria                                                                       | Item correspondente em [[Projeto01/Vulnerabilidades]]                   |
| --- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 1   | IDOR corrigido nas rotas de `tarefas`                                                    | Vulnerabilidade corrigida                                                       | — (ressalva: item 4, SQLi, contorna essa checagem por outra causa raiz) |
| 2   | Autenticação real (JWT) exigida em `tarefas` e `/usuarios/me`                            | Vulnerabilidade corrigida                                                       | item 2 (expiração ainda pendente)                                       |
| 3   | Senha removida das respostas JSON                                                        | Vulnerabilidade corrigida                                                       | — (totalmente resolvido)                                                |
| 4   | Escalonamento de privilégio no cadastro corrigido (`papel` não é mais aceito do cliente) | Vulnerabilidade corrigida (introduzida e corrigida dentro do próprio Projeto01) | — (totalmente resolvido)                                                |
| 5   | Objeto de usuário cru removido do `localStorage` (agora é só o JWT)                      | Melhoria parcial                                                                | itens 2 e 3 (token ainda exposto e sem expiração)                       |
| 6   | Senha em texto puro → hash MD5 sem salt                                                  | Melhoria parcial                                                                | item 1 (hash ainda fraco)                                               |
| 7   | `authInterceptor`, `GET /api/usuarios/me`, tratamento de `401` no Kanban                 | Hardening/qualidade                                                             | —                                                                       |

Nenhuma destas comparações se estende a projetos anteriores ao [[Projeto00]] — não
existem, [[Projeto00]] é a baseline original do laboratório.
