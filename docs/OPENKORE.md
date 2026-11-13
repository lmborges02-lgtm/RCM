# Conexão pelo OpenKore

1. Copie `plugins/rcm_status.pl` para a pasta `plugins` do OpenKore. Se vários profiles compartilham a instalação, copie **uma vez**.
2. Em cada console aberto, execute `plugin load rcm_status` ou, se já estiver carregado, `plugin reload rcm_status`. Para carregamento seletivo (`loadPlugins 2`), inclua `rcm_status` em `loadPlugins_list` no `control/sys.txt`.
3. Confira `[RCM] Status em:` no console. Com um profile ativo chamado `Conta01`, o arquivo é `logs/rcm-status-Conta01.json`. Uma instalação sem profile continua usando `logs/rcm-status.json`. Os arquivos são atualizados aproximadamente a cada dois segundos.
4. Ao migrar, pause o RCM, troque o caminho antigo em cada cadastro e retome o monitoramento. Com dois profiles diferentes ativos, confira se cada um atualiza seu próprio arquivo e se a coluna **Estado do client** mostra o estado esperado.

Use **uma instância por profile na mesma instalação**. Duas instâncias com o mesmo profile ainda escrevem no mesmo arquivo. Ao trocar de profile, o plugin passa a atualizar o novo arquivo e o anterior expira. O cadastro do RCM continua vinculado ao caminho que você configurou.

O plugin observa `Network::IN_GAME`, `Network::stateChanged` e `disconnected`. Não envia comandos ou pacotes ao jogo. Seu JSON inclui apenas versão, PID do OpenKore, sequência, horário, estado e uma indicação de recuperação; não inclui nomes de personagens, contas ou senhas. Não lê o log de console.

No monitor, pause, selecione o client e clique em **Editar selecionado**. Preencha **Status do OpenKore** com o caminho completo do arquivo indicado no console do profile correspondente. Este arquivo tem prioridade sobre a captura visual: sprites animados não cancelam uma desconexão informada pelo OpenKore. O campo **Tempo sem movimento** também define, nesta versão, o tempo de tolerância para a desconexão (padrão 120 s).

- **Online**: OpenKore informa estado de servidor de mapa. Não é uma consulta independente ao servidor oficial.
- **Offline**: OpenKore deixou de informar esse estado. A recuperação requer conexão anterior observada pelo plugin ou evento `disconnected`, mais uma falha persistente durante a tolerância.
- **Desconhecido**: arquivo ausente, inválido, grande demais ou sem atualização por mais de 15 s. Não reinicia o client por esse motivo.

A primeira desconexão já existente antes de carregar o plugin pode aparecer como **aguardando primeira conexão**, sem recuperação automática. Isso evita tratar a tela de login inicial como travamento. Depois de uma conexão ou evento confirmado, uma desconexão persistente entra na fila de reinícios. O monitor confirma novamente o status antes de encerrar e preserva o intervalo global de 60 s e o limite de tentativas.

Se o próprio OpenKore parar ou bloquear seu loop, o heartbeat expira e o monitor informa desconhecido. Esta versão não reinicia automaticamente o OpenKore. Depois de reiniciar o client, sua conexão ao mapa continua dependendo do jogo/OpenKore; abrir o executável não equivale a reconectar o personagem.

A aba Discord envia mudanças online/offline/desconhecido quando os avisos estão habilitados. Os arquivos de status são locais; não devem ser publicados como exemplos reais.
