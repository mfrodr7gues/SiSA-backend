# Revisão 3 — permissões e perfis do SiSA

## Matriz de permissões

| Funcionalidade | Participante | Organizador | Administrador |
|---|---:|---:|---:|
| Consultar eventos | Sim | Sim | Sim |
| Inscrever-se em eventos | Sim | Sim, exceto no próprio evento | Sim, inclusive no evento sob sua responsabilidade |
| Consultar os próprios certificados | Sim | Sim | Sim |
| Criar e gerenciar eventos | Não | Eventos sob sua responsabilidade | Todos os eventos |
| Gerenciar subeventos e sessões | Não | Eventos sob sua responsabilidade | Todos os eventos |
| Consultar inscrições | Próprias | Próprias e dos eventos sob sua responsabilidade | Visão administrativa global |
| Registrar frequência | Não | Eventos sob sua responsabilidade | Todos os eventos |
| Exportar lista de frequência | Não | Eventos sob sua responsabilidade | Todos os eventos |
| Gerenciar usuários e perfis | Não | Não | Sim |
| Aprovar organizadores | Não | Não | Sim |
| Consultar auditoria e indicadores | Não | Não | Sim |

## Alteração de perfil

Endpoint: `POST /api/v1/admin/users/{id}/change-role/`

Promover um organizador a administrador:

```json
{"role": "admin"}
```

Rebaixar um organizador a participante:

```json
{"role": "participant"}
```

A operação só aceita usuários que atualmente tenham perfil `organizer`. Antes de rebaixar, o administrador precisa transferir todos os eventos não cancelados e ainda não encerrados para outro organizador ativo. A API informa os IDs dos eventos que ainda precisam ser transferidos.

A promoção preserva SIAPE e e-mail institucional. O rebaixamento remove esses identificadores, mas preserva inscrições, certificados, solicitações e históricos existentes. Toda alteração gera auditoria.

## Importante para integração

A interface deve tratar o perfil administrativo como um conjunto de permissões acumuladas, não como uma área isolada. A autorização definitiva permanece no backend. Após uma mudança de perfil, o frontend deve atualizar os dados do usuário autenticado e refletir as permissões novas.
