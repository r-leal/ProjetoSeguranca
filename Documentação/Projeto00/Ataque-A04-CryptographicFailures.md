# Projeto00 — Ataque A04: Cryptographic Failures (senha em texto puro)

Guia prático, passo a passo, de como explorar a falha de **A04 Cryptographic Failures**
(ver [[OWASP Top 10]]) no [[Projeto00]] — especificamente o armazenamento e transporte de
senha em **texto puro**, já catalogado em [[Projeto00/Vulnerabilidades]] (item 1).

> Nota de versão: esta categoria é **A04** na edição 2025 (vigente) do
> [[OWASP Top 10]]; na edição 2021 era numerada **A02**. O conteúdo técnico abaixo não
> muda — só a numeração oficial.

Análogo a [[Projeto00/Ataque-A01-BrokenAccessControl]], mas aqui o foco é **só**
criptografia fraca/ausente em senhas. As demais falhas do Projeto00 continuam em
[[Projeto00/Vulnerabilidades]] e serão tratadas em guias próprios de outros projetos.

Público-alvo: iniciante em segurança ofensiva — assume que você sabe usar o DevTools do
navegador e consegue instalar um programa gratuito no seu computador.

## Pré-requisitos

- [[Projeto00/Backend|api00]] rodando em `http://localhost:8000`.
- [[Projeto00/Frontend|client00]] rodando em `http://localhost:4200`.
- Um usuário de teste cadastrado (pode reaproveitar o `vitima@teste.com` / `123456` do
  guia de A01).
- **DB Browser for SQLite** instalado — programa gratuito e open source para abrir
  arquivos `.sqlite3` sem linha de comando: `sqlitebrowser.org`.
- (Opcional, para a Parte 3) um superusuário Django criado com
  `python manage.py createsuperuser`, só para demonstrar o outro caminho de exposição.

## O que é a vulnerabilidade, em uma frase

O campo `senha` em `usuarios/models.py` é um `CharField` comum — a senha é salva **exatamente como o usuário digitou**, sem hash e sem salt. Isso significa que qualquer um com acesso ao banco, ao admin do Django, ou até à própria resposta da API consegue ler a senha de qualquer usuário diretamente, sem precisar "quebrar" nada.

---

## Parte 1 — Ver a sua própria senha trafegando e voltando em claro

1. Acesse `http://localhost:4200/login`, abra o DevTools (**F12**) e vá na aba
   **Network** antes de logar.
2. Faça login com `vitima@teste.com` / `123456`.
3. Clique na requisição `POST http://localhost:8000/api/login` na lista do Network.
4. Na aba **Payload/Request** você vê exatamente o que foi enviado:
   ```json
   { "email": "vitima@teste.com", "senha": "123456" }
   ```
5. Na aba **Response**, o backend devolve o objeto do usuário **incluindo a senha de
   volta**:
   ```json
   {
     "id": 1,
     "nome": "Vitima",
     "sobrenome": "Teste",
     "data_nascimento": null,
     "email": "vitima@teste.com",
     "senha": "123456"
   }
   ```

**O que reparar aqui**: não existe nenhuma transformação entre o que você digitou e o que
trafegou/voltou pela rede — a senha está em claro em dois pontos que nunca deveriam
expor isso (o corpo da resposta de login, e qualquer log de acesso/proxy que registre o
request). Mesmo que o site usasse HTTPS (criptografia **em trânsito**), isso só protege o
pacote entre navegador e servidor — não resolve o problema de fundo, que é a senha nunca
ter sido transformada (hash) em nenhum momento do caminho.

## Parte 2 — Ler a senha de **outro** usuário direto do banco

Esse é o ataque central deste guia: simular alguém que conseguiu acesso ao arquivo do
banco (vazamento de backup, cópia indevida, acesso físico/compartilhado ao servidor de
desenvolvimento — um cenário extremamente comum em incidentes reais).

1. Localize o arquivo do banco: `Projeto00/api00/db.sqlite3`.
2. Abra o **DB Browser for SQLite** e use **Open Database** para abrir esse arquivo.
3. Vá na aba **Browse Data** e selecione a tabela `usuarios_usuario`.
4. Pronto — a tabela inteira aparece, com uma coluna `senha` mostrando **a senha de
   todos os usuários cadastrados, em texto puro**, lado a lado com o email de cada um.
