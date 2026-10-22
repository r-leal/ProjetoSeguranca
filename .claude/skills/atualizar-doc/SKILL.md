---
name: atualizar-doc
description: "Cria ou atualiza a documentação do vault (Documentação/ProjetoNN/) de um dos projetos deste repositório — Estrutura, Backend, Frontend, Visão, Vulnerabilidades, Melhorias (comparado só com o projeto imediatamente anterior) e guias de Ataque por código OWASP — a partir da leitura do código-fonte atual de apiNN/clientNN, no mesmo formato usado para o Projeto00. Use quando o usuário pedir para atualizar/gerar/sincronizar a documentação de um ProjetoNN, passando o número do projeto (ex.: \"01\", \"1\", \"Projeto02\")."
---

# atualizar-doc

Gera ou atualiza `Documentação/ProjetoNN/` para o projeto indicado em `args`, no mesmo
padrão já estabelecido em `Documentação/Projeto00/` (que é a referência de formato —
releia-a sempre que precisar comparar estilo, nunca invente um formato novo).

Esta skill roda **inline**, nesta própria conversa (não como subagente em background) —
o usuário deve poder acompanhar e comentar o que está sendo escrito.

## 1. Resolver o número do projeto

`args` traz o projeto pedido. Normalize para o formato `NN` com dois dígitos:
- `"1"` ou `"01"` → `01`
- `"Projeto1"` / `"projeto 1"` / `"P01"` → `01`
- Se `args` vier vazio ou ambíguo, pergunte ao usuário qual projeto antes de continuar.

A partir daqui, `NN` = o número normalizado (ex. `01`), e:
- Pasta do backend: `ProjetoNN/apiNN/`
- Pasta do frontend: `ProjetoNN/clientNN/`
- Pasta de documentação a criar/atualizar: `Documentação/ProjetoNN/`

Se `ProjetoNN/` não existir no repositório, pare e avise o usuário — não documente um
projeto inexistente.

Calcule também `NN_anterior` = `NN - 1`, com dois dígitos (ex. `NN=02` → `NN_anterior=01`).
Esse é **o único** projeto anterior usado como referência de comparação em todo o
restante desta skill — nunca agregue ou compare com `NN-2`, `NN-3`, etc., mesmo que
existam. Se `NN == 00` (primeiro projeto da série), não há `NN_anterior`: pule qualquer
seção/documento que dependa de comparação com o projeto anterior (notadamente
`Melhorias.md`, seção 4).

## 2. Ler a convenção do vault

Releia `CLAUDE.md` (raiz do repo) antes de escrever qualquer arquivo. Regras que não
podem ser violadas:
- Documentação extensa vai em `Documentação/ProjetoNN/`, nunca em `.md` soltos dentro da
  pasta do projeto.
- Um arquivo por tema dentro da subpasta (pode crescer; não force um único arquivo se já
  há conteúdo dividido).
- Título do documento sempre `# ProjetoNN — Tema` (nunca só `# Tema`).
- Referência a outro projeto sempre pelo nome completo em link (`[[Projeto00]]`,
  `[[Projeto01]]`), nunca por termos genéricos como "o projeto anterior".

## 3. Ler o estado atual — documentação existente e código-fonte

**Não overwrite sem ler primeiro.** Se `Documentação/ProjetoNN/` já existir, leia tudo
antes de editar: pode haver decisões, correções já aplicadas (ex.: um item documentado
como "(Correção)" em vez de vulnerabilidade) ou numeração de itens que precisa ser
preservada/ajustada, não reescrita do zero. Prefira `Edit` a `Write` quando o arquivo já
existir e a mudança for incremental.

Releia também a documentação de `Projeto<NN_anterior>` (o único projeto anterior — ex.:
ao documentar `Projeto02`, releia `Documentação/Projeto01/*`, nunca
`Documentação/Projeto00/*` diretamente) para saber o que já foi classificado como
"herdado sem alteração", "corrigido" ou "vulnerabilidade proposital nova" — e não
duplicar texto que já existe lá; linke de volta em vez de copiar. Itens que
`Projeto<NN_anterior>` já descreve como "herdados de Projeto<NN-2>" permanecem herdados
por transitividade — você não precisa reabrir `Projeto<NN-2>`, só confiar na
classificação que `Projeto<NN_anterior>` já fez.

