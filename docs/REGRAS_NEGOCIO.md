# Regras de negócio implementadas no MVP

## Papéis

- Participante: inscreve-se em eventos e subeventos e acessa os próprios certificados.
- Organizador: mantém as capacidades de participante, pode organizar eventos, exceto se inscrever no próprio evento.
- Administrador: aprova organizadores, gerencia usuários/eventos, consulta inscrições e indicadores; não se inscreve e não registra frequência.
- Todo novo cadastro começa como participante. Pedido de organizador só é aceito no cadastro e exige SIAPE e e-mail institucional.
- Contas são inativadas, não apagadas.

## Eventos

- Um responsável aprovado e ativo por evento; administrador pode criar e atribuir responsável.
- Evento exige título, descrição, tipo livre, local, datas, capacidade e imagem de capa.
- Inscrições usam janela temporal do evento. Status de evento é calculado pelas datas; cancelamento é explícito.
- Evento encerrado não pode ser cancelado. Evento com histórico de inscrição não pode ser excluído.
- Subevento usa janela de inscrições do evento principal e tem capacidade independente, limitada à capacidade do evento.
- Sessões devem caber no período da atividade, sem sobreposição interna.

## Inscrições

- Uma inscrição por participante/evento, com reativação do registro existente dentro da janela de inscrições e sujeito a vagas.
- Reativação da inscrição principal não reativa automaticamente inscrições em subeventos.
- Cancelamento da inscrição principal cancela as inscrições em subeventos; cancelamento do evento também cancela inscrições ativas e registra o motivo.
- Sem lista de espera. Validações de capacidade usam transações e bloqueio do registro de evento/subevento no PostgreSQL.
- Não permite subeventos com horários sobrepostos para o mesmo participante, comparando sessões quando existentes.

## Frequência

- Presente/Ausente por atividade, sem registro por sessão.
- Só organizador responsável registra frequência, até o encerramento da atividade.
- Ausência de registro significa frequência ainda não lançada.

## Certificados

- Geração automática após término, somente com frequência presente e inscrição ativa.
- Carga horária = soma das sessões da atividade, em minutos; sem sessões, a emissão é adiada.
- PDF privado, código único e QR Code para verificação pública.
- Certificados já emitidos preservam um retrato do nome, atividade, período e carga horária.

## Administração

- Aprovação/rejeição de organizador; ativação/inativação; revogação de permissão; substituição do responsável; auditoria; painel básico.
- Auditoria guarda ações essenciais, incluindo cancelamentos e substituições de organizador.

## Observações de escopo

- A documentação técnica final deve refletir a implementação efetiva, não apenas a versão inicial do documento de requisitos.
- A configuração de SMTP real é responsabilidade do ambiente de implantação.
- O agendador simples foi escolhido para o MVP; produção exige coordenação de processos e monitoramento.

## Permissões acumulativas e gerenciamento de perfis (revisão 3)

- O perfil **administrador** acumula as funcionalidades de participante e organizador, além das operações administrativas.
- Administradores podem consultar eventos, realizar e cancelar suas próprias inscrições, selecionar subeventos, acessar seus próprios certificados, criar/editar eventos, gerenciar atividades e sessões, consultar inscrições dos eventos e registrar frequência.
- O administrador pode registrar frequência e exportar a lista de frequência de qualquer evento. Para organizadores, permanece a restrição de atuar somente nos eventos sob sua responsabilidade.
- Um administrador pode ser definido como responsável por um evento. A validação do responsável aceita organizador ou administrador ativo.
- Somente administradores podem alterar o perfil de um organizador, usando a ação `POST /api/v1/admin/users/{id}/change-role/` com `{"role":"admin"}` ou `{"role":"participant"}`.
- A promoção para administrador preserva SIAPE, e-mail institucional e vínculos históricos com eventos.
- Para rebaixar um organizador a participante, todos os eventos não cancelados e ainda não encerrados sob sua responsabilidade devem ser reatribuídos previamente a outro organizador ativo. Se ainda houver eventos, a API rejeita a alteração e informa os identificadores pendentes.
- Ao rebaixar, SIAPE e e-mail institucional são removidos do cadastro; inscrições, certificados e históricos permanecem.
- Toda mudança de perfil e reatribuição de responsável deve gerar registro de auditoria.
