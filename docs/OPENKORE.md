# Conexão pelo OpenKore

Copie `plugins/rcm_status.pl` deste pacote para a pasta `plugins` de cada OpenKore. No console do OpenKore, carregue com `plugin load rcm_status`, ou reinicie o OpenKore. Ele grava `logs/rcm-status.json` nessa instalação, aproximadamente a cada dois segundos e em mudanças de estado.

Se `control/sys.txt` usa `loadPlugins 2`, o carregamento automático é seletivo: acrescente `rcm_status` à lista `loadPlugins_list`, separado por vírgula. Apenas copiar o arquivo não basta nesse modo. Para as sessões já abertas, o comando `plugin load rcm_status` carrega o plugin imediatamente. Se retornar erro, confira a mensagem no console. Após alguns segundos, `logs/rcm-status.json` deve existir e seu horário de atualização deve avançar.

O plugin observa `Network::IN_GAME`, `Network::stateChanged` e `disconnected`. Não envia comandos ou pacotes ao jogo. Seu JSON inclui apenas versão, PID do OpenKore, sequência, horário, estado e uma indicação de recuperação; não inclui nomes de personagens, contas ou senhas. Não lê o log de console.

No monitor, pause, selecione o client e clique em **Editar selecionado**. Preencha **Status do OpenKore** com o caminho daquele `logs/rcm-status.json`. Este arquivo tem prioridade sobre a captura visual: sprites animados não cancelam uma desconexão informada pelo OpenKore. O campo **Tempo sem movimento** também define, nesta versão, o tempo de tolerância para a desconexão (padrão 120 s).

- **Online**: OpenKore informa estado de servidor de mapa. Não é uma consulta independente ao servidor oficial.
- **Offline**: OpenKore deixou de informar esse estado. A recuperação requer conexão anterior observada pelo plugin ou evento `disconnected`, mais uma falha persistente durante a tolerância.
- **Desconhecido**: arquivo ausente, inválido, grande demais ou sem atualização por mais de 15 s. Não reinicia o client por esse motivo.

A primeira desconexão já existente antes de carregar o plugin pode aparecer como **aguardando primeira conexão**, sem recuperação automática. Isso evita tratar a tela de login inicial como travamento. Depois de uma conexão ou evento confirmado, uma desconexão persistente entra na fila de reinícios. O monitor confirma novamente o status antes de encerrar e preserva o intervalo global de 60 s e o limite de tentativas.

Se o próprio OpenKore parar ou bloquear seu loop, o heartbeat expira e o monitor informa desconhecido. Esta versão não reinicia automaticamente o OpenKore. Depois de reiniciar o client, sua conexão ao mapa continua dependendo do jogo/OpenKore; abrir o executável não equivale a reconectar o personagem.

A aba Discord envia mudanças online/offline/desconhecido quando os avisos estão habilitados. Os arquivos de status são locais; não devem ser publicados como exemplos reais.