5. Alternativamente, use a aba **Execute SQL** e rode:
   ```sql
   SELECT email, senha FROM usuarios_usuario;
   ```
   Isso devolve a lista completa de credenciais do sistema em uma única consulta.

**Resultado**: sem quebrar hash nenhum, sem força bruta, sem sequer precisar da
aplicação rodando — só abrindo o arquivo do banco, você tem a senha de **todas** as
contas, inclusive de usuários que você nunca interagiu via login.

## Parte 3 — O mesmo vazamento, mas pelo painel administrativo

Caminho alternativo, útil para entender que a falha se repete em qualquer superfície que
toque o model `Usuario`.

1. Acesse `http://localhost:8000/admin/` e faça login com o superusuário.
2. Clique em **Usuarios** → clique em qualquer registro da lista.
3. O formulário de edição mostra o campo **Senha** com o valor em claro, pronto para ser
   lido (e até copiado) direto da tela — o Django Admin não sabe que deveria mascarar
   esse campo, porque para ele é só mais um `CharField` comum, igual a `nome` ou
   `email`.

## Passo final — Documentar o achado

- **Vulnerabilidade**: armazenamento de senha sem hash (`usuarios/models.py`, campo
  `senha`), e devolução da senha em claro nas respostas de `POST /api/usuarios` e
  `POST /api/login` (`usuarios/views.py`).
- **Passos para reproduzir**: Partes 1–3 acima.
- **Evidência**: print da aba Response do login (Parte 1) e print da tabela
  `usuarios_usuario` no DB Browser (Parte 2).
- **Impacto**: comprometimento total de credenciais de todos os usuários a partir de
  qualquer vazamento de banco, backup ou acesso administrativo — e, como a maioria das
  pessoas reutiliza senha em vários sites, o impacto normalmente vai além do próprio
  sistema.
- **Causa raiz**: nenhuma função de hash é usada ao salvar (`Usuario.objects.create(...,
  senha=dados.get('senha', ''))`) nem ao autenticar (`Usuario.objects.filter(email=...,
  senha=...)`).

---

## Sobre criptografia de senha: por que "fraca" é fraca e o que usar hoje

### Criptografia reversível não é a resposta

O erro mais comum de quem corrige esse tipo de falha "pela metade" é trocar
`senha='123456'` por `senha=criptografar('123456')` usando uma criptografia
**reversível** (AES, por exemplo) — ou seja, existe uma chave que descriptografa de
volta para o texto original. Isso só desloca o problema: quem roubar o banco **e** a
chave (frequentemente guardada no mesmo servidor) ainda lê todas as senhas em claro.
Senha deve passar por **hash**, uma função de **mão única**: dá para calcular o hash a
partir da senha, mas não existe operação inversa que recupere a senha a partir do hash.

### O que é hash

Um **hash** é o resultado de passar um dado (texto, arquivo, o que for) por uma função
matemática que sempre devolve uma saída de **tamanho fixo**, de aparência
"embaralhada"/pseudoaleatória, e **determinística**: a mesma entrada sempre produz a
mesma saída, mas não existe nenhum caminho de volta da saída para a entrada.

Exemplo simples, usando SHA-256 (só para ilustrar o conceito — na prática não é o
algoritmo certo para senha, ver abaixo):

```
sha256("123456")        → 8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c
sha256("123457")        → d5cd1ac1ff82d4f8c0ea3d360bca45bf4b4da7caeb08359e74dfa29e9da1a05
sha256("Senha-Forte!99") → 3b2c... (outro valor completamente diferente)
```

Repare duas coisas: (1) mudar **um único caractere** da entrada ("123456" → "123457")
muda o hash inteiro, de forma imprevisível — isso é proposital, chamado de "efeito
avalanche", e impede qualquer atacante de "chutar por aproximação"; (2) o tamanho da
saída é sempre o mesmo (64 caracteres hexadecimais no caso do SHA-256), não importa se a
entrada tinha 4 ou 4.000 caracteres.

### O que é salt

**Salt** é um valor aleatório, gerado uma vez por registro (por senha), que é misturado
à senha **antes** de calcular o hash — e depois guardado junto do hash resultante (não
precisa ser secreto, só precisa ser único e imprevisível).

```
usuário "ana":   salt = "x7Qw"   hash( "x7Qw" + "123456" ) → aaa111...
usuário "bruno": salt = "pL9k"   hash( "pL9k" + "123456" ) → bbb222...
```

