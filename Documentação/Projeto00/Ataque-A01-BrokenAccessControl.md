# Projeto00 — Ataque A01: Broken Access Control (IDOR)

Guia prático, passo a passo, de como explorar a falha de **A01 Broken Access Control**
(ver [[OWASP Top 10]]) no [[Projeto00]], especificamente a variante **IDOR (Insecure
Direct Object Reference)** já catalogada em [[Projeto00/Vulnerabilidades]] (item 3).

Este documento foca **somente** em Broken Access Control. As demais vulnerabilidades do
Projeto00 (senha em texto puro, CSRF, CORS, etc.) estão descritas em
[[Projeto00/Vulnerabilidades]] e serão exploradas em guias próprios de outros projetos.

> Nota de versão: A01 Broken Access Control é a categoria A01 tanto na edição 2021
> quanto na **edição 2025** (vigente) do [[OWASP Top 10]] — continua em 1º lugar e, em
> 2025, passou a absorver também o SSRF (que era categoria própria, A10, em 2021).

Público-alvo: iniciante em segurança ofensiva — o guia assume que você sabe navegar e
usar o DevTools do navegador, mas nunca interceptou/alterou uma requisição HTTP.

## Pré-requisitos

- [[Projeto00/Backend|api00]] rodando em `http://localhost:8000` (ver `Projeto00/api00/README.md`
  ou a conversa de setup do backend).
- [[Projeto00/Frontend|client00]] rodando em `http://localhost:4200` (`ng serve`).
- Dois usuários cadastrados no sistema, para provar que dá para ver dados de **outra**
  conta. Pela tela `/cadastro`, crie:
  - Usuário A: `vitima@teste.com` / senha `123456`
  - Usuário B: `atacante@teste.com` / senha `123456`
