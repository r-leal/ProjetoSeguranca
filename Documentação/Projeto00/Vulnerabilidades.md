# Projeto00 — Vulnerabilidades

Lista das vulnerabilidades propositais do [[Projeto00]] (backend `api00` + frontend
`client00`), ordenadas da mais simples de explorar para a mais complexa. Para
arquitetura e rotas ver [[Projeto00/Backend]] e [[Projeto00/Frontend]]; para o objetivo
do projeto ver [[Projeto00/Visao]].

Cada item segue o formato: **o que é** → **como explorar** → **como mitigar**.

---

## 1. Senhas em texto puro no banco (`Usuario.senha`)

**Arquivo**: `usuarios/models.py`, `usuarios/views.py`

O campo `senha` é um `CharField` armazenado e comparado em texto puro — sem hash, sem
salt:
```python
usuario = Usuario.objects.filter(email=email, senha=senha).first()
```

**Como explorar**: basta acessar o banco (`db.sqlite3`) ou o painel `/admin/` (ver item
2) para ler todas as senhas de todos os usuários diretamente, sem precisar quebrar hash
nenhum. Qualquer vazamento do arquivo `db.sqlite3` ou de um backup expõe credenciais em
claro — que costumam ser reutilizadas em outros sistemas pelos usuários.

**Mitigação**:
- Usar `django.contrib.auth.hashers.make_password()` ao salvar e `check_password()` ao
  autenticar (ou, melhor, usar o próprio sistema `django.contrib.auth.User` com
  `AbstractUser`, já que `django.contrib.auth` já está instalado).
- Nunca devolver o campo de senha (nem o hash) em nenhuma resposta JSON.

---

## 2. Painel `/admin/` exposto sem reforço

**Arquivo**: `api00/urls.py`, `settings.py`

O Django Admin está habilitado em `/admin/`, com `DEBUG = True` e sem
`ALLOWED_HOSTS` restrito (`['*']`).

**Como explorar**: acessar `http://<host>/admin/` e tentar credenciais padrão/fracas de
superusuário (força bruta, já que não há rate limiting nem bloqueio de tentativas). Uma
vez dentro, dá para ler/editar/apagar qualquer `Usuario` e ver as senhas em claro (item
1) — admin vira um atalho direto para o banco inteiro.

**Mitigação**:
- Rate limiting / bloqueio de tentativas de login (ex: `django-axes`).
- Mover a URL do admin para um caminho não óbvio e/ou restringir por IP.
- Exigir MFA para contas de staff/superusuário.
- Nunca rodar com `DEBUG = True` em produção (ver item 7).

---

## 3. Sem autorização — IDOR (Insecure Direct Object Reference)

**Arquivo**: `tarefas/views.py` (`listar_tarefas_por_usuario`, `tarefa_detalhe`),
`usuarios/views.py`

Nenhuma view valida **quem está fazendo a requisição**. `GET
/api/usuarios/<usuario_id>/tarefas` devolve as tarefas de qualquer `usuario_id`
informado na URL; `PUT`/`DELETE /api/tarefas/<tarefa_id>` edita/apaga qualquer tarefa de
qualquer usuário, sem checar dono.

**Como explorar**: autenticado como o usuário `1`, basta trocar o id na URL
(`/api/usuarios/2/tarefas`, `/api/tarefas/57`) para ler, editar ou apagar dados de
outras contas. Não precisa nem de token — é só variar o número.

**Mitigação**:
- Autenticação real por requisição (ver item 4) + checagem de posse: toda view de
  `tarefas` deve confirmar que `tarefa.usuario_id == request.user.id` antes de
  ler/editar/apagar.
- Preferir expor recursos relativos ao usuário autenticado (`/api/me/tarefas`) em vez de
  aceitar o id do usuário como parâmetro de URL vindo do cliente.

---

## 4. Ausência de autenticação de sessão/token

**Arquivo**: `usuarios/views.py` (`login`), todas as views de `tarefas`

O endpoint `login` apenas confere email/senha e devolve o objeto `Usuario` — não gera
sessão, cookie, token JWT nem nada que identifique requisições futuras. Toda view
subsequente roda sem checar **nenhuma** credencial; "estar logado" existe só no
`localStorage` do frontend (ver [[Projeto00/Frontend]]).

**Como explorar**: ignorar completamente a tela de login e chamar a API diretamente
(`curl`/Postman) em qualquer endpoint — tudo funciona sem token, cookie ou header de
autenticação.

