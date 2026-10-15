# Projeto01 — Vulnerabilidades

Lista das vulnerabilidades propositais do [[Projeto01]] (backend `api01` + frontend
`client01`), focada no que **mudou** em relação ao [[Projeto00]]. Vulnerabilidades
herdadas sem alteração (CSRF desativado, CORS liberado, `DEBUG=True` + `SECRET_KEY`
commitada, falta de validação de entrada, XSS armazenado na descrição da tarefa) estão
detalhadas em [[Projeto00/Vulnerabilidades]] e continuam valendo aqui — não foram
duplicadas neste documento. Para arquitetura e rotas ver [[Projeto01/Visao]].

> **Ver também [[Projeto01/Melhorias]]**: os itens 3 (IDOR) e 4 (ausência de
> autenticação) de [[Projeto00/Vulnerabilidades]] foram corrigidos nas rotas de
> `tarefas` e na nova rota `GET /api/usuarios/me` — a narrativa completa da correção
> está lá, não neste documento, que lista apenas o que **continua** explorável.

Cada item segue o formato: **o que é** → **como explorar** → **como mitigar**.

---

## 1. Senha com hash MD5 sem salt

**Arquivo**: `usuarios/views.py` (`hash_md5`), `usuarios/models.py`

```python
def hash_md5(texto: str) -> str:
    return hashlib.md5(texto.encode('utf-8')).hexdigest()
```

O cadastro salva `hash_md5(senha)` e o login compara `hash_md5(senha_informada)` com o
valor salvo. É uma melhoria em relação ao texto puro do [[Projeto00]] (item 1 de
[[Projeto00/Vulnerabilidades]]), mas ainda gravemente inseguro: MD5 é criptograficamente
quebrado, extremamente rápido de calcular (bilhões de tentativas por segundo em GPU) e,
sem salt, duas contas com a mesma senha produzem o mesmo hash — visível a quem tiver
acesso ao banco.

**Como explorar**: com acesso ao `db.sqlite3` ou ao `/admin/`, basta rodar o hash MD5
contra listas de senhas comuns (rockyou.txt) ou rainbow tables públicas de MD5 — a
maioria das senhas fracas/reutilizadas é revertida em segundos. Hashes idênticos entre
usuários diferentes também revelam senha compartilhada sem precisar quebrar nada. Passo a
passo completo em [[Projeto01/Ataque-A04-MD5SemSalt]].

**Mitigação**:
- Usar um algoritmo de hash lento e com salt desenhado para senhas: `django.contrib.auth.hashers.make_password()`
  (PBKDF2/Argon2, dependendo do `PASSWORD_HASHERS` configurado) e `check_password()` para
  validar.
- Nunca devolver o hash da senha em nenhuma resposta JSON (aqui `usuario_para_json` já
  não devolve `senha`, mas isso não compensa o algoritmo fraco).

---

## 2. Token JWT nunca expira

**Arquivo**: `usuarios/jwt_utils.py` (`gerar_token`), `usuarios/views.py` (`login`)

O JWT emitido no login não possui claim `exp` (nem `iat`/`nbf`). As rotas de `tarefas` e
`GET /api/usuarios/me` **validam a assinatura** do token
(`usuarios/decorators.py:jwt_required`, ver [[Projeto01/Melhorias]]), mas não verificam
nenhum prazo de validade — um token assinado continua aceito para sempre, por mais
antigo que seja.

**Como explorar**: um token roubado uma única vez (ex.: via XSS, item 10 de
[[Projeto00/Vulnerabilidades]], que continua valendo aqui) permanece válido
indefinidamente, sem janela de expiração que force reautenticação ou limite a janela de
uso de um token comprometido. Passo a passo completo (incluindo o contraste com a
tentativa de **forjar** um token, que a validação de assinatura já bloqueia — ver
[[Projeto01/Melhorias]]) em [[Projeto01/Ataque-A07-TokenSemExpiracao]].

**Mitigação**:
- Incluir `exp` no payload do JWT (ex.: 15–60 minutos) e implementar renovação via
  refresh token de vida mais curta e revogável.
- Rejeitar em `jwt_required` qualquer token cujo `exp` já tenha passado.
- Manter uma lista de revogação (ou trocar a `SECRET_KEY`) para invalidar tokens
  comprometidos antes do prazo de expiração.

---

## 3. JWT guardado no `localStorage` e decodificado sem verificar assinatura

**Arquivo**: `client01/src/app/core/services/auth.service.ts` (`salvarToken`,
`usuarioLogado`)

O token substitui o objeto `Usuario` cru que o [[Projeto00]] guardava em `localStorage`
(item 9 de [[Projeto00/Vulnerabilidades]]), mas continua no mesmo local acessível a
qualquer JavaScript da página — incluindo um XSS (item 10). Além disso, o frontend
decodifica o payload do JWT (`atob` no segmento do meio) sem nunca verificar a
assinatura HMAC, então qualquer tela que exiba "dados do usuário logado" confia
ciegamente no conteúdo do token.

