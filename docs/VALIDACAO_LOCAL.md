# Roteiro de validação local (Windows + Docker Desktop)

1. `Copy-Item .env.example .env` no PowerShell; edite as duas senhas/chaves de exemplo.
2. `docker compose up --build -d`
3. `docker compose ps` (os serviços `web`, `db`, `scheduler` devem estar ativos).
4. `docker compose logs web --tail=100` (verifique migrações e inicialização do Gunicorn).
5. Abra `http://localhost:8000/api/docs/`.
6. `docker compose exec web python manage.py createsuperuser`
7. `docker compose exec web pytest -v`
8. No Swagger, crie um participante e um pedido de organizador; entre como admin para aprovar.
9. Entre como organizador (SIAPE), crie evento com capa, sessões e subeventos.
10. Entre como participante (e-mail), faça inscrição, teste vaga, subevento e cancelamento.
11. Marque presença antes do encerramento. Para testar emissão, use atividade encerrada e frequência previamente marcada.
12. `docker compose exec web python manage.py issue_certificates`; confira `GET /certificates/me/` e download.
13. Confirme a verificação pública do QR Code.
14. Teste o React na porta 5173 com CORS habilitado.

## Diagnóstico

- `docker compose logs -f web` — erros Django.
- `docker compose logs -f scheduler` — emissão de certificados.
- `docker compose down` — interrompe, preservando volumes.
- Nunca publique o `.env` ou credenciais reais.

**Nota:** Os testes automatizados e a execução do Docker precisam ser realizados na máquina do usuário; não foi possível executá-los no ambiente de geração por ausência de Django instalado e acesso a pacotes de rede.
