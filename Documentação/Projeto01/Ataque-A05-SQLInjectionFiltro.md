# Projeto01 — Ataque A05: Injection (SQL Injection no filtro de tarefas)

Guia prático, passo a passo, de como explorar a falha de **A05 Injection** (ver
[[OWASP Top 10]]) no [[Projeto01]], especificamente a **SQL Injection** no filtro de
tarefas por nome do Kanban, já catalogada em [[Projeto01/Vulnerabilidades]] (item 4).

> Nota de versão: Injection é classificado como **A05** na edição 2025 (vigente) do
> [[OWASP Top 10]]; na edição 2021 era **A03**.

Importante: diferente do IDOR do [[Projeto00]] (ver
[[Projeto00/Ataque-A01-BrokenAccessControl]]), este ataque **continua funcionando mesmo
depois** da correção de IDOR aplicada no [[Projeto01]] (ver [[Projeto01/Melhorias]]) — a
checagem de posse confirma que você só pode *pedir* suas próprias tarefas,
mas a injeção, uma vez dentro da sua própria requisição autorizada, reescreve a cláusula
`WHERE` e lê dados de qualquer outro usuário de qualquer forma. É um ótimo exemplo prático
de por que corrigir um controle de acesso não substitui corrigir a causa raiz de uma
injeção.

Público-alvo: iniciante em segurança ofensiva — assume que você sabe usar o DevTools e
consegue fazer login na aplicação com uma conta própria.

## Pré-requisitos

- [[Projeto01/Backend|api01]] rodando em `http://localhost:8000`.
- [[Projeto01/Frontend|client01]] rodando em `http://localhost:4200`.
- **Duas contas cadastradas** (pela tela `/cadastro`):
  - Conta do atacante: `atacante@teste.com` / senha `123456` (papel `usuario`, padrão)
  - Conta da vítima: `vitima@teste.com` / senha `123456`
- Logado como a **vítima**, crie no Kanban uma tarefa identificável, ex. nome
  "Tarefa secreta da vítima".
- Faça logout e **logue como o atacante** — a partir daqui, todos os passos usam a
  sessão/token do atacante. Isso é importante: diferente do Projeto00, hoje é preciso
  estar autenticado como alguém para passar pela checagem de posse antes de chegar à
  injeção.

## O que é a vulnerabilidade, em uma frase

`tarefas/views.py:listar_tarefas_por_usuario`, quando recebe o parâmetro `?nome=`, monta
a consulta SQL por concatenação de string (f-string), sem parametrização:

```python
query = (
    "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
    "FROM tarefas_tarefa "
    f"WHERE usuario_id = {usuario_id} AND nome LIKE '%{nome_filtro}%'"
)
with connection.cursor() as cursor:
    cursor.execute(query)
```

Isso acontece **depois** da checagem `request.usuario['id'] != usuario_id` (que bloqueia
só a troca do id na URL) — então o valor de `nome_filtro` ainda pode alterar a lógica da
consulta inteira, inclusive ignorar o `usuario_id` que acabou de ser "autorizado".

---

## Parte 1 — Observar a chamada normal do filtro

1. Logado como o atacante, acesse `/kanban`.
2. Digite qualquer texto no campo de filtro (ex. `xyz`) e clique em "Filtrar".
3. No DevTools (**F12** → **Network**), veja a requisição:
   ```
   GET http://localhost:8000/api/usuarios/<seu-id>/tarefas?nome=xyz
   ```
   com `Authorization: Bearer <seu-token>` no header (anexado automaticamente pelo
   `authInterceptor`).
4. Como "xyz" não bate com nenhuma tarefa sua, a resposta é `[]` — comportamento normal
   de um filtro "sem match".

## Parte 2 — Confirmar a injeção com um payload de verdade/falso

Payloads clássicos de detecção de SQLi: um que force **falso** e um que force
**verdadeiro**, comparando os resultados.

1. No campo de filtro, digite:
   ```
   xxx' AND '1'='2
   ```
   Clique em "Filtrar" → resultado: `[]` (esperado, a condição extra é sempre falsa).