**Mitigação**:
- Implementar autenticação real: sessão Django (`django.contrib.auth.login`) ou
  token/JWT (ex: `djangorestframework-simplejwt`).
- Exigir essa credencial em **todas** as views via `@login_required` /
  `IsAuthenticated`, combinando com a checagem de posse do item 3.

---

## 5. CSRF desativado em todas as views (`@csrf_exempt`)

**Arquivo**: todas as views de `usuarios/views.py` e `tarefas/views.py`

Toda view usa `@csrf_exempt`, e o `MIDDLEWARE` nem inclui `CsrfViewMiddleware`.

**Como explorar**: combinado com autenticação por sessão/cookie (quando implementada —
item 4) e CORS liberado (item 6), uma página maliciosa em outro domínio pode disparar
requisições `POST`/`PUT`/`DELETE` autenticadas em nome da vítima sem o conhecimento dela
(Cross-Site Request Forgery) — ex: criar/apagar tarefas, ou trocar o cadastro do usuário
logado.

**Mitigação**:
- Reativar `django.middleware.csrf.CsrfViewMiddleware` e remover os `@csrf_exempt`.
- Se a API usa token de autenticação (Authorization header) em vez de cookie de sessão,
  o risco de CSRF cai bastante — mas o CORS ainda precisa ser restrito (item 6).

---

## 6. CORS liberado para qualquer origem

**Arquivo**: `settings.py` (`CORS_ALLOW_ALL_ORIGINS = True`)

Qualquer site, de qualquer origem, pode fazer requisições à API e ler a resposta via
JavaScript no navegador da vítima.

**Como explorar**: hospedar uma página em outro domínio que faça `fetch()` para a API e
leia a resposta (dados de usuários, tarefas) usando as credenciais/sessão do navegador
da vítima — amplia bastante o impacto do item 5 (CSRF) e de qualquer XSS no frontend.

**Mitigação**:
- Trocar para `CORS_ALLOWED_ORIGINS = [<domínio do client00>]`, nunca `*`, especialmente
  quando a API usa cookies de sessão.

---

## 7. `DEBUG = True` em produção + `SECRET_KEY` commitada

**Arquivo**: `settings.py`

```python
SECRET_KEY = 'django-insecure-x+udn)lvpu*27&j43@r8sr_n4i#^@cynpyfp#s*#v^upl6)tge'
DEBUG = True
```

**Como explorar**: qualquer exceção não tratada (ex: enviar um `usuario_id` inválido,
JSON malformado) devolve a página de debug do Django com stack trace completo —
expondo caminhos do servidor, trechos de código-fonte, variáveis locais e configurações.
A `SECRET_KEY` fixa e versionada no Git permite forjar cookies de sessão assinados e
tokens caso o projeto passe a usá-la para isso.

**Mitigação**:
- `DEBUG = False` em produção, com `ALLOWED_HOSTS` restrito aos domínios reais.
- `SECRET_KEY` fora do repositório, lida de variável de ambiente (`os.environ`) e
  gerada de forma aleatória por ambiente.

---

## 8. Falta de validação/sanitização de entrada (mass assignment)

**Arquivo**: `usuarios/views.py`, `tarefas/views.py`

Os campos do JSON recebido são lidos direto com `.get(...)` e passados ao
`Model.objects.create(...)`/atribuídos ao objeto, sem schema de validação (não usa DRF
serializers nem `forms.Form`). Não há limite de tamanho, tipo ou formato checado além do
que o próprio banco impõe.

**Como explorar**: enviar tipos inesperados (`"data_prazo": "não é uma data"`,
`"estado": "qualquer-string"` fora dos `choices`, corpo gigante) para causar erro 500
(que some com stack trace completo por causa do item 7) ou dados inconsistentes no
banco. Também é possível enviar um `usuario_id` arbitrário em `criar_tarefa` para
atribuir tarefas a qualquer usuário (reforça o item 3).

**Mitigação**:
- Validar entrada com Django Forms ou DRF Serializers antes de tocar no ORM.
- Normalizar erros de validação em respostas `400` controladas, nunca deixar vazar
  exceção crua.

---

## 9. (Frontend) Dados sensíveis em `localStorage`

**Arquivo**: `client00` (ver [[Projeto00/Frontend]])

O "usuário logado" (incluindo os campos devolvidos pelo backend, que hoje incluem a
senha em claro — item 1) fica persistido no `localStorage` do navegador.

