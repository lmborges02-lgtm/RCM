# Avisos no Discord

Na aba **Discord**, informe um webhook de um canal de texto do seu servidor Discord, marque **Habilitar avisos automáticos** e salve. **Enviar teste ao canal** envia uma mensagem real ao canal configurado e registra sucesso ou falha no diário do monitor.

Crie o webhook nas integrações do canal/servidor, com uma conta que tenha permissão de gerenciar webhooks. Use a URL completa fornecida pelo Discord, no formato `https://discord.com/api/webhooks/ID/TOKEN`. Não é preciso criar um bot para receber esses avisos. Referência: [documentação oficial de webhooks](https://docs.discord.com/developers/resources/webhook#execute-webhook).

`discord.json` guarda essa URL somente na pasta da instalação e está excluído do Git. Ela permite postar no canal: não a publique em issues nem a compartilhe junto com a configuração. Não há URL real incluída no aplicativo distribuído.

O monitor envia o nome cadastrado e uma descrição do estado, sem argumentos do executável, caminhos, capturas ou dados de login. Menções automáticas estão desativadas. Os avisos cobrem client fechado, processo encontrado, janela de erro, reabertura, falha no reinício, bloqueio de acesso e limite de tentativas. Mudanças no contador de segundos não geram mensagens repetidas.

O envio ocorre numa thread separada: falhas de rede não bloqueiam o monitor. Há timeout de 10 segundos por envio. Falhas não são reenviadas automaticamente, evitando duplicações; o diário informa o problema. Em limite de envio (HTTP 429), o aviso é descartado e o envio espera o prazo informado. Ao desabilitar os avisos, mensagens ainda não enviadas são descartadas; uma requisição já em andamento pode terminar.

## Personagem online/offline no Freya

Quando um arquivo de status do plugin está associado ao client, os avisos indicam online/offline/desconhecido **conforme informado pelo OpenKore**. Isso não é uma consulta independente ao servidor oficial. Veja [a integração OpenKore](OPENKORE.md). Sem esse arquivo configurado, um processo aberto ou reaberto não prova conexão do personagem e os avisos deixam isso explícito. Nenhuma senha de conta é necessária para a integração Discord.
