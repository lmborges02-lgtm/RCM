# Histórico de alterações

## 0.3.0 — 2026-10-14

- Plugin OpenKore gera um pequeno heartbeat JSON, sem ler o console.log nem enviar comandos ao jogo.
- Estado online/offline/desconhecido informado pelo OpenKore e avisado pelo Discord.
- Recuperação de desconexão persistente tem prioridade sobre a captura visual; sprites animados não cancelam o sinal de desconexão.
- Status antigo, inválido ou ausente não causa reinício. Reconexão cancela uma tentativa pendente.
- Testes Python de leitura e recuperação e teste Perl com módulos simulados.
- Gravação inicial imediata, confirmação de carregamento e diagnóstico de erros no console do plugin.
- Instruções corrigidas para `plugin load rcm_status` e lista seletiva `loadPlugins_list` no GordoKore utilizado.

## 0.2.0 — 2026-10-14

- Aba de configuração e teste de avisos pelo Discord.
- Envio assíncrono de mudanças do estado dos clients, sem repetições do contador de tempo.
- Webhook local separado e excluído do Git; mensagens sem menções automáticas.
- Documentação distingue processo aberto de personagem conectado. Detecção de conexão no Freya ainda depende de calibração e validação.

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
