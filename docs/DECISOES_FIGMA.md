# SiSA — Figma x API (revisão do MVP)

Referência visual: `SiSA.pdf` (37 páginas). Regras: `Documento de requisitos - SiSA (4).pdf`.

## Alterações nesta versão

| Páginas | Necessidade visual | Solução |
|---|---|---|
| 2–3 | Login com e-mail/SIAPE | Schema Swagger explicita `identifier` e `password`; resposta JWT documentada |
| 4–7 | Recuperar, verificar código, trocar senha | Nova verificação de código; redefinição existente |
| 17, 34 | Alterar e-mail e senha | Novos endpoints autenticados que exigem senha atual |
| 26 | Banner da atividade | Campo opcional `cover` em subevento |
| 31, 35 | Baixar lista de frequência | PDF de frequência do evento, restrito ao organizador |

## Pontos que exigem decisão da equipe

- **Eventos (páginas 25–26):** o backend usa capacidade, tipo e janela de inscrições, ausentes nos formulários exibidos. A equipe React precisa incluí-los ou definir uma etapa adicional; não removemos regras essenciais do backend.
- **Atividades (página 26):** capacidade precisa ser informada. Sessões detalhadas podem ser cadastradas após a criação.
- **Código de recuperação (página 5):** o Figma desenha 4 caixas, mas o backend gera **6 dígitos**. Atualizar o componente visual para seis dígitos.
- **Excluir conta (páginas 17 e 34):** não foi implementado, porque uma exclusão permanente pode apagar ou quebrar o histórico de inscrições e certificados. Definir política de retenção antes de implementar.
- **Frequência de subeventos:** exportação PDF ainda não foi incluída nesta revisão.
- **Tela de frequência (página 24) e certificados (página 29):** os layouts estão vazios; a equipe precisa concluir as interações.
- **Aprovação de organizadores (página 18):** o perfil apresenta biografia, mas o backend não exige biografia para aprovar.

## Atenção

A comparação visual não substitui testes de integração. Não foram executados testes completos com PostgreSQL/Docker neste ambiente.