**Como explorar**: qualquer XSS no `client00` (ver item 10, abaixo), ou extensão de
navegador maliciosa, lê `localStorage` diretamente via JavaScript e exfiltra os dados —
diferente de cookies `httpOnly`, não há nenhuma barreira.

**Mitigação**:
- Nunca devolver senha/hash na API (resolve a causa raiz, item 1).
- Mover token de sessão para cookie `httpOnly` + `Secure` + `SameSite`, em vez de
  `localStorage`, quando a autenticação real (item 4) for implementada.
- Aplicar práticas de prevenção de XSS no Angular (evitar `innerHTML`/`bypassSecurityTrust*`
  sem sanitização — ver item 10).

---

## 10. XSS Armazenado na descrição da tarefa (`[innerHTML]` sem sanitização)

**Arquivo**: `client00/src/app/pages/kanban/kanban.component.ts` (método
`descricaoHtml`), `kanban.component.html`

A descrição da tarefa, que vem direto do que o usuário digita no formulário (sem
sanitização no backend — item 8), é renderizada assim:
```ts
descricaoHtml(tarefa: Tarefa): SafeHtml {
  return this.sanitizer.bypassSecurityTrustHtml(tarefa.descricao);
}
```
```html
<p [innerHTML]="descricaoHtml(tarefa)"></p>
```
`bypassSecurityTrustHtml` desliga de propósito o sanitizador que o Angular aplicaria por
padrão a qualquer `[innerHTML]` — qualquer HTML/JS salvo na descrição é renderizado sem
filtro para quem quer que abra aquele cartão.

**Como explorar**: cadastrar uma tarefa com uma descrição contendo um elemento com
atributo de evento inline (ex.: `<img src="x" onerror="...">` — uma tag `<script>` pura
**não** executa quando inserida via `innerHTML`, é uma restrição do próprio DOM). O
código dentro do `onerror` roda no contexto da aplicação, podendo ler
`localStorage`/cookies, fazer requisições autenticadas em nome da vítima, ou exfiltrar
dados. Combinado com a falta de checagem de dono nas tarefas (item 3, IDOR), o payload
pode atingir qualquer usuário do sistema, não só quem o criou. Passo a passo completo em
[[Projeto00/Ataque-A05-StoredXSS]].

**Mitigação**:
- Voltar à interpolação padrão do Angular (`{{ tarefa.descricao }}`), que escapa HTML
  automaticamente — suficiente aqui, já que a aplicação não precisa renderizar HTML na
  descrição.
- Se precisar de HTML limitado no futuro, sanitizar com biblioteca dedicada (`DOMPurify`)
  e allowlist estrita, nunca manualmente.
- Validar/limitar o conteúdo da descrição no backend (reforça item 8).

---

## Resumo

Classificação pela edição vigente do [[OWASP Top 10]] (**2025**); entre parênteses, o
código correspondente na edição 2021, para quem já conhece a numeração antiga.

| # | Vulnerabilidade | Classe (OWASP 2025) | Complexidade de exploração |
|---|---|---|---|
| 1 | Senha em texto puro | A04 Cryptographic Failures (era A02 em 2021) | Trivial |
| 2 | Admin exposto sem reforço | A07 Authentication Failures (era A07 em 2021) | Trivial–Baixa |
| 3 | IDOR / falta de autorização | A01 Broken Access Control (era A01 em 2021) | Baixa |
| 4 | Sem autenticação real | A07 Authentication Failures (era A07 em 2021) | Baixa |
| 5 | CSRF desativado | A01 Broken Access Control (era A01 em 2021) | Média |
| 6 | CORS liberado | A02 Security Misconfiguration (era A05 em 2021) | Média |
| 7 | `DEBUG=True` + `SECRET_KEY` exposta | A02 Security Misconfiguration (era A05 em 2021) | Média |
| 8 | Falta de validação de entrada | A05/A06 Injection / Insecure Design (era A03/A04 em 2021) | Média–Alta |
| 9 | Dados sensíveis em `localStorage` | A04 Cryptographic Failures (era A02 em 2021) | Alta (depende de XSS) |
| 10 | XSS armazenado (`[innerHTML]` sem sanitização) | A05 Injection (era A03 em 2021) | Média |

Essas falhas foram deixadas propositalmente no Projeto00 como baseline "inseguro" — a
evolução de segurança (hardening progressivo) deve ser documentada em projetos
posteriores, linkando de volta para cá (ex.: [[Projeto00/Vulnerabilidades]]) para
mostrar o que foi corrigido em cada etapa.