**Como explorar**: um XSS armazenado (item 10 de [[Projeto00/Vulnerabilidades]]) lê
`localStorage.getItem('auth_token')` e exfiltra o token, que — por nunca expirar (item 2)
— serve de credencial permanente para a API (que agora valida assinatura nas rotas de
`tarefas` e em `GET /api/usuarios/me`, ver [[Projeto01/Melhorias]], mas não teria como
distinguir o uso legítimo do uso pelo atacante, já que o token em si é válido).

Vale notar que o nome exibido no cabeçalho do Kanban (`kanban.component.ts`) já não vem
mais do payload decodificado sem verificação — passou a vir de
`AuthService.buscarUsuarioLogado()`, que chama `GET /api/usuarios/me` e recebe uma
resposta validada pelo backend (ver [[Projeto01/Melhorias]]). O `id` do usuário ainda é
lido do payload
decodificado (`usuarioLogado()`), mas só para montar a URL de `/tarefas`; a autorização
de fato continua sendo feita no backend, então um `id` adulterado no cliente no máximo
causa um `403`, não um vazamento de dados. Qualquer código novo que precise confiar em
dados do usuário logado deve preferir `buscarUsuarioLogado()`.

**Mitigação**:
- Mover o token para cookie `httpOnly` + `Secure` + `SameSite=Strict`, inacessível a
  JavaScript — mitiga o roubo via XSS.
- Sempre verificar a assinatura (e expiração) do token no backend antes de confiar em
  qualquer claim do payload.
- Tratar o conteúdo decodificado no frontend apenas como dado de exibição, nunca como
  fonte de autorização (a autorização real deve vir de uma checagem server-side).

---

## 4. SQL Injection no filtro de tarefas por nome

**Arquivo**: `tarefas/views.py` (`listar_tarefas_por_usuario`),
`client01/src/app/pages/kanban/kanban.component.ts` (`filtrarTarefas`)

O termo digitado na aba de filtro do Kanban é concatenado direto numa query SQL crua,
sem parametrização:

```python
query = (
    "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
    "FROM tarefas_tarefa "
    f"WHERE usuario_id = {usuario_id} AND nome LIKE '%{nome_filtro}%'"
)
with connection.cursor() as cursor:
    cursor.execute(query)
```

**Como explorar**: autenticado como qualquer usuário, abrir o Kanban e digitar no campo
de filtro um valor que quebre a string SQL e injete uma condição sempre verdadeira, por
exemplo:

```
xxx' OR '1'='1' --
```

A consulta efetiva passa a ser `... WHERE usuario_id = <id> AND nome LIKE '%xxx' OR
'1'='1'` — como `'1'='1'` é sempre verdadeiro e tem precedência de `OR` sobre o `AND`, a
cláusula `WHERE` inteira passa a valer para **todas as linhas da tabela**, retornando as
tarefas de **todos os usuários**, não só as do usuário logado. Também é possível
confirmar a injeção com payloads clássicos de detecção, como `' OR SLEEP(0)-- ` (ou
testar `' AND '1'='2`, que deve devolver zero resultados, contra `' OR '1'='1`, que deve
devolver tudo) para diferenciar de um filtro apenas "sem match".

**Como explorar (via cURL, sem precisar da UI)**:
```bash
curl "http://localhost:8000/api/usuarios/2/tarefas?nome=xxx%27%20OR%20%271%27%3D%271%27%20--%20"
```

Passo a passo completo (incluindo como essa injeção continua funcionando mesmo depois da
correção de IDOR — ver [[Projeto01/Melhorias]]) em [[Projeto01/Ataque-A05-SQLInjectionFiltro]].

**Impacto**: vazamento horizontal de dados entre contas (qualquer usuário autenticado lê
tarefas de qualquer outro usuário só manipulando o filtro), e abre caminho para extração
de outras informações do banco via técnicas de SQL Injection mais avançadas (ex.:
`UNION SELECT` contra outras tabelas, já que a função que monta a query não restringe as
colunas retornadas a um schema fixo).

**Mitigação**:
- Nunca concatenar entrada do usuário em SQL cru. Usar queries parametrizadas:
  ```python
  cursor.execute(
      "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
      "FROM tarefas_tarefa WHERE usuario_id = %s AND nome LIKE %s",
      [usuario_id, f'%{nome_filtro}%'],
  )
  ```
- Preferir o ORM do Django para esse filtro, que já parametriza automaticamente:
  `Tarefa.objects.filter(usuario_id=usuario_id, nome__icontains=nome_filtro)`.
- A checagem de posse já existe (ver [[Projeto01/Melhorias]]), mas não basta por si só —
  ela só impede trocar o `usuario_id` da URL; a parametrização da query é o que falta
  para fechar também o desvio por injeção.

---

## 5. Broken Access Control — aba "Usuários" sem checagem de papel no backend

