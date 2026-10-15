# Projeto01 — Ataque A04: Cryptographic Failures (hash MD5 sem salt)

Guia prático, passo a passo, de como quebrar as senhas do [[Projeto01]], cujo hash é
**MD5 sem salt**, já catalogado em [[Projeto01/Vulnerabilidades]] (item 1). É uma
evolução do [[Projeto00/Ataque-A04-CryptographicFailures]] — lá a senha estava em texto
puro (bastava ler); aqui é preciso **quebrar um hash fraco**, o que introduz as técnicas
reais de cracking (dicionário, rainbow table) resumidas naquele guia e aplicadas aqui na
prática.

> Nota de versão: esta categoria é **A04** na edição 2025 (vigente) do
> [[OWASP Top 10]]; na edição 2021 era numerada **A02**.

Leia [[Projeto00/Ataque-A04-CryptographicFailures]] antes deste guia, especialmente a
seção final "Sobre criptografia de senha" — ela explica **por que** MD5 sem salt cai tão
rápido; este guia foca só na exploração prática contra o [[Projeto01]].

Público-alvo: iniciante em segurança ofensiva — assume que você sabe usar o DevTools e
consegue instalar/rodar uma ferramenta de linha de comando gratuita.

## Pré-requisitos

- [[Projeto01/Backend|api01]] rodando em `http://localhost:8000`.
- [[Projeto01/Frontend|client01]] rodando em `http://localhost:4200`.
- Um usuário de teste cadastrado com uma senha **comum/fraca** (ex.: `123456` ou
  `password`), para que o ataque de dicionário tenha sucesso rápido — é exatamente esse
  tipo de senha que o ataque de dicionário/rainbow table quebra em segundos.
- **Hashcat** ou **CrackStation** (`crackstation.net`, consulta online gratuita de
  rainbow table) — qualquer um dos dois serve para a Parte 2.
- **DB Browser for SQLite** (`sqlitebrowser.org`), para abrir o `db.sqlite3` na Parte 1.

## O que é a vulnerabilidade, em uma frase

`usuarios/views.py` calcula `hashlib.md5(senha.encode('utf-8')).hexdigest()` e guarda
esse valor em `Usuario.senha` — sem nenhum salt (valor aleatório único por usuário
misturado à senha antes do hash). MD5 é um algoritmo de hash **rápido** e **sem
salt torna o mesmo valor reproduzível por qualquer atacante para qualquer senha
candidata, uma única vez, para todas as contas do mundo** (rainbow table — ver
explicação detalhada em [[Projeto00/Ataque-A04-CryptographicFailures]]).

---

## Parte 1 — Obter o hash MD5 de uma conta

Diferente do [[Projeto00]], aqui a senha **não** volta em claro na resposta da API
(`usuario_para_json` não inclui `senha`) — então o caminho de exploração é obter o hash
diretamente do banco ou do admin, não da rede.

1. Localize o arquivo do banco: `Projeto01/api01/db.sqlite3`.
2. Abra o **DB Browser for SQLite**, **Open Database** nesse arquivo.
3. Aba **Execute SQL**, rode:
   ```sql
   SELECT email, senha FROM usuarios_usuario;
   ```
4. Anote o hash da conta de teste, por exemplo:
   ```
   vitima@teste.com | e10adc3949ba59abbe56e057f20f883e
   ```
   (esse é exatamente o MD5 de `"123456"` — confirme calculando você mesmo:
   `echo -n "123456" | md5sum` no terminal, ou qualquer calculadora MD5 online, deve
   devolver o mesmo valor.)

## Parte 2 — Quebrar o hash com uma rainbow table pública

Como não há salt, o hash de uma senha comum **já foi calculado e publicado por outra
pessoa antes** — não é preciso nem instalar nada.

1. Acesse `https://crackstation.net` (ou outro serviço de "hash lookup" equivalente).
2. Cole o hash obtido na Parte 1 (`e10adc3949ba59abbe56e057f20f883e`) no campo de busca.
3. O serviço devolve a senha original instantaneamente: `123456`.

**Por que isso funciona tão rápido**: alguém, em algum momento, já calculou o MD5 de
milhões de senhas comuns e publicou a tabela de busca `hash → senha`. Sem salt, o MD5 de
`"123456"` é **sempre o mesmo valor**, para qualquer sistema do mundo — então a consulta
é só uma busca em tabela, não um cálculo.

## Parte 3 — Quebrar com Hashcat (quando a senha não está em nenhuma rainbow table pública)

Para senhas um pouco menos comuns (mas ainda fracas), uma consulta online pode não ter o
hash pré-calculado — aí entra um cracker de verdade, rodando um ataque de dicionário
localmente.

1. Salve o hash num arquivo, ex. `hashes.txt`:
   ```
   e10adc3949ba59abbe56e057f20f883e
   ```
2. Baixe uma wordlist de senhas vazadas (ex. `rockyou.txt`, amplamente usada em
   treinamentos de segurança).
3. Rode o Hashcat no modo MD5 (`-m 0`) com ataque de dicionário:
   ```bash
   hashcat -m 0 -a 0 hashes.txt rockyou.txt
   ```
4. Em segundos (MD5 é extremamente rápido de calcular em GPU — bilhões de tentativas por
   segundo), o Hashcat imprime `e10adc3949ba59abbe56e057f20f883e:123456`.

## Parte 4 — Confirmando o impacto: login com a senha recuperada

1. Volte para `http://localhost:4200/login`.
2. Entre com o email da vítima e a senha recuperada (`123456`).
3. Login bem-sucedido — prova de que a senha quebrada é válida e utilizável para
   assumir a conta da vítima.

## Passo final — Documentar o achado

- **Vulnerabilidade**: hash de senha MD5 sem salt (`usuarios/views.py:hash_md5`,
  `usuarios/models.py`, campo `senha`).
- **Passos para reproduzir**: Partes 1–4 acima.
- **Evidência**: print da consulta SQL com o hash (Parte 1), print do resultado do
  CrackStation ou da saída do Hashcat (Partes 2–3), print do login bem-sucedido com a
  senha recuperada (Parte 4).
- **Impacto**: qualquer acesso ao banco (vazamento, backup, acesso indevido ao servidor)
  permite recuperar a senha original de qualquer conta cuja senha seja comum ou
  mediamente fraca — em segundos via rainbow table, em minutos/horas via dicionário —
  comprometendo não só esse sistema, mas qualquer outro onde a vítima reutilize a mesma
  senha (muito comum na prática).
- **Causa raiz**: função de hash rápida (MD5) e sem salt — ver análise completa de "por
  quê" em [[Projeto00/Ataque-A04-CryptographicFailures]].

## Mitigação

Já detalhado em [[Projeto01/Vulnerabilidades]] (item 1) e, em profundidade conceitual,
em [[Projeto00/Ataque-A04-CryptographicFailures]]:

1. Trocar `hashlib.md5(...)` por `django.contrib.auth.hashers.make_password()`
   (PBKDF2/Argon2) ao cadastrar e `check_password()` ao autenticar — gera salt único por
   usuário automaticamente e usa um algoritmo deliberadamente lento.
2. Nunca reutilizar a mesma senha entre sistemas (orientação para usuários finais, não
   corrige a causa raiz, mas reduz o impacto de um vazamento).
