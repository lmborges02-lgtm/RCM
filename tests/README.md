# Testes automatizados

Na raiz do projeto, execute:

```powershell
python -m unittest discover -s tests -v
```

Os 11 testes verificam criação e preservação da configuração, atividade visual, títulos de erro e reinícios em sequência. As consultas, capturas, processos e aberturas são simulados: nenhum client real é encerrado ou aberto.

Veja [CONTRIBUTING.md](../CONTRIBUTING.md) para orientação de desenvolvimento.
