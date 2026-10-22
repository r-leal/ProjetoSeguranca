# Projeto00 — Ataque A05: Injection (XSS Armazenado na descrição da tarefa)

Guia prático, passo a passo, de como explorar um **Cross-Site Scripting (XSS)
armazenado** no [[Projeto00]] (frontend `client00`) — introduzido de propósito no campo
`descricao` das tarefas do Kanban, já catalogado em [[Projeto00/Vulnerabilidades]] (item
10). Complementa [[Projeto00/Ataque-A01-BrokenAccessControl]] e
[[Projeto00/Ataque-A04-CryptographicFailures]]: os três guias cobrem falhas distintas do
mesmo projeto-base.

> Nota de versão: XSS é classificado dentro de **A05 Injection** na edição 2025
> (vigente) do [[OWASP Top 10]]; na edição 2021 era **A03 Injection**. O conteúdo técnico
> abaixo não muda — só a numeração oficial.

Público-alvo: iniciante em segurança ofensiva — assume que você sabe usar o DevTools do
navegador.

## Pré-requisitos

- [[Projeto00/Backend|api00]] rodando em `http://localhost:8000`.
- [[Projeto00/Frontend|client00]] rodando em `http://localhost:4200`.
- O usuário `ana@example.com` (id `1`) já tem uma tarefa de demonstração cadastrada
  (criada direto no banco para este guia — ver Parte 0).

## O que é a vulnerabilidade, em uma frase

`kanban.component.html` renderiza a descrição da tarefa com
`[innerHTML]="descricaoHtml(tarefa)"`, e `descricaoHtml()` usa
`DomSanitizer.bypassSecurityTrustHtml(tarefa.descricao)` — ou seja, **desliga de
propósito** o sanitizador que o Angular aplicaria por padrão a qualquer `[innerHTML]`.
Como a `descricao` vem direto do que o usuário digitou no formulário "Nova tarefa" (ou do
corpo JSON enviado a `POST /api/tarefas`), qualquer HTML/JS colocado ali é renderizado
sem filtro para **qualquer pessoa que abrir aquele cartão do Kanban** — inclusive outro
usuário, já que não há checagem de dono (reforça o IDOR do item 3 de
[[Projeto00/Vulnerabilidades]]).

### Por que o payload não é um `<script>` puro

Um detalhe técnico que costuma confundir quem está começando: **inserir uma tag
`<script>` via `innerHTML` não executa o script** — essa é uma restrição da própria
especificação do DOM (`Element.innerHTML`), não uma proteção do Angular. Navegadores
modernos ignoram `<script>` quando ele é injetado dessa forma.

O caminho que **de fato** executa JavaScript via `innerHTML` é usar uma tag com um
**atributo de evento inline** (`onerror`, `onload`, `onclick`...) que o navegador dispara
sozinho ao renderizar o elemento — por exemplo uma `<img>` com `src` inválido, que
dispara `onerror` ao falhar o carregamento.

---

## Parte 0 — O payload usado (já cadastrado na tarefa de demonstração)

```html
<img src="x" onerror="
  (function(){
    var d = JSON.stringify(localStorage);
    alert('Dados roubados do localStorage:\n' + d);
  })()
">
```

O que cada parte faz:
1. `<img src="x" onerror="...">` — a URL `"x"` não é uma imagem válida, então o
   navegador dispara o evento `onerror` imediatamente após tentar (e falhar) carregá-la.
2. `JSON.stringify(localStorage)` — serializa **todo** o conteúdo do `localStorage` do
   domínio atual (no Projeto00, isso inclui a chave `usuario_logado`, com o objeto
   `Usuario` completo — nome, email e, por causa do item 1 de
   [[Projeto00/Vulnerabilidades]], a **senha em texto puro**).
3. `alert(...)` — mostra o conteúdo roubado na tela, só para efeito didático de prova de
   conceito (num ataque real, o atacante **não** mostraria um alerta — isso alertaria a
   vítima).
Esse registro já foi inserido diretamente na tabela `tarefas_tarefa` (coluna
`descricao`), associado ao usuário `ana@example.com` (id `1`), com o nome
"Tarefa de demonstracao XSS", para fins deste laboratório.

### Por que `mailto:` e não um envio de e-mail "silencioso"

Importante entender o limite real desta técnica: **JavaScript no navegador não consegue
enviar e-mail diretamente** sem passar por (a) um link `mailto:`, que abre o cliente de
e-mail e exige que a vítima clique em "Enviar", ou (b) uma requisição HTTP
(`fetch`/`XMLHttpRequest`) para um servidor controlado pelo atacante, que aí sim dispara
o e-mail do lado do backend. Este guia usa `mailto:` de propósito, por ser mais
transparente para fins didáticos — em um XSS real malicioso, a opção (b) é a mais usada,
justamente porque é silenciosa e não depende de ação da vítima.