- Logado como Usuário A, crie pelo menos uma tarefa no Kanban (ex.: "Tarefa secreta da
  vítima") para ter algo identificável para "roubar" depois.

## O que é a vulnerabilidade, em uma frase

O backend ([[Projeto00/Backend]]) nunca checa **quem** está fazendo a requisição — ele
só confia no `usuario_id` que vem na própria URL. Trocar esse número na requisição é
suficiente para ler, editar ou apagar tarefas de qualquer outro usuário.

---

## Passo 1 — Fazer login e abrir o DevTools

1. Acesse `http://localhost:4200/login` e entre com o **Usuário A** (`vitima@teste.com`).
2. Antes de continuar, abra o DevTools do navegador apertando **F12** (ou
   `Ctrl+Shift+I`).
3. Clique na aba **Network** (Rede). Se não aparecer nada ainda, deixe o DevTools aberto
   e recarregue a página (`F5`) — é importante que o Network esteja gravando **antes** do
   Kanban carregar.

## Passo 2 — Observar a chamada que busca as tarefas

1. Com o DevTools aberto, navegue para `/kanban` (ou clique em "Entrar" se ainda estiver
   no login).
2. Na lista de requisições do Network, procure uma linha do tipo:
   ```
   GET  http://localhost:8000/api/usuarios/1/tarefas
   ```
   (o número `1` é o id do Usuário A — pode ser diferente no seu caso, dependendo da
   ordem de cadastro).
3. Clique nessa requisição. Olhe a aba **Response** (ou **Preview**) — você verá um JSON
   assim:
   ```json
   [
     {
       "id": 4,
       "usuario_id": 1,
       "nome": "Tarefa secreta da vítima",
       "descricao": "...",
       "data_prazo": null,
       "estado": "esperando"
     }
   ]
   ```

**O que reparar aqui**: a URL contém `usuarios/1/tarefas` — o `1` é literalmente o id do
usuário sendo consultado, exposto na própria rota. Isso é o primeiro sinal de uma
possível IDOR: sempre que um id "de quem é o dado" aparece na URL (em vez de o backend
descobrir isso sozinho a partir de quem está autenticado), vale testar trocar esse
número.

## Passo 3 — Confirmar que não existe nenhuma camada de autenticação

Repare que, nem na aba **Headers** da requisição, não existe nenhum `Authorization:
Bearer ...` nem cookie de sessão sendo enviado — porque o [[Projeto00/Frontend|client00]]
não implementa autenticação real, só guarda o usuário em `localStorage` (ver
[[Projeto00/Frontend]]). Isso confirma a suspeita: o backend não tem como saber quem é
"você" além do número que a própria URL carrega — e ele não confere nada.

## Passo 4 — Repetir a chamada trocando o id (a exploração em si)

Agora vamos simular o "Usuário B" (atacante) tentando ver as tarefas do "Usuário A"
(vítima), sem precisar nem saber a senha dele.

### Opção 1 — direto pela barra de endereço (mais simples)

1. Abra uma nova aba do navegador.
2. Digite diretamente: `http://localhost:8000/api/usuarios/1/tarefas`
3. O navegador faz um `GET` e mostra o JSON cru na tela — **as tarefas do Usuário A**,
   mesmo sem estar logado como ele.
4. Agora troque o número: `http://localhost:8000/api/usuarios/2/tarefas`,
   `.../3/tarefas`, etc. Cada número existente devolve as tarefas daquele usuário. Você
   acabou de enumerar os dados de qualquer conta do sistema só variando um número na
   URL.

### Opção 2 — reenviando pelo DevTools (mais realista, como um pentest de verdade)

1. Volte para a aba **Network** do DevTools (ainda logado como Usuário A).
2. Clique com o botão direito na requisição `GET /api/usuarios/1/tarefas` →
   **Copy → Copy as fetch** (no Chrome) ou **Copy → Copy Value → Copy as fetch**
   (dependendo da versão).
3. Abra a aba **Console** do DevTools.
4. Cole o comando copiado, mas **troque o `1` por outro id** antes de apertar Enter,
   por exemplo:
   ```js
   fetch("http://localhost:8000/api/usuarios/2/tarefas", {
     "headers": { "accept": "application/json" },
     "method": "GET"
   }).then(r => r.json()).then(console.log)
   ```
5. Aperte Enter. O Console imprime o array de tarefas do usuário `2` — executado a
   partir da própria sessão do navegador logado como Usuário A, sem nenhuma permissão
   verificada.

**Resultado**: você leu dados de uma conta que não é a sua, sem senha, sem token, só
trocando um número.

## Passo 5 — Ir além da leitura: editar e apagar tarefas de outra conta

A mesma falta de checagem vale para `PUT` e `DELETE` em `tarefa_detalhe`
(`/api/tarefas/<tarefa_id>`) — aqui o id que importa é o **da tarefa**, não o do dono, e
também não é validado.

1. No Console do DevTools (pode ser em qualquer aba, nem precisa estar logado), rode:
   ```js
   fetch("http://localhost:8000/api/tarefas/4", {
     method: "DELETE"
   }).then(r => console.log(r.status))
   ```
   Troque `4` pelo id da "Tarefa secreta da vítima" que você viu no Passo 2.
2. Volte para a aba do Usuário A no Kanban e dê um refresh — a tarefa sumiu, apagada por
   uma sessão que nunca foi autenticada como esse usuário.
3. Da mesma forma, um `PUT` no mesmo endpoint com um corpo JSON
   (`{"nome": "Tarefa alterada pelo atacante"}`) reescreve qualquer tarefa de qualquer
   usuário:
   ```js
   fetch("http://localhost:8000/api/tarefas/5", {
     method: "PUT",
     headers: { "Content-Type": "application/json" },
     body: JSON.stringify({ nome: "Pwned" })
   }).then(r => r.json()).then(console.log)
   ```

## Passo 6 — Documentar o achado (como em um relatório de pentest real)

Para transformar isso num relatório, anote sempre:

- **Endpoint vulnerável**: `GET/PUT/DELETE /api/tarefas/<tarefa_id>` e
  `GET /api/usuarios/<usuario_id>/tarefas`.
- **Passos para reproduzir**: exatamente os passos 1–5 acima.
- **Evidência**: print do JSON retornado com dados de outra conta (aba Network ou
  Console do DevTools).
- **Impacto**: qualquer usuário autenticado (ou até não autenticado, via chamada direta
  à API) pode ler, modificar ou apagar tarefas de qualquer outro usuário do sistema —
  perda de confidencialidade e integridade dos dados de todos os usuários.
- **Causa raiz**: nenhuma view confere posse do recurso (`tarefa.usuario_id ==
  usuário autenticado`) nem exige autenticação (ver [[Projeto00/Vulnerabilidades]],
  itens 3 e 4).

## Como esse ataque seria bloqueado (mitigação)

Já detalhado em [[Projeto00/Vulnerabilidades]] (item 3), resumindo para este guia:

1. **Autenticar cada requisição** (sessão Django ou token/JWT) — sem isso não dá nem
   para saber "quem" está pedindo.
2. **Checar posse do recurso em toda view**: antes de ler/editar/apagar uma `Tarefa`,
   confirmar que `tarefa.usuario_id == request.user.id`. O mesmo vale para a listagem —
   nunca confiar num id de usuário vindo da URL/body do cliente para decidir "de quem"
   mostrar dados; usar sempre o usuário autenticado da sessão/token.
3. Testar manualmente esse tipo de troca de id (exatamente os passos deste guia) sempre
   que uma nova rota autenticada for criada — é o teste mais barato de Broken Access
   Control que existe.
