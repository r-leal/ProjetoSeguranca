# Regras do repositório ProjetoSeguranca

## Documentação — sempre no vault do Obsidian

Toda documentação extensa sobre os projetos (visão/objetivo, modelo de dados, decisões
técnicas, vulnerabilidades propositais, evolução de segurança etc.) deve ser registrada
dentro do vault do Obsidian em `Documentação/`, na raiz do repositório — nunca em
arquivos `.md` soltos dentro da pasta de cada projeto. READMEs curtos de instruções de
execução (`ProjetoNN/README.md`) continuam ok, mas não substituem a documentação do
vault.

Além da documentação por projeto, o vault também pode ter subdiretórios de referência
transversal, não ligados a um projeto específico (ex.: `Documentação/OWASP Top 10/`).
Esses seguem o mesmo princípio de um arquivo por tema, mas sem a exigência de nome igual
a uma pasta de projeto.

### Estrutura obrigatória (documentação por projeto)

- Um subdiretório por projeto dentro de `Documentação/`, nomeado **exatamente igual** à
  pasta do
  projeto no repositório (sem espaços, mesma capitalização). Ex.: para `Projeto00/` →
  `Documentação/Projeto00/`.
- Dentro da subpasta do projeto, usar um arquivo por tema conforme o conteúdo crescer:
  - `Visao.md` — objetivo, descrição funcional, telas, modelo de dados.
  - `Vulnerabilidades.md` — vulnerabilidades propositais/encontradas e como explorá-las.
  - `Decisoes.md` — decisões técnicas e trade-offs.
  - Outros arquivos temáticos conforme necessário.
- Enquanto o conteúdo for pequeno, é aceitável um único arquivo
  `Documentação/ProjetoNN/ProjetoNN.md` cobrindo tudo; dividir em arquivos temáticos
  quando crescer.
- Antes de criar documentação nova, verificar se a subpasta do projeto já existe em
  `Documentação/` e reaproveitar os arquivos existentes em vez de criar duplicados.

### Identificação inequívoca do projeto

Como o vault conterá **vários projetos mostrando a evolução de segurança** (do inseguro
de propósito ao hardened), cada documento deve deixar claro, já no título/cabeçalho, a
qual projeto pertence — mesmo que o arquivo seja aberto fora do contexto da pasta:

- Título do documento no formato `# ProjetoNN — Tema` (ex.: `# Projeto00 — Visão`), nunca
  apenas `# Visão`.
- Se o documento fizer referência a outro projeto (comparação, evolução), linkar
  explicitamente pelo nome completo (`[[Projeto00]]`, `[[Projeto01]]`), nunca por termos
  genéricos como "o projeto anterior".