## Parte 1 — Disparar o payload

1. Acesse `http://localhost:4200/login` e faça login como `ana@example.com` (ou qualquer
   usuário de teste).
2. Vá para `/kanban`.
3. Localize o cartão **"Tarefa de demonstracao XSS"** na coluna "Esperando".
4. No momento em que o Angular renderiza o cartão, o `<img>` tenta carregar `src="x"`,
   falha, e o `onerror` dispara:
   - Aparece um `alert()` com o conteúdo do `localStorage` (incluindo email e senha em
     claro do usuário logado).
   - Ao fechar o alerta, o navegador tenta abrir o cliente de e-mail padrão com uma
     mensagem pré-preenchida endereçada a `rafael.leal@inchurch.com.br`, assunto
     `[DEMO XSS] Exfiltracao Projeto00` e corpo contendo o JSON exfiltrado.

## Parte 2 — Reproduzir criando a tarefa pela própria UI (opcional)

Para ver o ataque de ponta a ponta, incluindo a etapa de "injeção" (e não só a de
execução):

1. No formulário "Nova tarefa" do Kanban, cole o mesmo payload da Parte 0 no campo
   **Descrição**.
2. Clique em "Adicionar tarefa".
3. O cartão aparece na coluna "Esperando" e, ao ser renderizado, dispara o mesmo
   `alert()` + tentativa de `mailto:` descritos na Parte 1 — provando que **qualquer**
   usuário com acesso ao formulário (sem precisar de acesso ao banco) consegue armazenar
   o payload, que executa para quem quer que abra aquele cartão depois.

## Passo final — Documentar o achado

- **Vulnerabilidade**: XSS armazenado via `[innerHTML]` + `bypassSecurityTrustHtml` sem
  sanitização (`kanban.component.ts`, método `descricaoHtml`; `kanban.component.html`,
  linha do `<p [innerHTML]="...">`).
- **Passos para reproduzir**: Partes 0–2 acima.
- **Evidência**: print do `alert()` mostrando o conteúdo do `localStorage`, e print do
  cliente de e-mail aberto com o corpo pré-preenchido.
- **Impacto**: qualquer pessoa que visualize o cartão da tarefa tem JavaScript arbitrário
  executado no contexto da própria aplicação — podendo ler `localStorage` (que hoje
  guarda até a senha em claro, item 1 de [[Projeto00/Vulnerabilidades]]), cookies não
  `httpOnly`, fazer requisições autenticadas em nome da vítima, redirecionar a página,
  ou — como demonstrado aqui — preparar a exfiltração dos dados roubados.
- **Causa raiz**: uso de `DomSanitizer.bypassSecurityTrustHtml()` sobre entrada do
  usuário não validada, combinado com a ausência total de sanitização de entrada no
  backend (item 8 de [[Projeto00/Vulnerabilidades]]) e com a falta de checagem de dono
  nas tarefas (item 3, IDOR) — que amplia o alcance do ataque para qualquer usuário do
  sistema, não só quem criou a tarefa.

## Mitigação

- **Nunca** usar `bypassSecurityTrustHtml` sobre texto vindo do usuário. Voltar à
  interpolação padrão do Angular (`{{ tarefa.descricao }}`), que escapa HTML
  automaticamente — essa é, por si só, a correção completa para este caso específico, já
  que a aplicação não precisa renderizar HTML/rich text na descrição.
- Se algum dia for necessário permitir HTML limitado (ex.: um editor rich text), usar uma
  biblioteca de sanitização dedicada (ex.: `DOMPurify`) com uma allowlist estrita de
  tags/atributos — nunca confiar em sanitização manual.
- Validar/limitar o conteúdo da descrição no backend (reforça o item 8 de
  [[Projeto00/Vulnerabilidades]]), como camada adicional de defesa em profundidade.
- Mover o "usuário logado" de `localStorage` para cookie `httpOnly` + `Secure` +
  `SameSite` (item 9 de [[Projeto00/Vulnerabilidades]]), para que, mesmo que um XSS volte
  a existir no futuro, o token de sessão não seja legível por JavaScript.

> Importante: usar esta técnica fora deste laboratório, sem autorização explícita do
> dono do sistema, é crime (no Brasil, Lei 12.737/2012 e Marco Civil da Internet, entre
> outros). O uso legítimo é em ambientes de laboratório como este [[Projeto00]], CTFs, ou
> engajamentos de pentest formalmente autorizados.
