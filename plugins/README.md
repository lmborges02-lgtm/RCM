# Plugin de status OpenKore

Copie `rcm_status.pl` para a pasta `plugins` de cada instalação do OpenKore. No GordoKore utilizado, execute:

```text
plugin load rcm_status
```

Para carregar automaticamente com `loadPlugins 2`, acrescente `rcm_status` em `loadPlugins_list` no `control/sys.txt`. Para atualizar um plugin já carregado, use `plugin reload rcm_status`.

A confirmação começa com `[RCM] Plugin carregado. Status em:`. O plugin grava `logs/rcm-status.json` imediatamente e o atualiza periodicamente. Associe esse caminho ao client no monitor.

O plugin observa o estado do OpenKore; não envia comandos ou pacotes ao jogo. Veja [OPENKORE.md](../docs/OPENKORE.md) para comportamento, tolerâncias e limites.
