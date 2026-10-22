# Projeto02 — Vulnerabilidades

Lista das vulnerabilidades propositais do [[Projeto02]] (backend `api02` + frontend
`client02`) que continuam exploráveis. A maior parte das falhas de autenticação e
autorização do [[Projeto01]] foi corrigida neste projeto — ver
[[Projeto02/Melhorias]] para a narrativa completa de cada correção. Este documento lista
só o que **permanece**. Para arquitetura e rotas ver [[Projeto02/Backend]] e
[[Projeto02/Frontend]].

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

## 1. SQL Injection no filtro de tarefas (herdado, sem alteração)

**Arquivo**: `tarefas/views.py` (`listar_tarefas_por_usuario`),
`client02/src/app/pages/kanban/kanban.component.ts` (`filtrarTarefas`)

Idêntico, caractere por caractere, ao item 4 de [[Projeto01/Vulnerabilidades]] — o termo
digitado no filtro do Kanban continua concatenado direto numa query SQL crua:

```python
query = (
    "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
    "FROM tarefas_tarefa "
    f"WHERE usuario_id = {usuario_id} AND nome LIKE '%{nome_filtro}%'"
)
```

Esta falha é propositalmente **independente** do eixo de autenticação/autorização deste
projeto (ver [[Projeto02/Visao]]) e não foi tocada. Exploração, impacto e mitigação
completos já estão documentados em [[Projeto01/Ataque-A05-SQLInjectionFiltro]] — os
mesmos passos (incluindo o payload `xxx' OR '1'='1' --`) funcionam sem alteração contra
o [[Projeto02/Backend|api02]]. Não há guia de ataque novo para este item; use o do
[[Projeto01]].

**Mitigação**: ver [[Projeto01/Vulnerabilidades]] item 4 (parametrizar a query ou usar o
ORM do Django).

---

## Vulnerabilidades herdadas do [[Projeto00]], sem alteração

Continuam presentes e sem nenhuma mudança de forma — ver
[[Projeto00/Vulnerabilidades]]:

- **Item 2** — Painel `/admin/` exposto sem reforço.
- **Item 7** — `DEBUG = True` em produção + `SECRET_KEY` commitada (e, agora, também o
  fallback de desenvolvimento de `JWT_SECRET_KEY`, pela mesma razão — ver
  [[Projeto02/Backend]]).
- **Item 8** — Falta de validação/sanitização de entrada (mass assignment).
- **Item 10** — XSS armazenado na descrição da tarefa (`bypassSecurityTrustHtml`).

Os itens 5 (CSRF desativado) e 6 (CORS liberado) daquele documento, que seguiam
inalterados até o [[Projeto01]], mudaram neste projeto — **item 6 foi corrigido** (ver
[[Projeto02/Melhorias]]) e **item 5 deixou de se aplicar na prática**: as rotas que
continuam `@csrf_exempt` (`login`, `cadastrar_usuario`, todas as de `tarefas`) autenticam
por header `Authorization`, não por cookie — não há credencial ambiente para uma
requisição forjada em outro site explorar. As únicas rotas que passaram a depender de
cookie (`/token/refresh`, `/logout`) já nascem protegidas por `CsrfViewMiddleware` (ver
[[Projeto02/Backend]] e [[Projeto02/Melhorias]]).

---

## Resumo

Classificação pela edição vigente do [[OWASP Top 10]] (**2025**).

| # | Vulnerabilidade | Classe (OWASP 2025) | Complexidade de exploração |
|---|---|---|---|
| 1 | SQL Injection no filtro de tarefas (herdada do [[Projeto01]]) | A05 Injection | Baixa |

Vulnerabilidades herdadas do [[Projeto00]] sem alteração relevante — ver
[[Projeto00/Vulnerabilidades]] itens 2, 7, 8 e 10. O item 6 daquele documento (CORS
liberado) foi corrigido neste projeto — ver [[Projeto02/Melhorias]]. O item 5 (CSRF
desativado) deixou de representar um risco real, pela ausência de credencial de cookie
nas rotas que continuam isentas — ver nota acima.

Todas as cinco vulnerabilidades próprias do [[Projeto01]] (hash MD5 sem salt, token sem
expiração, token em `localStorage` sem verificar assinatura, e Broken Access Control na
listagem de usuários — faltando só a SQL Injection, item 1 acima, que não foi tocada)
foram corrigidas — ver [[Projeto02/Melhorias]] para o detalhamento de cada uma. Isso faz
do [[Projeto02]] o primeiro projeto do laboratório que é, de fato, uma correção de
causa raiz (não uma troca de vulnerabilidades) no eixo de autenticação e autorização —
mas ainda não deve ser tomado como referência de "aplicação totalmente segura": a SQL
Injection (item 1) e as falhas herdadas do [[Projeto00]] continuam exploráveis. A
progressão de hardening deve continuar em projetos posteriores, linkando de volta para
cá.
