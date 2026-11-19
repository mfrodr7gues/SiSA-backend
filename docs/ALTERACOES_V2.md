# Entrega v2 — alterações e testes

## O que mudou

- Organização dos módulos Python: funções e classes com indentação consistente, espaçamento e docstrings explicativas.
- Documentação OpenAPI do login e da recuperação de senha.
- `POST /api/v1/auth/password-recovery/verify/` — recebe `email` e `code`.
- `POST /api/v1/users/me/change-password/` — recebe `current_password` e `new_password`.
- `POST /api/v1/users/me/change-email/` — recebe `current_password` e `new_email`.
- `GET /api/v1/attendance-sheets/{event_id}/` — baixa PDF da frequência, apenas para organizador responsável.
- `cover` opcional em subeventos (requer migração).
- Administração deixa de listar inscrições individuais em `GET /registrations/`.
- `.dockerignore` exclui segredos e arquivos locais do build.

## Como atualizar sem apagar dados

1. **Faça backup do banco antes de substituir qualquer arquivo:**
   `docker compose exec -T db pg_dump -U sisa -d sisa > backup-sisa.sql`
2. Copie o novo código para **uma pasta separada** (por exemplo `C:\Projeto\SiSA-backend-v2`).
3. Copie seu `.env` atual para essa nova pasta. Não compartilhe o `.env`.
4. Execute `docker compose config` para conferir variáveis.
5. Para testar em paralelo sem conflitar com portas/volumes, altere a porta publicada no `compose.yaml` e use um nome de projeto Compose distinto (`docker compose -p sisa_v2 up --build -d`). **Não reutilize o banco antigo sem backup.**
6. Acesse `/api/docs/` na porta configurada e teste os fluxos abaixo.

**Migrações:** a versão ainda utiliza `makemigrations` no build, como o protótipo original. Antes de implantação definitiva, gere e versione as migrações em um ambiente Django completo.

## Checklist de testes manuais

1. Cadastro de participante e organizador.
2. Login por e-mail e SIAPE; refresh e logout.
3. Recuperação: solicitar código, verificar, redefinir senha e fazer login.
4. Alterar senha com senha atual incorreta/correta.
5. Alterar e-mail duplicado/novo; login com e-mail novo.
6. Aprovar/rejeitar solicitação de organizador.
7. Criar evento, subevento com banner e sessões; testar períodos/capacidade.
8. Inscrever, cancelar e reativar; testar conflito de horários.
9. Marcar presença; baixar PDF de frequência como organizador e testar acesso negado como participante.
10. Emitir certificado após encerramento e verificar QR Code.
11. Consultar painel e auditoria como administrador.

## Limitações desta revisão

Não foi possível executar Django, pytest nem Docker no ambiente de edição porque as dependências não estavam disponíveis para instalação. Foi realizada validação sintática dos módulos Python; os testes de execução devem ser feitos no seu Docker.

## Revisão 3 — permissões acumulativas do administrador

- O administrador passa a poder executar as ações de participante e organizador, além das funções administrativas.
- Administradores podem realizar inscrições inclusive em eventos sob sua própria responsabilidade.
- Administradores podem gerenciar frequência e exportar a lista de frequência de eventos; organizadores continuam limitados aos próprios eventos.
- Administradores podem ser responsáveis por eventos.
- Foi adicionada a ação `POST /api/v1/admin/users/{id}/change-role/`, aceitando `role=admin` ou `role=participant` para usuários atualmente organizadores.
- O rebaixamento para participante exige reatribuição prévia de todos os eventos ativos/futuros. O histórico é preservado e os identificadores institucionais são removidos do perfil rebaixado.
- Foram adicionados testes automatizados para promoção/rebaixamento e inscrição/frequência por administrador. A execução completa ainda precisa ocorrer no ambiente Docker com as dependências do projeto.