Depois, leia o código-fonte **completo e atual** de `ProjetoNN` — nunca documente a
partir de memória de uma conversa anterior, ele pode ter mudado:

**Backend (`apiNN/`)**
- `apiNN/settings.py`, `apiNN/urls.py`, `manage.py`, `requirements.txt`, `.gitignore`
- Para cada app (ex. `usuarios`, `tarefas`, e qualquer outro que exista): `models.py`,
  `views.py`, `urls.py`, `admin.py`, `apps.py`, e os arquivos em `migrations/` (para
  confirmar o schema real, não só o que `models.py` declara)
- Qualquer módulo auxiliar que não exista no Projeto00 (ex.: `jwt_utils.py`,
  `decorators.py`) — leia por completo, essas costumam ser exatamente onde vulnerabilidades
  ou correções propositais vivem

**Frontend (`clientNN/`)**
- `src/app/app.config.ts`, `app.routes.ts`, `app.component.ts`
- `src/app/core/api.config.ts`, `core/models/*.ts`, `core/services/*.ts`,
  `core/interceptors/*.ts` (se existir)
- Cada componente em `src/app/pages/*/`: o `.ts` (lógica) e o `.html` (template) — preste
  atenção especial a `[innerHTML]`, `bypassSecurityTrustHtml`, chamadas HTTP sem
  tratamento de erro, uso de `localStorage`/`sessionStorage`, e qualquer lógica de
  autorização feita só no cliente
- `package.json` para a lista de bibliotecas

Se o projeto tiver mais apps/páginas do que o Projeto00, documente todos — não assuma que
a estrutura é idêntica.

Para escrever `Melhorias.md` (seção 4), você também precisa ter lido o código-fonte de
`Projeto<NN_anterior>/api<NN_anterior>/` e `Projeto<NN_anterior>/client<NN_anterior>/`
com o mesmo nível de detalhe — a comparação é código-contra-código, não só
doc-contra-doc.

## 4. Produzir/atualizar os documentos

Todos em português, mesmo tom técnico-didático do Projeto00, com links `[[ProjetoNN/Arquivo]]`
e `[[ProjetoNN/Arquivo|Texto alternativo]]` quando precisar de um texto de link diferente
do nome do arquivo. Título de cada documento: `# ProjetoNN — <Tema>`.

### `Visao.md`
Objetivo do projeto (o que ele demonstra/evolui em relação ao projeto anterior, se for
uma evolução — linkando o projeto anterior pelo nome completo), descrição funcional,
telas, campos de cadastro, modelo de dados em tabela (Usuário, e cada entidade de
domínio), stack, aviso educacional padrão. Se for uma evolução de outro projeto, inclua
uma seção "O que mudou em relação ao [[ProjetoXX]]" numerada, igual ao que já existe em
`Documentação/Projeto01/Visao.md` — use-o de referência de formato se `NN > 00`.

### `Estrutura.md`
Índice em tabela linkando os outros documentos deste projeto (incluindo `Melhorias.md`,
quando existir), tabela "visão geral dos subprojetos" (pasta, stack, papel), e um
diagrama ASCII do fluxo ponta a ponta (frontend → HTTP/JSON → backend → ORM → banco), no
mesmo estilo do diagrama em `Documentação/Projeto00/Estrutura.md`.

### `Backend.md`
Arquitetura (camadas reais do código, não um MVC genérico — descreva o que o código faz),
diagrama de fluxo de requisição, organização de pastas (árvore), tabela de apps de
domínio, modelo de dados por model (campos, tipo Django, observações — marcando campos
sensíveis/inseguros), tabela de rotas da API por app (método, rota, view, input, output),
bibliotecas (`requirements.txt` em tabela), configurações relevantes de `settings.py`.
Sinalize com ⚠️ qualquer comportamento inseguro notável direto no corpo do texto (sem
repetir a análise completa, que vai em `Vulnerabilidades.md` — só apontar e linkar).

### `Frontend.md`
Arquitetura (árvore de dependência entre `main.ts` → `app.config.ts` → `app.routes.ts` →
`pages/` → `core/`), organização de pastas, tabela de rotas/páginas, uma subseção por
componente de página descrevendo estado local e ações (igual ao Projeto00), tabela da
camada `core` (arquivo → papel), seção de armazenamento local (o que é persistido, onde,
por quanto tempo, quem consegue ler), bibliotecas (`package.json` em tabela).