2. Agora digite:
   ```
   xxx' OR '1'='1' --
   ```
   Clique em "Filtrar" → resultado: **todas as tarefas de todos os usuários**, incluindo
   a "Tarefa secreta da vítima" que você (atacante) nunca deveria conseguir ver.

A consulta efetiva, nesse segundo caso, se torna:
```sql
SELECT id, usuario_id, nome, descricao, data_prazo, estado
FROM tarefas_tarefa
WHERE usuario_id = <seu-id> AND nome LIKE '%xxx' OR '1'='1' --%'
```
O `--` comenta o resto da linha (incluindo o `%'` final que o template adicionaria), e
`'1'='1'` é sempre verdadeiro. Como `OR` tem precedência menor que `AND` mas ainda se
aplica à cláusula inteira, o efeito é: `(usuario_id = <seu-id> AND nome LIKE '%xxx')
OR ('1'='1')` — e como o segundo lado do `OR` é sempre verdadeiro, a cláusula `WHERE`
inteira vale para **toda a tabela**, ignorando completamente o filtro de dono.

## Parte 3 — Reproduzindo via `curl`, sem precisar da UI

Para confirmar que o problema está no backend (não em algo específico do Angular), repita
direto na API, usando o token do atacante (visível em `localStorage.getItem('auth_token')`
no Console do DevTools, ou copiando a requisição do Network como "Copy as fetch"):

```bash
curl -G "http://localhost:8000/api/usuarios/<seu-id>/tarefas" \
  --data-urlencode "nome=xxx' OR '1'='1' -- " \
  -H "Authorization: Bearer <seu-token>"
```

A resposta traz tarefas com `usuario_id` diferente do seu — prova objetiva do vazamento
horizontal entre contas, mesmo com um token válido e a checagem de posse em vigor.

## Parte 4 — Até onde a injeção vai (opcional, para quem quiser ir além)

Como a função monta a lista de colunas manualmente no `SELECT` (não restringe via ORM/
schema fixo), em um banco com mais tabelas um atacante tentaria técnicas de
`UNION SELECT` para extrair dados de **outras** tabelas (ex. a própria tabela de
usuários, incluindo os hashes MD5 do item 1 de [[Projeto01/Vulnerabilidades]]) — desde
que o número de colunas do `UNION` bata com o da consulta original. Este guia não
detalha esse passo em profundidade (foge do escopo do Kanban), mas é importante registrar
no relatório que o vetor permite, em princípio, mais do que só ler tarefas de outros
usuários.

## Passo final — Documentar o achado

- **Vulnerabilidade**: SQL Injection no filtro de tarefas por nome
  (`tarefas/views.py:listar_tarefas_por_usuario`).
- **Passos para reproduzir**: Partes 1–3 acima.
- **Evidência**: print da resposta `[]` com `AND '1'='2` vs. a lista completa com
  `OR '1'='1' --` (Parte 2), e a mesma prova via `curl` (Parte 3).
- **Impacto**: qualquer usuário autenticado (mesmo sem nenhum papel especial) lê tarefas
  de qualquer outra conta, contornando a checagem de posse introduzida pela correção de
  IDOR (ver [[Projeto01/Melhorias]]) — e, potencialmente, outras tabelas do banco via
  `UNION SELECT`.
- **Causa raiz**: concatenação de entrada do usuário (`nome_filtro`) direto numa string
  SQL, sem parametrização, executada via `connection.cursor().execute(query)` em vez do
  ORM do Django.

## Mitigação

Já detalhado em [[Projeto01/Vulnerabilidades]] (item 4):

1. Usar consulta parametrizada:
   ```python
   cursor.execute(
       "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
       "FROM tarefas_tarefa WHERE usuario_id = %s AND nome LIKE %s",
       [usuario_id, f'%{nome_filtro}%'],
   )
   ```
2. Preferir o ORM, que já parametriza automaticamente:
   `Tarefa.objects.filter(usuario_id=usuario_id, nome__icontains=nome_filtro)`.
3. Depois de corrigir, reexecutar exatamente os payloads deste guia (Partes 2–3) como
   teste de regressão — a resposta a `OR '1'='1' --` deve voltar a ser só as tarefas do
   próprio usuário, igual ao resultado de um filtro "sem match" na Parte 1.
