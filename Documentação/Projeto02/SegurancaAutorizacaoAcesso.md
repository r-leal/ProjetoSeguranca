# Projeto02 — Segurança de Autorização e Acesso

> Guia didático para a equipe sobre autenticação, autorização e as boas
> práticas que vamos aplicar nos ajustes do [[Projeto02]] (cópia evoluída do
> [[Projeto01]]). O objetivo não é só dizer "o que fazer", mas explicar *por
> que* cada prática existe e qual ataque concreto ela neutraliza.

## 1. Autenticação vs. Autorização

Os dois termos são usados de forma intercambiável no dia a dia, mas resolvem
perguntas diferentes:

- **Autenticação (AuthN)** — "quem é você?". É o processo de login: o usuário
  prova a identidade dele (normalmente com email + senha), e o backend
  devolve uma credencial (ex.: um JWT) que representa essa identidade nas
  próximas requisições.
- **Autorização (AuthZ)** — "o que você pode fazer?". Dado que já sabemos
  quem é o usuário, decidimos se ele tem permissão para a ação que está
  tentando executar (ver sua própria tarefa, editar tarefa de outro usuário,
  acessar uma rota de admin, etc.).

Um erro comum é tratar "o usuário está logado" como sinônimo de "o usuário
pode fazer isso". No [[Projeto01]], por exemplo, o decorator `jwt_required`
(`usuarios/decorators.py`) resolve autenticação — garante que existe um token
válido e assinado — mas **não** resolve autorização de papel: ele não checa
se `request.usuario['papel']` é `admin` antes de liberar uma rota
administrativa. São duas camadas e as duas precisam existir.

## 2. JWT (JSON Web Token): o que é e para que serve

Um JWT é um token auto-contido, no formato `header.payload.assinatura`
(cada parte em Base64URL), usado para transportar afirmações ("claims")
sobre um usuário de forma que o servidor consiga verificar que elas não
foram adulteradas, sem precisar consultar o banco de dados a cada
requisição.

```
eyJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwicGFwZWwiOiJhZG1pbiJ9.k3F9a...
└────── header ──────┘└──────── payload ────────┘└─ assinatura ─┘
```

- **Header** — algoritmo de assinatura usado (ex.: `HS256`).
- **Payload** — as claims: id do usuário, papel, data de expiração, etc.
  **Não é criptografado, só codificado em Base64 — qualquer pessoa consegue
  ler o conteúdo**, inclusive abrindo o token em jwt.io. Nunca coloque dados
  sensíveis (senha, CPF, dados bancários) no payload.
- **Assinatura** — um HMAC (ou assinatura assimétrica) calculado sobre
  `header.payload` usando uma chave secreta que só o servidor conhece. É o
  que garante que o payload não foi alterado depois de emitido.

### Por que a assinatura importa

A segurança inteira do JWT depende de uma verificação: **o servidor recalcula
a assinatura a partir do payload recebido e compara com a assinatura que veio
no token.** Se um atacante editar o payload (ex.: trocar `"papel": "usuario"`
por `"papel": "admin"`), a assinatura recalculada não vai bater, e o token
deve ser rejeitado.

O `usuarios/jwt_utils.py` do [[Projeto01]] implementa exatamente isso com
`hmac.compare_digest` em `verificar_token()` — essa parte está correta. O
ponto cego está em outro lugar: **o frontend também decodifica o token**,
mas só com `atob()`, sem validar assinatura nenhuma (`auth.service.ts`,
método `usuarioLogado()`). Isso é aceitável *apenas* para exibir dados não
sensíveis na tela (ex.: nome do usuário no cabeçalho) — nunca para decidir
se uma ação é permitida. Qualquer decisão de autorização real tem que
passar pelo backend, que é o único lugar que possui a chave secreta e pode
validar a assinatura de verdade.

### Erros clássicos de implementação de JWT (e como evitá-los)

| Erro | Por que é perigoso | Como evitar |
|---|---|---|
| Aceitar `alg: none` ou deixar o cliente escolher o algoritmo | Um atacante manda um token sem assinatura e a biblioteca aceita | Fixar o algoritmo esperado no backend (nunca ler `alg` do token recebido) |
| Confundir "token decodificado" com "token validado" | Payload é só Base64, não prova nada por si só | Sempre chamar a função que recalcula e compara o HMAC (ou verifica a assinatura assimétrica) antes de usar qualquer campo do payload |
| Token sem campo `exp` (expiração) | Token roubado uma vez funciona para sempre | Ver seção 4 |
| Guardar segredos no payload | Payload é legível por qualquer um | Guardar só o necessário para identificar e autorizar (id, papel) |
| Chave secreta fraca, previsível ou hardcoded no código versionado | Permite forjar tokens offline (ataque de força bruta na chave) | Chave longa e aleatória, vinda de variável de ambiente/secret manager, nunca do próprio `SECRET_KEY` do framework reaproveitado para outra finalidade |

