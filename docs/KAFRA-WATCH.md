# Kafra Watch no RO Monitor

1. Copie `plugins/kafra_watch.pl` para a pasta compartilhada `plugins` do GordoKore.
2. No console de cada profile, execute `plugin load kafra_watch`, ou `plugin reload kafra_watch` se já estiver carregado. Para carregamento seletivo, inclua `kafra_watch` no `loadPlugins_list`.
3. No RO Monitor, abra **Kafra Watch → Escolher pasta do GordoKore** e selecione a instalação que contém `logs`. A aba lê os arquivos `kafra-watch-*.json` localmente; não precisa do coletor PowerShell nem do site.
4. Abra a janela de venda de um NPC com os itens no inventário. O plugin observa o preço-base oferecido pelo servidor sem executar vendas. Os preços ficam gravados no RO Monitor, por instalação. Use uma instalação por servidor para evitar misturar cotações.

**Loot NPC/h** divide o valor de venda das entradas cotadas pelo tempo da sessão, em horas. O valor unitário é `preço-base × 124 ÷ 100`, arredondado para baixo antes de multiplicar pela quantidade. A cotação mais recente do NPC tem prioridade; itens sem cotação continuam visíveis e o indicador de cobertura mostra quantos entraram no cálculo. Entradas de inventário podem incluir compras ou transferências. Ganhos no saldo são mostrados separadamente para evitar dupla contagem.

O catálogo embutido usa a base [rAthena Renewal](https://github.com/rathena/rathena/tree/1ca3e7700939ea40120cb51a777f8681ba5e84ae/db/re), commit `1ca3e7700939ea40120cb51a777f8681ba5e84ae`. Itens são associados pelo ID. O preço de referência usa `Sell` ou metade inteira de `Buy`, com o ajuste de preço da base, e exclui entradas sem preço documentado ou marcadas como não vendáveis. Preços de referência podem diferir do seu servidor.

A aba é local: não expõe o monitor na rede. O RCM continua usando `rcm_status.pl` para sua própria detecção do OpenKore.

O minimapa usa a imagem original disponibilizada pelo [Divine Pride](https://www.divine-pride.net/database/map/yuno_fild09). A imagem é armazenada em `map-cache` e só é exibida se suas dimensões coincidirem com as do mapa recebido pelo GordoKore. O marcador usa a última posição disponível na telemetria local. Para mapas sem imagem compatível, as coordenadas continuam visíveis.

**Visual do personagem:** a aba mostra um sprite de corpo inteiro montado com classe, cabelo, cores e IDs de aparência de acessórios, capa, arma e escudo que o GordoKore recebe. Visuais que o jogo não exibe ou que o renderizador não conhece podem não aparecer. Após atualizar o plugin, recarregue-o nos profiles abertos. O [ragassets](https://github.com/adsonpleal/ragassets) recebe somente os parâmetros de aparência, sem nick ou conta; os PNGs ficam em cache local em `sprite-cache`.
