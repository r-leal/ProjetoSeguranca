# OWASP Top 10

Documento de referência transversal do vault (não é específico de um projeto —
vale para todos: [[Projeto00]] e os que vierem depois). Serve de glossário/checklist ao
analisar vulnerabilidades de qualquer projeto do repositório — por exemplo,
[[Projeto00/Vulnerabilidades]] já classifica cada falha encontrada usando as categorias
listadas aqui.

## O que é o OWASP

**OWASP (Open Worldwide Application Security Project)** é uma fundação sem fins
lucrativos dedicada a melhorar a segurança de software. Mantém projetos abertos e
gratuitos — documentação, ferramentas, padrões e comunidades — voltados a
desenvolvedores, arquitetos e profissionais de segurança.

Entre os projetos mais conhecidos da OWASP estão:

- **OWASP Top 10** — as 10 categorias de risco mais críticas em aplicações web (este
  documento).
- **OWASP ASVS** (Application Security Verification Standard) — checklist detalhado de
  requisitos de segurança para verificação de aplicações.
- **OWASP Cheat Sheet Series** — guias práticos e objetivos de como implementar cada
  controle de segurança corretamente (ex.: "Password Storage Cheat Sheet").
- **OWASP ZAP** — ferramenta gratuita de teste de segurança (scanner de
  vulnerabilidades web).

## Como acessar

- Site oficial: **owasp.org**
- Página do Top 10 (edição atual): **top10.owasp.org/2025** (`owasp.org/Top10/2025/`
  redireciona para lá)
- Todo o conteúdo é aberto, gratuito e mantido pela comunidade (contribuições via GitHub
  da organização OWASP, repositório `OWASP/Top10`).

> O Top 10 é revisado periodicamente. A edição anterior era a **2021**; em novembro de
> 2025 a OWASP anunciou a revisão no OWASP Global AppSec Conference (Washington, D.C.),
> com a versão final publicada em janeiro de 2026 — esta é a edição vigente usada neste
> vault. Ao citar a lista em um relatório formal, vale sempre conferir no site oficial se
> já existe uma edição mais nova.

## O Top 10 (edição 2025)

| # | Categoria | Resumo |
|---|---|---|
| A01 | **Broken Access Control** (Quebra de Controle de Acesso) | Falhas que permitem a um usuário agir fora das permissões pretendidas — ex.: acessar/editar dados de outro usuário (IDOR), escalar privilégios, burlar checagem de autorização em rotas da API. Continua em 1º lugar e **passou a absorver o SSRF** (categoria própria em 2021), tratado agora como uma forma de acesso indevido a recursos. |
| A02 | **Security Misconfiguration** (Configuração Incorreta de Segurança) | Configurações padrão inseguras, serviços/debug expostos, headers de segurança ausentes, CORS liberado demais, mensagens de erro detalhadas em produção. Subiu da 5ª para a 2ª posição. |
| A03 | **Software Supply Chain Failures** (Falhas na Cadeia de Suprimento de Software) | **Categoria nova.** Expande o antigo "Vulnerable and Outdated Components" (2021) para cobrir toda a cadeia de fornecimento: dependências comprometidas, pipelines de build/CI inseguros, pacotes maliciosos publicados em repositórios públicos, falta de verificação de integridade de origem do código. |
| A04 | **Cryptographic Failures** (Falhas Criptográficas) | Dados sensíveis (senhas, tokens, dados pessoais) expostos por falta de criptografia, uso de algoritmos fracos/obsoletos, ou armazenamento em texto puro — ex.: senha salva sem hash. |
| A05 | **Injection** (Injeção) | Entrada do usuário interpretada como código/comando pelo backend — SQL Injection, Command Injection, XSS (Cross-Site Scripting) quando a saída não é sanitizada, LDAP/NoSQL injection, etc. |
| A06 | **Insecure Design** (Design Inseguro) | Falhas estruturais de concepção, não de implementação — ausência de controles de segurança já no desenho da funcionalidade (ex.: fluxo de recuperação de senha sem rate limit por design). |
| A07 | **Authentication Failures** (Falhas de Autenticação) | Falhas no processo de login/sessão — senhas fracas permitidas, ausência de MFA, tokens de sessão previsíveis ou que não expiram, força bruta sem bloqueio. (Em 2021 chamava-se "Identification and Authentication Failures".) |
| A08 | **Software or Data Integrity Failures** (Falhas de Integridade de Software ou Dados) | Código, pipelines de CI/CD ou atualizações/dados que não verificam integridade/assinatura — ex.: deserialização insegura. |
| A09 | **Security Logging and Alerting Failures** (Falhas de Registro e Alerta de Segurança) | Falta de logs de eventos de segurança (login, falhas de autorização) ou ausência de **alertas** acionáveis sobre eles — dificulta detectar e responder a incidentes. (Em 2021 era "...and Monitoring Failures".) |
| A10 | **Mishandling of Exceptional Conditions** (Tratamento Inadequado de Condições Excepcionais) | **Categoria nova**, substitui o SSRF (agora dentro de A01). Cobre tratamento de erro malfeito — exceções não tratadas que vazam stack trace/dados sensíveis, lógica de negócio que falha de forma insegura ("fail open" em vez de "fail closed"), mensagens de erro verbosas em produção. |

### O que mudou da edição 2021 para a 2025

- **Duas categorias novas**: A03 Software Supply Chain Failures e A10 Mishandling of
  Exceptional Conditions.
- **SSRF deixou de ser categoria própria** (era A10:2021) e passou a ser tratado como um
  caso de A01 Broken Access Control.
- **Security Misconfiguration subiu** da 5ª posição (2021) para a 2ª (2025).
- Pequenos ajustes de nome: "Identification and Authentication Failures" →
  "Authentication Failures" (A07); "...Logging and *Monitoring* Failures" →
  "...Logging and *Alerting* Failures" (A09).
- "Vulnerable and Outdated Components" (A06:2021) foi absorvido/expandido pelo novo A03
  Software Supply Chain Failures.

## Como usar isso no repositório

Ao documentar vulnerabilidades de um projeto (ex.: `Documentação/ProjetoNN/Vulnerabilidades.md`),
classificar cada achado com a categoria correspondente daqui (ex.: "A01 Broken Access
Control") deixa explícito o tipo de risco e facilita comparar a evolução de segurança
entre projetos do repositório. Como os guias de ataque existentes (ex.:
[[Projeto00/Ataque-A01-BrokenAccessControl]]) foram escritos citando um código de
categoria, ao reclassificar um achado para a edição 2025 deixe uma nota indicando
também o código antigo (2021), para não quebrar o contexto de quem já leu a versão
anterior.