Mesma senha (`"123456"`), hashes completamente diferentes, porque o salt de cada um é
diferente. Isso é o que derrota a **rainbow table** mencionada na seção anterior: sem
salt, um atacante calcula `hash("123456")` **uma vez** e usa esse mesmo valor para
identificar instantaneamente qualquer conta no mundo que use essa senha. Com salt único
por usuário, o atacante teria que recalcular o hash de "123456" **de novo para cada
usuário**, com o salt específico daquele registro — inviabilizando o pré-cálculo em
massa.

### Por que hash não é criptografia de mão dupla

"Criptografia", no sentido mais usado em segurança (AES, RSA, etc.), é **reversível por
construção**: existe uma chave que permite transformar o texto cifrado de volta no texto
original (`decrypt(encrypt(mensagem, chave), chave) == mensagem`). Isso é exatamente o
que se quer para, por exemplo, uma mensagem que precisa ser lida pelo destinatário.

**Hash não tem — nem tenta ter — essa propriedade.** Não existe "chave de
descriptografia" para um hash porque a função não guarda informação suficiente para
reconstruir a entrada:

- A saída tem **tamanho fixo** (ex.: sempre 64 caracteres no SHA-256), mas a entrada
  pode ter qualquer tamanho. Isso por si só já garante que a transformação **perde
  informação** (matematicamente, é uma função que não é injetora: múltiplas entradas
  diferentes mapeiam, em teoria, para o mesmo espaço finito de saídas — só que, numa
  boa função de hash, achar duas que colidem na prática é computacionalmente
  inviável). Não existe cálculo inverso possível quando a transformação literalmente
  descarta informação no caminho.
- Por isso, autenticar um usuário **nunca** é "descriptografar o hash salvo e comparar
  com a senha digitada" — é **recalcular o hash da senha digitada** (com o mesmo salt
  guardado) **e comparar os dois hashes**. Ninguém, nem o próprio sistema, nem quem
  programou o algoritmo, consegue ir de um hash de volta à senha original — só é
  possível *adivinhar* senhas candidatas, calcular o hash de cada uma, e comparar (é
  exatamente o que um ataque de força bruta/dicionário faz, e por isso a **velocidade**
  do hash importa tanto — ver a seção seguinte).

Em resumo: criptografia (AES/RSA) protege dados que **precisam** ser recuperados depois;
hash protege dados que só **precisam ser verificados**, nunca recuperados — que é
exatamente o caso de uma senha.

### Por que MD5 (e SHA-1 sozinho) são considerados fracos para senha

- **MD5** foi desenhado em 1992 para checksums de integridade, não para senhas. Hoje é
  considerado quebrado: é possível gerar **colisões** (duas entradas diferentes com o
  mesmo hash) de forma prática desde 2004, o que já o desqualifica para qualquer uso que
  dependa de unicidade garantida. Mas mesmo ignorando colisões, o problema real para
  senha é **velocidade**: GPUs comuns calculam **bilhões de hashes MD5 por segundo**. Um
  atacante com uma lista de hashes MD5 testa o dicionário de senhas mais comuns (ou
  força bruta de 6-8 caracteres) em minutos/horas.
- **SHA-1** tem o mesmo problema de fundo: foi quebrado quanto a colisões em 2017
  (ataque "SHAttered" do Google), mas o motivo real de não servir para senha é que
  também é **rápido demais** — continua sendo recalculável aos bilhões por segundo em
  hardware acessível.
- **SHA-256/SHA-512 "puro"** (sem nada além do hash) resolve colisão, mas **continua
  rápido demais** para senha — GPUs calculam centenas de milhões a bilhões de hashes
  SHA-256 por segundo. Rapidez é ótima para checksum de arquivo, péssima para proteger
  senha: você *quer* que validar uma senha seja lento o suficiente para inviabilizar
  testar bilhões de combinações por segundo.
- **Sem salt, nenhum dos acima resolve nada**: sem um valor aleatório único por usuário
  misturado ao hash, duas pessoas com a mesma senha têm o mesmo hash — e um atacante
  pode pré-calcular hashes de senhas comuns uma única vez (**rainbow table**) e
  comparar contra o banco inteiro de uma vez, em vez de atacar usuário por usuário.

### O padrão de mercado hoje: funções de hash lentas e com salt

Em vez de hash genérico (MD5/SHA-*), o padrão atual é uma **função de hash para senha**
("password hashing function"), que é deliberadamente lenta e cara de calcular, com salt
único embutido automaticamente:

| Algoritmo | Observação |
|---|---|
| **Argon2** (especificamente Argon2id) | Vencedor da Password Hashing Competition (2015); hoje a recomendação nº 1 da OWASP. É *memory-hard* — exige muita memória RAM para calcular, o que encarece drasticamente atacar em paralelo com GPU/ASIC (que têm pouca memória por núcleo). |
| **bcrypt** | Mais antigo (1999) e ainda amplamente usado e confiável; tem um "cost factor" configurável que aumenta o tempo de cálculo conforme hardware fica mais rápido. |
| **scrypt** | Também memory-hard, alternativa ao Argon2, comum em contextos de criptomoedas além de senhas. |
| **PBKDF2** | Mais simples (aplica um hash tipo SHA-256 repetidas vezes, com salt); aceito por padrões como NIST, mas não é memory-hard — considerado o mais fraco dos quatro listados aqui, ainda assim muito melhor que MD5/SHA-* puro. |

Todos compartilham as mesmas ideias-chave:
1. **Salt único e aleatório por senha**, gerado automaticamente e guardado junto do
   hash — elimina rainbow tables e garante que senhas iguais gerem hashes diferentes.
2. **Custo computacional ajustável** ("work factor"/iterações) — o algoritmo é lento de
   propósito, e esse custo pode ser aumentado com o tempo conforme hardware evolui.
3. **Resistência a hardware especializado** (GPU/ASIC) — Argon2 e scrypt vão além e
   também exigem memória, não só tempo de CPU.

### Como isso se aplicaria ao Projeto00

O Django já traz isso pronto em `django.contrib.auth.hashers` — não seria preciso
escolher/implementar um algoritmo manualmente:

```python
from django.contrib.auth.hashers import make_password, check_password

# ao cadastrar:
usuario.senha = make_password(dados.get('senha'))  # gera hash + salt automaticamente

# ao logar:
check_password(senha_informada, usuario.senha)  # True/False, nunca expõe a senha original
```

Por padrão o Django usa **PBKDF2 com SHA-256**; trocar para Argon2 (hoje considerado o
mais forte) é literalmente adicionar `'django.contrib.auth.hashers.Argon2PasswordHasher'`
no topo de `PASSWORD_HASHERS` em `settings.py` e instalar o pacote `argon2-cffi`. Essa
correção — junto de nunca mais devolver o campo `senha` em nenhuma resposta JSON —
resolve a causa raiz deste guia.

---

## Como "quebrar" hash/criptografia na prática

Esta seção detalha o que significa, na prática, atacar os valores vistos acima — tanto
para entender melhor por que salt + lentidão resolvem o problema, quanto para saber
quais ferramentas um atacante (ou um pentester autorizado) realmente usaria.

### Rainbow table, em detalhe

Uma **rainbow table** é uma estrutura de dados pré-calculada que mapeia hashes de volta
para a senha que os gerou — não porque o hash foi "revertido" matematicamente (isso
continua impossível, ver seção anterior), mas porque alguém já calculou o hash de uma
quantidade gigantesca de senhas candidatas **de antemão** e guardou o resultado.

Como funciona, simplificado:

1. Alguém pega uma lista enorme de senhas candidatas (dicionários de senhas vazadas,
   combinações de caracteres até N posições, etc.) e calcula `hash(senha)` para cada
   uma, **uma única vez**, offline, sem pressa.
2. O resultado é guardado numa tabela de busca: `hash → senha original`.
   (Rainbow tables de verdade usam uma técnica de "cadeias de redução" para comprimir
   essa tabela e caber em menos espaço em disco do que uma lista literal de pares —
   mas o efeito prático é o mesmo: uma tabela de consulta pronta.)
3. Depois, para "quebrar" qualquer hash vazado, o atacante só **procura esse hash na
   tabela** — uma operação quase instantânea, em vez de recalcular tudo de novo.

**Por que salt destrói essa estratégia**: a tabela foi construída para `hash(senha)`,
sem salt. Se o sistema usa `hash(salt + senha)` e o salt é diferente por usuário, o
mesmo `"123456"` produz um hash diferente em cada conta — a tabela pré-calculada nunca
vai bater, e o atacante seria obrigado a construir uma tabela nova para **cada** salt
individual, o que elimina a vantagem de pré-calcular (o custo volta a ser o mesmo de um
ataque de força bruta online, só que agora offline e ainda lento por causa do algoritmo).

### Outras formas de "quebrar" senhas/hashes

