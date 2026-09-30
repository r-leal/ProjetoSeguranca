# Projeto 00

## Objetivo

Projeto **00** é o nível mais básico e propositalmente **inseguro** do laboratório. O objetivo é demonstrar, de forma didática, as vulnerabilidades mais comuns e mais graves em uma aplicação web — construída sem nenhuma preocupação de segurança — para depois servir de base de comparação com versões mais seguras (Projeto 01, 02, ...).

## Descrição funcional

O sistema é um software de acompanhamento de tarefas simplificado, no estilo Jira: usuários se cadastram, fazem login e gerenciam suas próprias tarefas em um quadro Kanban.

### Telas

- **Login** — autenticação do usuário (email + senha).
- **Criação de usuário** — cadastro de um novo usuário.
- **Quadro Kanban** — visualização das tarefas do usuário logado, organizadas por estado.
- **Sobre** — tela institucional/informativa sobre o projeto.

### Usuário

Campos de cadastro:
- Nome
- Sobrenome
- Data de nascimento (opcional)
- Email
- Senha

Não existem papéis (roles) de usuário — todos os usuários têm o mesmo nível de acesso, apenas às suas próprias tarefas.

### Tarefas

Cada tarefa pertence a um usuário e possui:
- Nome da tarefa
- Descrição
- Data de prazo
- Estado: `esperando`, `em andamento`, `concluído`

## Vulnerabilidades propositais

Este projeto deve ser implementado **de forma deliberadamente insegura**, incluindo (mas não se limitando a):

- **Senhas em texto puro**: a tabela de usuários armazena a senha sem qualquer hash ou criptografia.
- **Sem proteção CSRF**: nenhum token ou mecanismo de proteção contra Cross-Site Request Forgery.
- **Sem proteção XSS**: nenhuma sanitização/escaping de entradas ou saídas, permitindo injeção de scripts.
- **Sem configuração de CORS**: API aberta sem restrição de origem.
- **Sem controle de autorização**: ausência de papéis e, potencialmente, de verificação adequada de propriedade dos recursos (ex.: um usuário pode conseguir acessar tarefas de outro usuário se a validação não for feita).

## Stack

- **Frontend**: Angular + TypeScript
- **Backend**: Django + Python

## Modelo de dados (alto nível)

**Usuário**
| Campo | Tipo |
|---|---|
| id | inteiro |
| nome | texto |
| sobrenome | texto |
| data_nascimento | data (opcional) |
| email | texto |
| senha | texto (sem criptografia) |

**Tarefa**
| Campo | Tipo |
|---|---|
| id | inteiro |
| usuario_id | referência ao usuário |
| nome | texto |
| descricao | texto |
| data_prazo | data |
| estado | enum (`esperando`, `em_andamento`, `concluido`) |

## Aviso

Este projeto é exclusivamente educacional. As vulnerabilidades aqui presentes são intencionais e **não devem** ser replicadas em sistemas reais/produção.
