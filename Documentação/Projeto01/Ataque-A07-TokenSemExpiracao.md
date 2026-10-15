# Projeto01 — Ataque A07: Authentication Failures (token JWT sem expiração)

Guia prático, passo a passo, de como abusar do JWT do [[Projeto01]] que **nunca expira**,
já catalogado em [[Projeto01/Vulnerabilidades]] (itens 2 e 3). Mostra tanto o que **ainda
funciona** (reusar um token roubado indefinidamente) quanto o que a correção de IDOR
(ver [[Projeto01/Melhorias]]) **já bloqueia** (forjar um token do zero) — útil para
entender a diferença entre "token roubado" e "token forjado".

> Nota de versão: Authentication Failures é a categoria **A07** tanto na edição 2021
> quanto na **edição 2025** (vigente) do [[OWASP Top 10]].

Este guia depende do XSS armazenado já documentado em
[[Projeto00/Ataque-A05-StoredXSS]] (item 10 de [[Projeto00/Vulnerabilidades]], ainda
presente sem alteração no [[Projeto01]]) como forma de roubar o token — leia aquele guia
primeiro se ainda não o fez; aqui o foco é só no que se faz **depois** de ter o token em
mãos.

Público-alvo: iniciante em segurança ofensiva — assume familiaridade básica com DevTools
e o conceito de que um JWT é só um texto em três partes separadas por `.`.

## Pré-requisitos

- [[Projeto01/Backend|api01]] rodando em `http://localhost:8000`.
- [[Projeto01/Frontend|client01]] rodando em `http://localhost:4200`.
- Uma conta de teste cadastrada e logada pelo menos uma vez, para ter um token real
  salvo em `localStorage`.

## O que é a vulnerabilidade, em uma frase

`usuarios/jwt_utils.py:gerar_token` monta o payload do JWT **sem** a claim `exp` (nem
`iat`/`nbf`), e nenhuma rota do backend (`usuarios/decorators.py:jwt_required`) checa
prazo de validade — ela só confirma a **assinatura**. Um token assinado uma vez, por mais
antigo que seja, continua sendo aceito para sempre.

---

## Parte 1 — Obter um token válido e confirmar que ele nunca expira

1. Faça login normalmente em `http://localhost:4200/login`.
2. Abra o Console do DevTools (**F12** → **Console**) e rode:
   ```js
   localStorage.getItem('auth_token')
   ```
3. Copie a string retornada (três blocos separados por `.`).
4. Decodifique o payload (segundo bloco) para ver o conteúdo, sem precisar de nenhuma
   ferramenta além do próprio Console:
   ```js
   JSON.parse(atob(localStorage.getItem('auth_token').split('.')[1]))
   // { id: 1, nome: "...", sobrenome: "...", email: "...", papel: "usuario" }
   ```
5. Repare que **não existe** nenhum campo `exp`, `iat` ou `nbf` no objeto decodificado —
   só os dados do usuário. Isso confirma, direto na prática, o que o código de
   `gerar_token` já deixava claro: não há nenhuma informação de validade temporal
   embutida no token.

## Parte 2 — Reusar o mesmo token indefinidamente

1. Com o token copiado na Parte 1, teste a API diretamente, quanto tempo depois quiser
   (minutos, dias, meses — não há diferença para o backend):
   ```bash
   curl http://localhost:8000/api/usuarios/me \
     -H "Authorization: Bearer <token-copiado>"
   ```
2. A resposta continua sendo `200` com os dados do usuário, por mais "velho" que o token
   seja — não existe nenhum mecanismo de expiração para rejeitá-lo.

**Combinando com o XSS armazenado** (ver [[Projeto00/Ataque-A05-StoredXSS]]): o payload
daquele guia já lê `localStorage` e exfiltra seu conteúdo via `mailto:`. Nesta versão do
projeto, o que é exfiltrado é o JWT (não mais a senha em claro) — mas o efeito prático é
equivalente: quem recebe o token roubado consegue se autenticar como a vítima **para
sempre**, sem nunca precisar da senha dela, e sem que a vítima tenha como saber que isso
está acontecendo (não existe nenhuma lista de sessões ativas nem forma de revogar só
aquele token).

## Parte 3 — O que a correção de assinatura já impede: forjar um token do zero

Para deixar claro o que **mudou** desde a correção de IDOR (ver [[Projeto01/Melhorias]]),
tente montar um token "na mão", sem nunca ter feito login — ou seja, sem conhecer
`JWT_SECRET`:

1. No Console do DevTools, monte um header e um payload forjados, fingindo ser o
   usuário de id `1` com papel `admin`:
   ```js
   function b64url(obj) {
     return btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
   }
   const header = b64url({ alg: 'HS256', typ: 'JWT' });
   const payload = b64url({ id: 1, nome: 'Forjado', sobrenome: 'X', email: 'x@x.com', papel: 'admin' });
   const tokenForjado = `${header}.${payload}.assinatura-qualquer`;
   ```
2. Teste contra a API:
   ```js
   fetch('http://localhost:8000/api/usuarios/me', {
     headers: { Authorization: `Bearer ${tokenForjado}` }
   }).then(r => console.log(r.status))
   ```
3. Resultado: **`401`**, `{"erro": "Token inválido."}`. Diferente de uma versão anterior
   do projeto (sem a validação de assinatura em `usuarios/jwt_utils.py:verificar_token`),
   aqui o backend recalcula o HMAC esperado com `JWT_SECRET` e compara via
   `hmac.compare_digest` — como você não tem a chave, não existe forma de produzir uma
   assinatura que bata, então o token forjado é sempre rejeitado.

Esse contraste (Parte 2 funciona, Parte 3 não) é o ponto central deste guia: validar
assinatura resolve "alguém forjar identidade do zero", mas **não resolve** "alguém reusar
um token legítimo que já vazou" — são duas garantias diferentes, e só a primeira existe
hoje no [[Projeto01]].

## Passo final — Documentar o achado

- **Vulnerabilidade**: ausência de expiração no JWT (`usuarios/jwt_utils.py:gerar_token`)
  combinada com o token acessível via `localStorage` a qualquer XSS (item 10 de
  [[Projeto00/Vulnerabilidades]]).
- **Passos para reproduzir**: Partes 1–2 acima (a Parte 3 é só para evidenciar o que
  **não** é mais explorável, útil para o relatório mostrar progresso real).
- **Evidência**: print do payload decodificado sem `exp` (Parte 1), print da resposta
  `200` reusando o mesmo token depois de um intervalo (Parte 2), print do `401` ao tentar
  forjar (Parte 3, para contraste).
- **Impacto**: um token roubado uma única vez (via XSS, extensão de navegador maliciosa,
  log de proxy mal configurado, etc.) vale como credencial permanente — não há janela de
  expiração que limite o estrago nem forma de revogar sessões individualmente.
- **Causa raiz**: `gerar_token` não inclui `exp`, e `jwt_required`/`verificar_token` não
  checam nenhum prazo de validade, só a assinatura.

## Mitigação

Já detalhado em [[Projeto01/Vulnerabilidades]] (item 2):

1. Incluir `exp` no payload (ex.: 15–60 minutos) e rejeitar em `verificar_token()`
   qualquer token cujo `exp` já tenha passado.
2. Implementar renovação via refresh token de vida mais curta e revogável
   separadamente do token de acesso.
3. Mover o token para cookie `httpOnly` (item 3 de [[Projeto01/Vulnerabilidades]]), para
   que um XSS futuro não consiga mais lê-lo via `localStorage` — reduz drasticamente o
   cenário de roubo descrito na Parte 2 deste guia.