## 3. Papéis (Roles) e controle de acesso

"Papel" (role) é uma forma simples de autorização: cada usuário tem um papel
(`usuario`, `gerente`, `admin`, por exemplo, como em `usuarios/models.py`), e
cada rota/ação declara quais papéis podem executá-la.

Duas regras que valem para qualquer sistema com papéis:

1. **A checagem de papel é responsabilidade do backend, sempre.** O
   frontend pode (e deve) esconder botões e rotas que o usuário não deveria
   ver — isso é só UX. Mas se a API não repetir a checagem no servidor,
   basta o atacante chamar o endpoint direto (via `curl`/Postman) ignorando
   a interface para burlar a restrição. Esconder um botão não é controle de
   acesso.
2. **Autorização de papel é diferente de autenticação.** Um token válido e
   assinado prova que o usuário é quem diz ser, mas não decide sozinho se
   `papel == 'admin'` é exigido para aquela rota específica. Isso exige uma
   checagem explícita, repetida em cada endpoint sensível — normalmente um
   decorator/middleware dedicado (ex.: um `papel_required('admin')` que
   roda depois do `jwt_required`), nunca confiar que "se chegou até aqui, já
   está autorizado".

Um padrão comum e recomendado é o **least privilege**: todo novo endpoint
nasce restrito ao papel mínimo necessário, e você vai liberando acesso
conforme a necessidade real aparece — nunca o caminho inverso (nascer aberto
e restringir depois que alguém notar o problema).

## 4. Expiração e validação no backend

Um token que nunca expira é, na prática, equivalente a uma senha que nunca
precisa ser trocada e que, se vazar uma vez (log, histórico do navegador,
extensão maliciosa, XSS), continua valendo para sempre. É exatamente o caso
documentado como vulnerabilidade proposital no [[Projeto01]]
(`Documentação/Projeto01/Ataque-A07-TokenSemExpiracao.md`): o payload do JWT
não tem claim `exp`, e `verificar_token()` nunca checa data de expiração.

Boas práticas de expiração:

- **Claim `exp` sempre presente**, com um tempo de vida curto para o
  *access token* — minutos, não dias (ex.: 15 minutos é um valor comum).
  Isso limita a janela de uso de um token roubado.
- **A validação de expiração acontece no backend, a cada requisição.** Nunca
  confiar que o frontend vai "fazer logout" quando o token expirar — um
  atacante pode simplesmente reenviar o token antigo direto para a API,
  ignorando o frontend inteiramente. A verificação de `exp` tem que estar no
  mesmo lugar que verifica a assinatura (`verificar_token()`), rejeitando
  qualquer token expirado com 401 antes de tocar em qualquer dado.
- **Tokens de vida curta trazem um problema de usabilidade** — o usuário
  seria deslogado a cada 15 minutos. É isso que o refresh token resolve
  (seção 5).

## 5. Refresh token: por que separar em dois tokens

A solução para "token de vida curta é mais seguro, mas incomoda o usuário" é
usar **dois tokens com papéis diferentes**:

- **Access token** — vida curta (minutos), enviado em todo request autenticado
  (`Authorization: Bearer ...`), é o que o backend valida a cada chamada de
  API.
- **Refresh token** — vida mais longa (dias/semanas), guardado com mais
  cuidado ainda, e usado *só* para pedir um novo access token quando o atual
  expira — nunca enviado para endpoints de negócio, só para o endpoint
  dedicado de renovação (ex.: `POST /auth/refresh`).

Por que isso é mais seguro do que um único token de vida longa:

- Se o **access token** vazar (ex.: XSS, log de rede, extensão de browser
  maliciosa lendo `localStorage`), a janela de uso é curta — expira em
  minutos.
- O **refresh token** fica exposto numa superfície de ataque muito menor:
  idealmente nunca é acessível via JavaScript (ver seção 6, httpOnly
  cookies), então um XSS no frontend não consegue roubá-lo diretamente.
- Refresh tokens podem (e devem) ser **revogáveis no backend** — mantendo um
  registro de refresh tokens válidos por usuário/sessão, é possível
  invalidar todas as sessões de um usuário (ex.: ao detectar atividade
  suspeita, ou num "logout em todos os dispositivos") sem precisar esperar
  nenhum token expirar. Access tokens stateless (JWT puro) não dão esse
  controle — por isso o refresh token costuma ser o ponto de revogação do
  sistema.