### `Vulnerabilidades.md`
Foque no que é **próprio deste projeto** — vulnerabilidades novas, vulnerabilidades
herdadas que mudaram de forma, e **correções** aplicadas em relação ao projeto anterior.
Para herdados sem nenhuma alteração, não duplique: cite o projeto anterior
(`[[ProjetoXX/Vulnerabilidades]]`, item N) e siga adiante.

Formato por item, numerado: **o que é** → **arquivo(s)** → **como explorar** →
**mitigação**. Itens que são correções (não vulnerabilidades) devem ser marcados
explicitamente como `## N. (Correção) <título>` — ver exemplo em
`Documentação/Projeto01/Vulnerabilidades.md` item 6 — e não contam como vulnerabilidade
exploravél no resumo/tabela.

Termine com uma tabela "Resumo" classificando cada vulnerabilidade pela **edição vigente
do OWASP Top 10 (2025)**, com o código (ex. `A01`, `A03`, `A04`, `A05`, `A07`) e uma nota
da complexidade de exploração — igual ao Projeto00. Sempre linke `[[OWASP Top 10]]` na
primeira menção. Verifique o código correto na edição 2025 antes de escrever — não
reutilize de memória o código de 2021 sem checar se mudou (várias categorias foram
renumeradas entre 2021 e 2025; ver notas de versão nos guias de Ataque do Projeto00 como
referência dos mapeamentos já confirmados: A01↔A01, A02(2021)→A04(2025) cripto, A03(2021)
Injection→A05(2025) Injection, A05(2021) Misconfig→A02(2025), A07(2021)↔A07(2025) Auth
Failures).

### `Melhorias.md` (só existe se houver `NN_anterior`; pule inteiramente para `NN == 00`)

Documenta **o que melhorou** de `Projeto<NN_anterior>` para `ProjetoNN` — a contrapartida
de `Vulnerabilidades.md`, que documenta o que continua/ficou pior. Regra inegociável:
**compare sempre com `Projeto<NN_anterior>`, nunca com qualquer projeto mais antigo que
esse**, mesmo que a melhoria "pareça" remontar a algo de duas ou três versões atrás — do
ponto de vista deste documento, a baseline é sempre a imediatamente anterior.

Título: `# ProjetoNN — Melhorias em relação ao [[Projeto<NN_anterior>]]`.

Conteúdo, organizado em categorias (omita qualquer categoria vazia):

1. **Vulnerabilidades corrigidas** — toda vulnerabilidade listada em
   `Documentação/Projeto<NN_anterior>/Vulnerabilidades.md` que `ProjetoNN` efetivamente
   corrigiu (não só mitigou parcialmente). Para cada uma: `item X de
   [[Projeto<NN_anterior>/Vulnerabilidades]]` → o que mudou no código → por que isso
   fecha a causa raiz (ou, se fechar só parcialmente, diga exatamente o que ainda falta e
   linke o item correspondente que documenta o restante em `Vulnerabilidades.md` deste
   projeto). Use como referência de tom e nível de detalhe o item "6. (Correção)..." já
   escrito em `Documentação/Projeto01/Vulnerabilidades.md` — mas aqui o lugar certo para
   essa narrativa é `Melhorias.md`, não mais dentro de `Vulnerabilidades.md` (a partir de
   agora, correções vão em `Melhorias.md`; `Vulnerabilidades.md` fica só com o que
   permanece explorável).
2. **Hardening/qualidade sem ser correção de uma vulnerabilidade específica** — ex.:
   tratamento de erro adicionado, interceptor HTTP novo, endpoint novo que reduz
   superfície de confiança no cliente, testes adicionados. Qualquer melhoria de código
   que não estava fechando um item numerado de `Vulnerabilidades.md`.
3. **Funcionalidades novas não seguras/relacionadas a segurança** (se houver) — recursos
   novos que não são nem vulnerabilidade nem correção, só evolução funcional (ex.: um
   campo novo, uma tela nova). Mencione brevemente só para a Visão ficar completa; o
   detalhe funcional mesmo pertence a `Visao.md`/`Backend.md`/`Frontend.md` — aqui é só
   "o que isso significa em termos de melhoria", se for o caso.

