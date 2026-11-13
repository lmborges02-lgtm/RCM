# Plugin de status OpenKore

Copie `rcm_status.pl` para a pasta `plugins` de cada instalação do OpenKore. No GordoKore utilizado, execute:

```text
plugin load rcm_status
```

Para carregar automaticamente com `loadPlugins 2`, acrescente `rcm_status` em `loadPlugins_list` no `control/sys.txt`. Para atualizar um plugin já carregado, use `plugin reload rcm_status`.

Use uma única cópia do plugin por instalação. A linha `[RCM] Status em:` informa o arquivo a vincular no monitor: `logs/rcm-status-<profile>.json` com profile ativo, ou `logs/rcm-status.json` sem profile. Use uma instância por profile e veja o [guia de integração](../docs/OPENKORE.md) para migrar cadastros existentes.

O plugin observa o estado do OpenKore; não envia comandos ou pacotes ao jogo. Veja [OPENKORE.md](../docs/OPENKORE.md) para comportamento, tolerâncias e limites.
