# Projeto02 — Vulnerabilidades

Lista das vulnerabilidades propositais do [[Projeto02]] (backend `api02` + frontend
`client02`) que continuam exploráveis. Todas as falhas de autenticação/autorização do
[[Projeto01]], a SQL Injection no filtro de tarefas (também herdada do [[Projeto01]]) e o
XSS armazenado na descrição da tarefa (herdado desde o [[Projeto00]]) foram corrigidos
neste projeto — ver [[Projeto02/Melhorias]] para a narrativa completa de cada correção.
Este documento lista só o que **permanece**. Para arquitetura e rotas ver
[[Projeto02/Backend]] e [[Projeto02/Frontend]].

Cada item segue o formato: **o que é** → **como explorar** → **como mitigar**.

> **Nota sobre a funcionalidade de preview de link**: a tarefa ganhou um campo `url`
> opcional cujo título o backend busca (`tarefas/link_preview.py`) — o tipo de recurso
> que, sem cuidado, normalmente seria um vetor de SSRF (Server-Side Request Forgery:
> usar o backend para alcançar endereços internos da rede). Não está listado como
> vulnerabilidade aqui porque nasceu com as defesas aplicadas desde a primeira versão
> (allowlist de esquema, validação de IP público, conexão fixada no IP validado,
> revalidação de redirecionamentos) — ver [[Projeto02/Backend]] e
> [[Projeto02/Melhorias]].

---

Nenhuma vulnerabilidade **própria** deste projeto (originada no [[Projeto01]] ou
corrigida aqui pela primeira vez) permanece — ver [[Projeto02/Melhorias]] para a
correção de cada uma: as quatro falhas de autenticação/autorização do [[Projeto01]], a
SQL Injection no filtro de tarefas (também item do [[Projeto01]]) e o XSS armazenado na
descrição da tarefa (herdado desde o [[Projeto00]], nunca tocado até aqui). O que resta
é só o que nenhum destes dois projetos jamais mexeu:

## Vulnerabilidades herdadas do [[Projeto00]], sem alteração

Continuam presentes e sem nenhuma mudança de forma — ver
[[Projeto00/Vulnerabilidades]]:

- **Item 2** — Painel `/admin/` exposto sem reforço.
- **Item 7** — `DEBUG = True` em produção + `SECRET_KEY` commitada (e, agora, também o
  fallback de desenvolvimento de `JWT_SECRET_KEY`, pela mesma razão — ver
  [[Projeto02/Backend]]).
- **Item 8** — Falta de validação/sanitização de entrada (mass assignment).

Os itens 5 (CSRF desativado), 6 (CORS liberado) e 10 (XSS armazenado) daquele documento,
que seguiam inalterados até o [[Projeto01]], foram todos corrigidos neste projeto — ver
[[Projeto02/Melhorias]]. O item 5 em particular passa de "não se aplicava na prática"
(nas primeiras versões deste projeto, quando só `/token/refresh`/`/logout` dependiam de
cookie) para **genuinamente corrigido e ampliado**: desde que o access token também
passou a viver só em cookie `HttpOnly`, toda rota que depende de `jwt_required`
(tarefas, `/usuarios/me`, `listar_usuarios`) autentica por cookie e exige
`X-XSRF-TOKEN` — não só as duas rotas originais (ver [[Projeto02/Backend]] e
[[Projeto02/Melhorias]]).

---

## Resumo

Classificação pela edição vigente do [[OWASP Top 10]] (**2025**).

Nenhuma vulnerabilidade própria deste projeto permanece — a tabela de itens numerados
fica vazia de propósito. O que resta é só o que já era herdado do [[Projeto00]] sem
nenhuma mudança (ver lista acima): itens 2, 7 e 8 daquele documento — painel `/admin/`
exposto, `DEBUG`/segredos commitados, e falta de validação de entrada (mass assignment),
todos classificados em [[Projeto00/Vulnerabilidades]].

Todas as vulnerabilidades próprias do [[Projeto01]] (hash MD5 sem salt, token sem
expiração, token em `localStorage` sem verificar assinatura, Broken Access Control na
listagem de usuários, e SQL Injection no filtro de tarefas) foram corrigidas, assim como
o XSS armazenado herdado desde o [[Projeto00]] — ver [[Projeto02/Melhorias]] para o
detalhamento de cada uma. Isso faz do [[Projeto02]] o primeiro projeto do laboratório em
que nenhuma vulnerabilidade própria ou do projeto imediatamente anterior permanece
explorável — mas ainda não deve ser tomado como referência de "aplicação totalmente
segura": as três falhas herdadas do [[Projeto00]] listadas acima (itens 2, 7 e 8)
continuam exploráveis, por serem propositalmente independentes do eixo de
autenticação/autorização, injeção e XSS deste projeto. A progressão de hardening deve
continuar em projetos posteriores, linkando de volta para cá.
