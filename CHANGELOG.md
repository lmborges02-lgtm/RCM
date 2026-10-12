# Histórico de alterações

## 0.1.0 — 2026-10-11

- Cadastro editável de atalhos e executáveis, sem número fixo de clients.
- Identificação por executável e argumentos completos.
- Recuperação de processos fechados e detecção opcional de congelamento visual.
- Captura isolada em subprocesso com timeout.
- Reconhecimento da janela Gravity Error Handler no processo identificado.
- Fila de reinícios com intervalo global configurável, padrão de 60 segundos.
- Verificação de PID e data de criação antes de encerrar um processo.
- Limite de três tentativas por client em 15 minutos.
- Interface Guardião dos clients, contadores e diário de eventos.
- Inicializador opcional como administrador.
- Configuração vazia automática na primeira execução e exemplo fictício.
- Documentação de uso, configuração, diagnóstico e arquitetura.
- Testes automatizados de configuração, atividade visual e fila de recuperação.
