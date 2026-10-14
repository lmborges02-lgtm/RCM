# Testes automatizados

Na raiz do projeto, execute:

```powershell
python -m unittest discover -s tests -v
```

Os 20 testes verificam configuração, atividade visual, títulos de erro, fila de reinícios, avisos Discord e status/recuperação via OpenKore. Consultas, capturas, processos, aberturas e entregas Discord são simulados: nenhum client real é encerrado ou aberto, e nenhuma mensagem real é enviada pelos testes.

Veja [CONTRIBUTING.md](../CONTRIBUTING.md) para orientação de desenvolvimento.
