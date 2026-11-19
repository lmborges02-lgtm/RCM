# Kafra Watch no RO Monitor

1. Copie `plugins/kafra_watch.pl` para a pasta compartilhada `plugins` do GordoKore.
2. No console de cada profile, execute `plugin load kafra_watch`, ou `plugin reload kafra_watch` se já estiver carregado. Para carregamento seletivo, inclua `kafra_watch` no `loadPlugins_list`.
3. No RO Monitor, abra **Kafra Watch → Escolher pasta do GordoKore** e selecione a instalação que contém `logs`. A aba lê os arquivos `kafra-watch-*.json` localmente; não precisa do coletor PowerShell nem do site.
4. Abra a janela de venda de um NPC com os itens no inventário. O plugin observa o preço-base oferecido pelo servidor sem executar vendas. Os preços ficam gravados no RO Monitor, por instalação. Use uma instalação por servidor para evitar misturar cotações.

**Loot NPC/h** divide o valor de venda das entradas cotadas pelo tempo da sessão, em horas. O valor unitário é `preço-base × 124 ÷ 100`, arredondado para baixo antes de multiplicar pela quantidade. A cotação mais recente do NPC tem prioridade; itens sem cotação continuam visíveis e o indicador de cobertura mostra quantos entraram no cálculo. Entradas de inventário podem incluir compras ou transferências. Ganhos no saldo são mostrados separadamente para evitar dupla contagem.

O catálogo embutido usa a base [rAthena Renewal](https://github.com/rathena/rathena/tree/1ca3e7700939ea40120cb51a777f8681ba5e84ae/db/re), commit `1ca3e7700939ea40120cb51a777f8681ba5e84ae`. Itens são associados pelo ID. O preço de referência usa `Sell` ou metade inteira de `Buy`, com o ajuste de preço da base, e exclui entradas sem preço documentado ou marcadas como não vendáveis. Preços de referência podem diferir do seu servidor.

A aba é local: não expõe o monitor na rede. O RCM continua usando `rcm_status.pl` para sua própria detecção do OpenKore.

## Sessões e histórico

O botão **Resetar sessão** encerra e salva a contagem do personagem selecionado, iniciando outra a partir da última amostra recebida (intervalo do plugin: aproximadamente cinco segundos). Não altera o inventário, saldo, conexão ou os preços de NPC salvos. A nova contagem desconta os itens e ganhos anteriores, sem reiniciar o plugin.

Em **Histórico de sessões**, consulte início, duração, valor do loot, zeny/h, cobertura de preços e motivo do encerramento. Os registros ficam em `kafra-sessions.sqlite3`, ao lado do aplicativo, e permanecem após fechar o programa. Não publique esse banco, pois contém nomes dos personagens e seus dados.

A média histórica é `soma dos valores de loot / soma das durações em horas`, incluindo a sessão em andamento, separada por instalação, profile e personagem. Ela não é a média simples das taxas de cada sessão. Sessões encerradas preservam a cotação usada ao encerrar; preços atualizados passam a valer na sessão em andamento. A cobertura informa quando o rendimento é parcial por itens sem cotação.

O histórico começa a ser registrado nesta atualização; não recupera sessões antigas que não foram salvas. Mudanças de sessão do plugin, desconexões e interrupções de sinal encerram o período no último registro recebido. Ao voltar com o mesmo identificador, a contagem recomeça sem incluir o intervalo sem sinal nem duplicar as coletas anteriores.

O minimapa usa a imagem original disponibilizada pelo [Divine Pride](https://www.divine-pride.net/database/map/yuno_fild09). A imagem é armazenada em `map-cache` e só é exibida se suas dimensões coincidirem com as do mapa recebido pelo GordoKore. O marcador usa a última posição disponível na telemetria local. Para mapas sem imagem compatível, as coordenadas continuam visíveis.

**Visual do personagem:** a aba mostra um sprite de corpo inteiro montado com classe, cabelo, cores e IDs de aparência de acessórios, capa, arma e escudo que o GordoKore recebe. Visuais que o jogo não exibe ou que o renderizador não conhece podem não aparecer. Após atualizar o plugin, recarregue-o nos profiles abertos. O [ragassets](https://github.com/adsonpleal/ragassets) recebe somente os parâmetros de aparência, sem nick ou conta; os PNGs ficam em cache local em `sprite-cache`.