Nenhuma delas reverte o hash matematicamente — todas são variações de **adivinhar a
entrada e comparar o hash resultante**:

- **Ataque de dicionário**: testar uma lista de senhas reais, vazadas de outros sites ao
  longo dos anos (ex.: a lista `rockyou.txt`, com ~14 milhões de senhas reais vazadas,
  amplamente usada em treinamentos e pentests). Extremamente eficaz porque pessoas
  reutilizam um conjunto pequeno de padrões de senha.
- **Força bruta (brute force)**: testar sistematicamente todas as combinações possíveis
  de caracteres até um certo tamanho (`a`, `b`, ..., `aa`, `ab`, ...). Garante achar a
  senha eventualmente, mas o tempo cresce exponencialmente com o tamanho/complexidade —
  por isso só é viável contra hashes rápidos (MD5/SHA-1/SHA-256 puro) ou senhas curtas.
- **Mask attack**: força bruta "inteligente", quando o atacante já sabe parte do
  formato (ex.: "sempre 8 caracteres, termina em 2 dígitos") e restringe o espaço de
  busca a esse padrão, em vez de testar tudo.
- **Ataque híbrido**: combina dicionário + mutações (acrescentar números/símbolos no
  fim, trocar `a` por `@`, capitalizar a primeira letra) — cobre o comportamento comum
  de "senha-base + variação" que usuários reais seguem para tentar satisfazer regras de
  complexidade.
- **Credential stuffing**: nem tenta quebrar hash nenhum — usa pares `email:senha` já
  vazados em texto puro de **outros** sistemas (exatamente o tipo de dado exposto pela
  falha deste guia) e testa em massa contra o sistema alvo, apostando na reutilização de
  senha entre serviços diferentes.

### Ferramentas comumente usadas (contexto de pentest/CTF autorizado)

| Ferramenta                                         | Tipo                                                      | Observação                                                                                                                                                                                                                      |
| -------------------------------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Hashcat**                                        | Cracker de hash com aceleração por GPU                    | A mais usada atualmente; suporta centenas de formatos de hash (MD5, SHA-*, bcrypt, etc.) e todos os modos de ataque acima (dicionário, força bruta, máscara, híbrido, regras).                                                  |
| **John the Ripper**                                | Cracker de hash (CPU, com variante "Jumbo" mais completa) | Um dos mais antigos e tradicionais; forte em detectar automaticamente o formato do hash e aplicar regras de mutação sobre wordlists.                                                                                            |
| **CrackStation / sites de "hash lookup"**          | Rainbow table pronta, consultável online                  | Serviços que mantêm bilhões de pares hash→senha pré-calculados para hashes sem salt (MD5/SHA-1/SHA-256); cola o hash e, se ele já foi quebrado antes por alguém, devolve a senha na hora — exatamente o cenário descrito acima. |
| **Wordlists públicas** (`rockyou.txt`, `SecLists`) | Dicionários de senhas reais vazadas                       | Matéria-prima dos ataques de dicionário/híbrido; `SecLists` (projeto no GitHub) reúne dezenas de listas temáticas usadas em pentest.                                                                                            |
| **Burp Suite / DevTools do navegador**             | Interceptação de tráfego                                  | Não quebra hash — mas é como se captura a senha **em claro** antes mesmo dela virar hash, exatamente como feito na Parte 1 deste guia (quando não há hash nem HTTPS no meio).                                                   |

> Importante: usar essas ferramentas contra sistemas sem autorização explícita é crime
> (no Brasil, pode se enquadrar na Lei 12.737/2012 e no Marco Civil da Internet, entre
> outros). O uso legítimo é em ambientes de laboratório como este [[Projeto00]], CTFs, ou
> engajamentos de pentest formalmente autorizados pelo dono do sistema.

### Por que isso reforça a escolha de Argon2/bcrypt/scrypt/PBKDF2

Toda essa seção existe para deixar concreto **por que velocidade e salt são os dois
fatores que mais importam**: um hash rápido e sem salt (MD5/SHA-1/SHA-256 puro) cai para
ataques de dicionário em segundos e pode já estar pré-quebrado numa rainbow table
pública; um hash lento, memory-hard e com salt único (Argon2/bcrypt/scrypt) obriga o
atacante a gastar segundos (em vez de nanossegundos) **por tentativa, por usuário**,
tornando até um dicionário de 14 milhões de senhas um ataque que levaria dias ou meses,
mesmo com GPUs potentes.
