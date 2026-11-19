# SiSA — Back-end (MVP)

Sistema de Gestão de Eventos Acadêmicos — IFCE Campus Cedro.

## Tecnologias

Python 3.12, Django 5.2, Django REST Framework, PostgreSQL 16, Docker Compose, JWT, OpenAPI/Swagger, ReportLab, QR Code e Pytest.

## Requisitos

- Docker Desktop + Docker Compose
- Git e VS Code (recomendados)

## Início rápido (Windows PowerShell)

1. Copie `.env.example` para `.env` e altere **obrigatoriamente** `DJANGO_SECRET_KEY` e `POSTGRES_PASSWORD`.
2. Abra o Docker Desktop.
3. Na pasta do projeto, execute:

   ```powershell
   docker compose up --build -d
   docker compose logs -f web
   ```

4. Após a mensagem de inicialização do Gunicorn, acesse:
   - Swagger: http://localhost:8002/api/docs/
   - Schema OpenAPI: http://localhost:8002/api/schema/
5. Crie um administrador:

   ```powershell
   docker compose exec web python manage.py createsuperuser
   ```

6. Testes:

   ```powershell
   docker compose exec web pytest
   ```

7. Encerrar:

   ```powershell
   docker compose down
   ```

**Não use** `docker compose down -v` se quiser preservar os dados e arquivos.

## Observação sobre migrações

O Dockerfile gera as migrações na construção da imagem e o serviço web as aplica na inicialização. Esta é uma conveniência para o protótipo: **antes de implantação definitiva, gere e versione as migrações no repositório**, para evitar diferenças de esquema entre ambientes.

## E-mails

O `.env.example` usa backend de e-mail em console. Códigos de recuperação aparecerão em `docker compose logs web`, **não chegarão ao e-mail** até configurar SMTP. Para envio real, configure `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` e credenciais SMTP válidas.

## Certificados

O serviço `scheduler` executa `issue_certificates` aproximadamente a cada minuto. Para testar manualmente:

```powershell
docker compose exec web python manage.py issue_certificates
```

A atividade precisa estar encerrada, possuir sessões (carga horária calculável) e frequência marcada como presente. O PDF é armazenado em volume privado persistente, acessível apenas por endpoint autenticado. A URL pública de verificação depende de `PUBLIC_BASE_URL`.

## Repositórios separados

Este repositório contém apenas o back-end. O React consome `/api/v1/`. Veja [docs/INTEGRACAO_REACT.md](docs/INTEGRACAO_REACT.md).

## Limitações e segurança

- O projeto **não foi executado nem testado com Docker neste ambiente de geração**. Faça a validação local e corrija eventuais incompatibilidades antes de publicar.
- `DJANGO_DEBUG=1` é apenas para desenvolvimento; use `0`, HTTPS, hosts e origens permitidas explícitas em produção.
- O endpoint de recuperação envia código pelo provedor de e-mail configurado; proteja e monitore tentativas e envio de mensagens em produção.
- A publicação de arquivos de mídia privados deve ser controlada por proxy/armazenamento seguro em produção.
- O agendador simples é adequado ao MVP local; ambientes com múltiplas réplicas exigem coordenação de tarefas.


## Revisão baseada no Figma (v2)

Consulte `docs/ALTERACOES_V2.md` para atualizar e testar sem perder dados e
`docs/DECISOES_FIGMA.md` para as diferenças entre as telas e a API.

A aplicação continua sendo **somente backend**: as telas React não fazem parte deste ZIP.

## Permissões do administrador (revisão 3)

O administrador possui permissões acumulativas: pode atuar como participante, como organizador e executar as operações administrativas. Assim, pode se inscrever em eventos, gerenciar atividades, registrar frequência e acessar seus próprios certificados. A ação `POST /api/v1/admin/users/{id}/change-role/` permite promover um organizador a administrador ou rebaixá-lo a participante. Antes do rebaixamento, todos os eventos ativos/futuros sob responsabilidade do organizador devem ser transferidos para outro organizador ativo.
