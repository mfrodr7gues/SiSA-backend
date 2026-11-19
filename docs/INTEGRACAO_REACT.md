# Integração React ↔ SiSA API

Base URL local: `http://localhost:8000/api/v1/`.

## Autenticação

`POST /auth/register/` — `{ "full_name": "...", "email": "...", "password": "...", "request_organizer": false }`.

`POST /auth/login/` — `{ "identifier": "email ou SIAPE", "password": "..." }`.

Resposta contém `access`, `refresh` e `user`. Nas rotas privadas, enviar `Authorization: Bearer <access>`.

`POST /auth/refresh/` — `{ "refresh": "..." }`; `POST /auth/logout/` — `{ "refresh": "..." }` com Bearer válido.

**Segurança no React:** não exponha tokens em logs, URLs ou commits; defina estratégia segura de armazenamento e renovação com a equipe. JWT é apenas o mecanismo de autenticação, não dispensa HTTPS em produção.

## Endpoints principais

- `GET /events/?search=...&type=...&status=registration_open` — listagem paginada.
- `POST /events/` — cria evento, autenticado como organizador ou admin. `multipart/form-data` para `cover`.
- `GET /subevents/?event=<uuid>` — subeventos do evento.
- `GET /event-sessions/` e `GET /subevent-sessions/` — sessões (veja Swagger).
- `POST /registrations/enroll/` — `{ "event": "<uuid>" }`.
- `GET /registrations/me/` — inscrições acessíveis.
- `POST /registrations/<uuid>/subevents/` — `{ "subevent": "<uuid>" }`.
- `POST /registrations/<uuid>/cancel/` e `/reactivate/`.
- `POST /subevent-registrations/<uuid>/cancel/`.
- `POST /event-attendance/` — `{ "registration": "<uuid>", "present": true }` (organizador).
- `POST /subevent-attendance/` — `{ "subevent_registration": "<uuid>", "present": true }`.
- `GET /certificates/me/` e `GET /certificates/<uuid>/download/`.
- `GET /certificates/verify/<code>/` — público.
- `GET /admin/dashboard/` — somente administrador.

## Erros

HTTP 400 = dados inválidos / regra de negócio; 401 = não autenticado; 403 = acesso proibido; 404 = inexistente; 429 = limite de requisições. Formato usual: `{ "detail": "..." }` ou campos com lista de mensagens.

## Documentação interativa

Swagger: `http://localhost:8000/api/docs/`.
OpenAPI: `http://localhost:8000/api/schema/`.

## Arquivos

Em desenvolvimento, URLs de mídia são servidas apenas com `DJANGO_DEBUG=1`. Em produção, use proxy ou serviço dedicado de mídia, com regras de acesso apropriadas para PDFs privados.