- Um padrão adicional recomendado é a **rotação de refresh token**: a cada
  uso, o backend invalida o refresh token antigo e emite um novo. Se um
  refresh token "usado" aparecer de novo, é sinal de que foi roubado e
  reutilizado por duas partes diferentes (o legítimo e o atacante) — o
  backend pode reagir revogando toda a cadeia de sessão.

## 6. Criptografia segura (senhas e assinatura)

Dois lugares diferentes do sistema usam "criptografia", com requisitos bem
diferentes — misturar os dois é a origem de boa parte dos bugs de segurança
nessa área.

### 6.1 Hash de senha (armazenamento)

Senha **nunca é criptografada de forma reversível** — ela é transformada por
uma **função de hash para senhas**, que é proposital e intencionalmente
lenta, e que o sistema não precisa (nem consegue) desfazer: no login, você
não "descriptografa" a senha salva para comparar, você aplica a mesma função
de hash na senha digitada e compara os hashes.

O [[Projeto01]] usa MD5 sem salt (documentado em
`Documentação/Projeto01/Ataque-A04-MD5SemSalt.md`), o que é inseguro por dois
motivos distintos:

- **MD5 é rápido demais.** Hash de senha precisa ser *lento de propósito*,
  para que testar milhões de senhas candidatas (força bruta/dicionário)
  seja caro computacionalmente. MD5 foi desenhado para ser rápido (checksum
  de integridade), o oposto do que se quer aqui.
- **Sem salt, hashes iguais ⇒ senhas iguais.** Um atacante com acesso ao
  banco consegue comparar hashes entre contas (duas pessoas usando
  "123456" terão o mesmo hash MD5) e usar **rainbow tables** (tabelas
  pré-computadas de hash → senha) para reverter o hash direto, sem nem
  precisar de força bruta online.

**Prática recomendada**: usar um algoritmo de hash de senha dedicado —
`bcrypt`, `argon2` ou `PBKDF2` (o próprio Django já tem isso embutido em
`django.contrib.auth.hashers`, com salt automático e custo configurável).
Nenhum desses dois problemas existe nesses algoritmos: eles são
deliberadamente custosos (ajustável com um "fator de custo", que pode subir
conforme hardware melhora) e geram/armazenam um salt único por senha.

### 6.2 Assinatura do token (integridade, não sigilo)

A assinatura HMAC do JWT (seção 2) resolve um problema diferente: não é
sobre esconder o conteúdo (o payload já é visível em Base64), é sobre
**provar que o conteúdo não foi alterado** depois de emitido pelo servidor.
Os requisitos de uma boa chave de assinatura:

- **Alta entropia** — longa e aleatória, não uma palavra ou frase previsível.
- **Nunca reaproveitar o `SECRET_KEY` do framework para outra finalidade.**
  No [[Projeto01]], `settings.py` faz `JWT_SECRET = SECRET_KEY` — ou seja, a
  mesma chave usada para assinar JWTs também assina sessões, tokens de reset
  de senha do Django, etc. Se qualquer um desses outros usos vazar a chave,
  o atacante ganha a capacidade de forjar JWTs válidos também. Chaves com
  finalidades diferentes devem ser independentes.
- **Nunca commitada em texto puro no repositório** — vir de variável de
  ambiente ou secret manager, rotacionável sem precisar de novo deploy de
  código.

## 7. Persistência no frontend: localStorage vs. httpOnly cookie

Depois que o backend emite o token, onde o frontend guarda ele importa
tanto quanto como o backend valida.

### 7.1 `localStorage` (o que o [[Projeto01]] faz hoje)

`auth.service.ts` guarda o token com
`localStorage.setItem(AUTH_TOKEN_KEY, token)`. Isso funciona, mas tem uma
exposição grave: **qualquer JavaScript executando na página tem acesso de
leitura ao `localStorage`.** Isso inclui:

- Scripts injetados por uma vulnerabilidade de **XSS** (Cross-Site
  Scripting) em qualquer parte do app — uma única `<script>` maliciosa
  consegue rodar `localStorage.getItem(...)` e mandar o token para um
  servidor do atacante. Com o token em mãos, o atacante se autentica como
  a vítima sem precisar da senha.
- Extensões de browser maliciosas ou comprometidas, que também enxergam o
  `localStorage` de qualquer site aberto.

Ou seja: localStorage resolve persistência, mas **não oferece nenhuma
barreira contra XSS** — se o atacante conseguir rodar JS na página, o jogo
acabou.

### 7.2 Cookie `httpOnly` + `Secure` + `SameSite`