**Arquivo**: `usuarios/views.py` (`listar_usuarios`),
`client01/src/app/app.component.ts` (`mostrarAbaUsuarios`),
`client01/src/app/pages/usuarios/usuarios.component.ts`

A aba "Usuários" (listagem de todos os usuários cadastrados, com filtro por nome/
sobrenome/email) só aparece na navegação para quem está logado como `admin`:

```ts
get mostrarAbaUsuarios(): boolean {
  return this.authService.usuarioLogado()?.papel === 'admin';
}
```

Mas essa é **só uma decisão de interface**. A rota que de fato devolve os dados,
`GET /api/usuarios`, exige um JWT válido (`@jwt_required`) — porém nunca confere
`request.usuario['papel']`:

```python
@jwt_required
def listar_usuarios(request):
    termo = request.GET.get('q', '')
    usuarios = Usuario.objects.all()
    if termo:
        usuarios = usuarios.filter(
            Q(nome__icontains=termo) | Q(sobrenome__icontains=termo) | Q(email__icontains=termo)
        )
    return JsonResponse([usuario_para_json(u) for u in usuarios.order_by('id')], safe=False)
```

**Como explorar**: fazer login com **qualquer** conta (papel `usuario`, sem nenhum
privilégio) e chamar a rota direto, sem passar pela UI:

```bash
curl http://localhost:8000/api/usuarios -H "Authorization: Bearer <token-de-um-usuario-comum>"
```

A resposta traz a lista completa de usuários do sistema (id, nome, sobrenome, email,
papel de cada um) — a mesma que só deveria aparecer para um admin na tela. O filtro
(`?q=<termo>`) funciona igual para qualquer chamador, autenticado ou não como admin.
Passo a passo completo em [[Projeto01/Ataque-A01-ListagemUsuariosSemChecarPapel]].

**Impacto**: qualquer conta cadastrada (inclusive uma criada agora mesmo pelo próprio
atacante via `/cadastro`, que sempre nasce `usuario` — item 4 de [[Projeto01/Melhorias]])
consegue enumerar todos os emails e papéis cadastrados no sistema — reconhecimento útil
para, por exemplo, decidir qual conta atacar primeiro (ex.: focar senha fraca na conta
que aparece como `papel: "admin"`).

**Mitigação**:
- Em `listar_usuarios`, depois de `jwt_required`, confirmar explicitamente
  `request.usuario['papel'] == 'admin'` (ou `in ('admin', 'gerente')`, dependendo da
  regra de negócio) antes de consultar o banco; devolver `403` caso contrário.
- Nunca tratar "esconder um link na UI" como controle de acesso — toda decisão de
  autorização precisa ser reforçada no backend, que é a única camada que o cliente não
  controla.
- Como reforço de defesa em profundidade, considerar também um guard de rota no
  Angular (`CanActivateFn`) que redirecione quem não é admin para fora de `/usuarios`
  antes mesmo da chamada à API — não substitui a checagem no backend, mas evita expor a
  tela por engano a quem simplesmente digitou a URL.

---

## Resumo

Classificação pela edição vigente do [[OWASP Top 10]] (**2025**).

| # | Vulnerabilidade | Classe (OWASP 2025) | Complexidade de exploração |
|---|---|---|---|
| 1 | Senha com hash MD5 sem salt | A04 Cryptographic Failures | Baixa–Média |
| 2 | Token JWT sem expiração | A07 Authentication Failures | Alta (depende de token roubado) |
| 3 | JWT em `localStorage` decodificado sem checar assinatura no frontend | A04 Cryptographic Failures | Alta (depende de XSS) |
| 4 | SQL Injection no filtro de tarefas | A05 Injection | Baixa |
| 5 | Broken Access Control — listagem de usuários sem checar papel | A01 Broken Access Control | Trivial |

Vulnerabilidades herdadas do [[Projeto00]] sem alteração relevante — ver
[[Projeto00/Vulnerabilidades]] itens 2, 5, 6, 7, 8 e 10. Os itens 3 (IDOR) e 4 (ausência
de autenticação) daquele documento foram corrigidos nas rotas de `tarefas` e em
`GET /api/usuarios/me` — narrativa completa da correção em [[Projeto01/Melhorias]]. O
painel `/admin/` (item 2 do [[Projeto00/Vulnerabilidades]]) e as rotas públicas de
cadastro/login não foram alteradas.

O escalonamento de privilégio via escolha livre de `papel` no cadastro, que existiu
neste projeto, também foi corrigido — ver [[Projeto01/Melhorias]].

Este projeto evolui a partir do baseline inseguro do [[Projeto00]] trocando e somando
falhas propositalmente, mas também corrige vulnerabilidades reais (ver
[[Projeto01/Melhorias]]) — ainda assim não deve ser tomado como referência de "versão
totalmente segura". A progressão de hardening real deve continuar em projetos
posteriores, linkando de volta para cá.
