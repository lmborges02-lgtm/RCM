# Configuração e uso

## Cadastro

O aplicativo começa sem clients cadastrados em uma instalação nova. **Adicionar arquivo** aceita um `.lnk` apontando diretamente para um `.exe` existente, ou o próprio `.exe`. Arquivos `.bat`, scripts e atalhos para esses arquivos não são suportados nesta versão.

Os argumentos do atalho são lidos no início de cada sessão de monitoramento. Quando dois atalhos apontam para o mesmo executável, os argumentos precisam ser diferentes para que os processos possam ser distinguidos. Se vários processos correspondem a um mesmo cadastro, a ação automática é suspensa.

Pause antes de alterar a lista. **Remover** exclui apenas o cadastro, preservando os arquivos originais. **Ativar / desativar** mantém o cadastro, mas define se ele participa das verificações.

## Campos

| Campo | Função | Padrão |
| --- | --- | --- |
| Nome | Identificação amigável na lista | Nome do arquivo |
| Caminho | Atalho ou executável a abrir | Escolhido no cadastro |
| Ativo | Participa do monitoramento | Sim ao adicionar |
| Detectar congelamento | Habilita a comparação visual | Não ao adicionar |
| Tempo sem movimento | Tolerância visual, em segundos | 120; mínimo 30 |
| Região | Esquerda, topo, largura e altura em % | `0, 0, 100, 100` |
| Status do OpenKore | Caminho do pequeno `rcm-status.json`; tem prioridade sobre a captura | Vazio |
| Intervalo entre reinícios | Espera global entre aberturas | 60 s; de 15 a 3600 |

A região deve ficar dentro da imagem, com largura e altura positivas. Por exemplo, `10, 20, 40, 50` começa a 10% da largura e a 20% da altura, cobrindo 40% da largura e 50% da altura.

A região precisa conter uma animação contínua. Uma região com chat, menus ou personagem estático pode gerar falsos positivos. Movimento causado por cursor ou outro elemento pode, ao contrário, mascarar o travamento.

## Arquivo de configuração

O programa cria `config.json` ao lado de `monitor.py`. Este arquivo é privado e não é versionado. O `config.example.json` demonstra a estrutura com dados fictícios; seu client está desativado.

```json
{
  "restart_interval": 60,
  "clients": [
    {
      "name": "Client de exemplo",
      "path": "C:\\Games\\Ragnarok\\Client01.lnk",
      "enabled": false,
      "visual": false,
      "timeout": 120,
      "roi": [0, 0, 100, 100]
    }
  ]
}
```

Prefira editar pela interface. Se editar o JSON manualmente, feche o monitor antes. JSON inválido impede a inicialização; preserve uma cópia e corrija a estrutura. Nomes, caminhos e campos precisam corresponder ao exemplo. Argumentos de login não são copiados para o JSON: permanecem no atalho cadastrado.

A configuração dos clients é salva ao editar a lista. O intervalo global é salvo ao iniciar o monitoramento. Um intervalo digitado mas não aplicado pode se perder ao fechar o programa.

## Estados e contadores

Os contadores indicam quantidade cadastrada, quantidade ativa na lista e quantidade ativa com detecção visual habilitada. **Não indicam quantos processos estão saudáveis.** A coluna de estado mostra o resultado das verificações de cada client.

- **Pausado**: verificações não iniciadas.
- **Aberto — detecção visual desativada**: processo encontrado; congelamento não é verificado.
- **Aguardando movimento**: comparação ainda não observou movimento para armar a detecção.
- **Na fila**: aguarda o intervalo global antes de tentar reiniciar.
- **Falha do Ragnarok**: janela de erro em confirmação.
- **Captura indisponível** ou **Sem acesso**: ação suspensa por falta de evidência.
- **Limite**: três tentativas no período de 15 minutos.
- **OpenKore — online**: estado de mapa informado pelo OpenKore.
- **OpenKore — offline**: aguardando conexão, tolerância ou recuperação de desconexão persistente.
- **OpenKore — desconhecido**: heartbeat ausente, inválido ou desatualizado; sem recuperação automática baseada nele.

## Pausar e retomar

Pausar interrompe novas ações quando a operação em andamento termina. Uma operação já iniciada não é desfeita. Ao retomar, o monitor relê os atalhos e recomeça os contadores de tentativas e as tolerâncias. Fechar o aplicativo interrompe o monitoramento. Não há execução permanente em segundo plano depois do fechamento.