A alternativa recomendada é o backend devolver o token (tipicamente o
refresh token, às vezes também o access token) num cookie com a flag
`HttpOnly`. Isso muda o modelo de ameaça:

- **`HttpOnly`** — o cookie fica invisível para `document.cookie` e qualquer
  outra API de JavaScript. Um XSS na página ainda consegue executar código,
  mas **não consegue ler o cookie** para roubá-lo e mandar para fora. O
  navegador continua enviando o cookie automaticamente em requisições para o
  domínio, só não permite leitura via script.
- **`Secure`** — o cookie só é enviado em conexões HTTPS, nunca em HTTP
  puro, prevenindo captura por quem está escutando a rede (ataque
  man-in-the-middle numa rede não confiável).
- **`SameSite=Strict` ou `Lax`** — controla se o cookie é enviado em
  requisições que se originam de outro site. Isso é a defesa principal
  contra **CSRF** (Cross-Site Request Forgery): sem `SameSite`, um site
  malicioso poderia fazer o navegador da vítima disparar uma requisição para
  a sua API, e o cookie seria enviado automaticamente, autenticando a
  requisição indesejada.

### 7.3 O trade-off: XSS vs. CSRF

Nenhuma das duas opções é uma bala de prata — cada uma fecha uma porta e
abre (ou deixa aberta) outra:

| | localStorage | Cookie httpOnly |
|---|---|---|
| Exposto a XSS (roubo de token via script) | Sim | Não |
| Exposto a CSRF (requisição forjada por outro site) | Não (token não é enviado automaticamente) | Sim, se faltar `SameSite`/proteção CSRF |
| Enviado automaticamente pelo browser | Não (precisa adicionar no header manualmente) | Sim |

Ou seja, mover o token para `httpOnly` cookie **troca o problema de XSS por
um problema de CSRF** — e CSRF se resolve com `SameSite` + (quando
necessário) um token CSRF dedicado para métodos que alteram estado (POST/
PUT/DELETE). Na prática, isso ainda é uma troca favorável, porque:

- XSS costuma ser mais fácil de introduzir sem querer (um campo de input
  renderizado sem escapar, uma lib de terceiros comprometida) do que CSRF é
  de explorar quando `SameSite` já está configurado corretamente.
- A defesa contra CSRF (`SameSite` + token CSRF) é bem estabelecida e barata
  de implementar; a defesa contra "XSS pode ler meu token" não existe de
  verdade além de "não ter XSS" — e eliminar 100% das superfícies de XSS num
  app real é muito mais difícil do que configurar `SameSite`.

**Recomendação prática**: refresh token em cookie `HttpOnly` + `Secure` +
`SameSite=Strict`; access token de vida curta pode continuar sendo enviado
no header `Authorization` (guardado só em memória no frontend, nunca em
`localStorage`/`sessionStorage`, para reduzir ainda mais a janela de
exposição a XSS).

## 8. Checklist de revisão para novas rotas/features

Antes de considerar uma rota autenticada "pronta", confirme:

- [ ] A rota exige token válido (`jwt_required` ou equivalente) — autenticação.
- [ ] A rota checa explicitamente o papel exigido, no backend — autorização.
- [ ] O token tem claim `exp`, e o backend rejeita token expirado.
- [ ] A assinatura do token é recalculada e comparada (`hmac.compare_digest`
      ou equivalente) antes de confiar em qualquer campo do payload.
- [ ] Nenhum dado sensível foi colocado no payload do JWT (ele é legível por
      qualquer um).
- [ ] A chave de assinatura do JWT é própria (não reaproveita `SECRET_KEY` de
      outro uso) e vem de variável de ambiente.
- [ ] Senha de usuário é hasheada com `bcrypt`/`argon2`/`PBKDF2` + salt —
      nunca MD5/SHA puro.
- [ ] O token (ao menos o refresh token) é persistido em cookie `HttpOnly` +
      `Secure` + `SameSite`, não em `localStorage`.
- [ ] Existe um caminho de revogação (logout real invalida o refresh token
      no backend, não só remove ele do frontend).

## Ver também

- [[Projeto01]] — `Documentação/Projeto01/Vulnerabilidades.md` e os guias de
  ataque `Ataque-A04-MD5SemSalt.md` e `Ataque-A07-TokenSemExpiracao.md`,
  que documentam as falhas concretas que este guia explica como evitar.
- `Documentação/OWASP Top 10/` — referência transversal dos códigos OWASP
  citados aqui (A01 - Broken Access Control, A02 - Cryptographic Failures,
  A07 - Identification and Authentication Failures).