Feche com uma tabela resumo (uma linha por melhoria): `# | Melhoria | Categoria | Item
correspondente em Vulnerabilidades.md (se houver)`.

Depois de escrever `Melhorias.md`, remova de `Vulnerabilidades.md` deste projeto qualquer
narrativa de correção que tenha migrado para lá (mantenha só a classificação/tabela
resumo e links cruzados — não duplique o texto inteiro nos dois arquivos).

### `Ataque-<CODIGO>-<NomeCurto>.md` (um por vulnerabilidade real explorável)

Só escreva um guia novo para vulnerabilidades **novas ou alteradas** neste projeto —
nunca duplique um guia de ataque que já documenta exatamente a mesma falha sem mudança
nenhuma; linke o guia existente do projeto anterior em vez disso (ex.:
`[[Projeto00/Ataque-A05-StoredXSS]]`). Não escreva guia de ataque para itens marcados como
"(Correção)" — esses não são exploráveis.

Nomeie o arquivo como `Ataque-<CODIGO-OWASP-2025>-<NomeCurtoEmCamelCase>.md` (ex.
`Ataque-A05-SQLInjectionFiltro.md`), espelhando exatamente o padrão dos arquivos existentes
em `Documentação/Projeto00/`. Estrutura obrigatória de cada guia (ver os três exemplos em
Projeto00 — A01, A04 e A05 — como referência de profundidade e tom):

1. Título `# ProjetoNN — Ataque <CÓDIGO>: <Nome da categoria>` + um parágrafo linkando a
   vulnerabilidade já catalogada em `[[ProjetoNN/Vulnerabilidades]]` (item correspondente).
2. Nota de versão do OWASP Top 10 (2025 vigente vs. 2021), mesmo quando o código não
   mudou entre as edições — deixe isso explícito.
3. Público-alvo (uma linha, nivelando a expectativa de conhecimento prévio).
4. "Pré-requisitos" — backend/frontend rodando (portas reais do projeto), dados de teste
   necessários (ex. dois usuários cadastrados).
5. "O que é a vulnerabilidade, em uma frase" — citando arquivo e trecho de código real.
6. Passos numerados de exploração **reais e específicos ao código efetivamente lido** —
   nunca genéricos. Inclua comandos `curl`/`fetch`/DevTools concretos com as rotas e
   payloads reais do projeto (teste mentalmente contra o código lido antes de escrever um
   payload — ele precisa realmente produzir o efeito descrito na consulta/lógica real).
7. "Passo final — Documentar o achado": vulnerabilidade, passos para reproduzir,
   evidência, impacto, causa raiz.
8. "Mitigação" linkando de volta para o item correspondente em `Vulnerabilidades.md`.

Se uma vulnerabilidade for genuinamente complexa (ex. criptografia fraca, como no guia
A04 do Projeto00), pode valer a pena uma seção didática extra ao final explicando o
conceito de fundo — siga esse mesmo padrão quando fizer sentido, sem forçar em casos
simples.

## 5. Verificação antes de finalizar

- Toda referência a arquivo/linha/trecho de código citada nos documentos precisa
  realmente existir no código lido nesta execução — não herde de memória de uma
  conversa anterior sem reconfirmar.
- Todo payload de exploração escrito num guia de Ataque precisa ser plausível contra a
  lógica real do código (se o código mudou desde a última vez que você documentou algo
  parecido, o payload pode já não funcionar — revalide).
- Nenhuma vulnerabilidade deve ser inventada: só documente o que o código efetivamente
  apresenta. Se o projeto já corrigiu algo que `Projeto<NN_anterior>` tinha, isso vai em
  `Melhorias.md`, não em `Vulnerabilidades.md`.
- Toda melhoria listada em `Melhorias.md` precisa comparar exclusivamente com
  `Projeto<NN_anterior>` — se, relendo o texto, você citou `Projeto<NN-2>` ou mais antigo
  como baseline de comparação, corrija antes de finalizar.
- Links `[[...]]` sempre com o nome completo do projeto/arquivo referenciado.

## 6. Fechar

Resuma ao usuário, em poucas linhas, quais arquivos foram criados e quais foram
atualizados (e por quê, se a mudança for notável) — sem reproduzir o conteúdo inteiro no
chat.
