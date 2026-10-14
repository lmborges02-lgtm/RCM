# Solução de problemas

## OpenKore aparece como desconhecido

Confirme que o cadastro aponta para o `logs/rcm-status.json` da instalação correspondente. O arquivo deve existir e ser atualizado continuamente. Com `loadPlugins 2`, inclua `rcm_status` em `loadPlugins_list`.

No GordoKore verificado, `plugin load plugins/rcm_status.pl` não encontra o plugin porque o comando pesquisa o nome do arquivo sem diretório/extensão. Use **`plugin load rcm_status`**. A confirmação é `[RCM] Plugin carregado. Status em: ...`. Para atualizar um plugin já carregado, use `plugin reload rcm_status`.

O plugin grava o primeiro status imediatamente e exibe erros de criação, gravação ou substituição do arquivo no console. Se o arquivo parar de atualizar por mais de 15 segundos, o monitor informa desconhecido e suspende a recuperação baseada nesse sinal.

## Discord não recebe avisos

Confira o webhook na aba Discord, habilite os avisos, salve e envie um teste. Consulte o diário do monitor para HTTP, limite de envio ou falha de rede. O teste envia uma mensagem real; testes automatizados do projeto simulam a entrega. Veja [DISCORD.md](DISCORD.md).

## Sem acesso aos parâmetros

Feche o monitor e abra **Iniciar como administrador.cmd**. Use o mesmo nível de acesso dos clients. O cabeçalho informa o nível de acesso do monitor.

Se os parâmetros continuarem bloqueados, as ações permanecem suspensas. Não é seguro identificar vários clients apenas pelo nome `Ragexe.exe`. Considere também launchers, proteção do client ou políticas do Windows; esta mensagem sozinha não identifica qual deles causou o bloqueio.

## Gravity(tm) Error Handler após reinícios

Vários clients abrindo com pouca diferença de tempo podem produzir falhas no ambiente de uso. Esta versão espaça as aberturas por uma fila global, com 60 segundos por padrão. Aumente o intervalo para 90 segundos ou mais se o carregamento demorar ou se a falha reaparecer.

O monitor reconhece a janela de erro visível apenas quando ela pertence ao processo do client identificado pelos argumentos. Após 10 segundos de persistência, confirma novamente a janela e tenta reiniciar esse client, respeitando o intervalo global e o limite de tentativas.

Uma janela de erro de um processo separado não é atribuída automaticamente a um client. A recuperação não impede erros internos do jogo. Consulte o histórico para distinguir a hora de início da tentativa e a hora em que o atalho foi reaberto.

## Captura preta, antiga ou minimizada

Pause o monitor e teste a captura com o client visível. Repita após alguns segundos. `PrintWindow` depende de o programa fornecer sua imagem corretamente. Uma janela minimizada, retorno inválido ou captura preta suspende a comparação visual.

Uma imagem antiga com aparência válida é mais difícil de reconhecer: pode causar reinício indevido depois de a detecção ser armada. Se isso ocorrer, desative **Detectar congelamento** até validar outro modo gráfico ou método de captura. Esta versão não tem outro método de captura implementado.

## Reinício por imagem congelada com o jogo funcionando

Confira se a região tem movimento contínuo quando o personagem fica parado. O monitor não distingue uma cena estática legítima de um congelamento. Aumentar o tempo reduz sensibilidade, mas não corrige uma região sem atividade.

## Client fechado não abriu imediatamente

O monitor concede até 90 segundos inicialmente e também aguarda o intervalo global quando outro client acabou de ser aberto. Confira se o cadastro está ativo, se o caminho existe e se não houve erro de acesso aos processos. O limite de três tentativas em 15 minutos também pode adiar a ação.

## Mais de um processo correspondente

Há múltiplas instâncias com o mesmo executável e a mesma lista de argumentos. Use atalhos distinguíveis, ou feche a instância extra manualmente. O monitor não escolhe um processo por suposição.

## O atalho abre, mas não volta ao personagem

O programa apenas reabre o atalho. Login, escolha de servidor e personagem dependem do client e dos argumentos do atalho. Não há preenchimento automático de telas do jogo.

## Python ou tkinter não encontrado

Instale Python 3 para Windows com tkinter e disponibilize `python.exe` e `pythonw.exe` no PATH. No terminal, verifique:

```powershell
python --version
python -c "import tkinter; print('tkinter OK')"
```

## Configuração inválida

Feche o programa, faça uma cópia de `config.json` e confira a sintaxe e os campos usando `config.example.json`. Para iniciar uma configuração vazia, renomeie o arquivo local: a próxima execução cria outro. Não substitua sua configuração real pelo exemplo sem preservar uma cópia.

## Informações úteis para relatar uma falha

Informe a versão do aplicativo, a versão do Windows e Python, o estado mostrado pelo client, se a captura funciona e o intervalo configurado. Remova caminhos pessoais, identificadores de login e outros dados privados de imagens e trechos de histórico. Não envie atalhos reais, parâmetros de login nem dumps do jogo ao repositório.
