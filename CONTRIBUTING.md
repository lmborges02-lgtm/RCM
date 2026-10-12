# Como contribuir

## Ambiente

Use Python 3 com tkinter. O aplicativo é destinado ao Windows; a interface e as APIs Win32 precisam de validação nesse sistema. Não instale dependências externas para os testes de lógica.

```powershell
python -m py_compile monitor.py
python -m unittest discover -s tests -v
```

Os testes usam somente diretórios temporários e processos simulados. Não consultam seus clients, não capturam jogos, não encerram programas e não escrevem em sua configuração real.

## Alterações

Explique o problema, a alteração de comportamento e a validação realizada. Para mudanças na interface, confira estados pausado, monitorando, fila, erro, lista vazia e edição. Teste uma janela reduzida, o uso do teclado e as barras de rolagem. Para recuperação, preserve a comparação completa de argumentos, a verificação de identidade, a fila global e o limite de tentativas.

Atualize o README e os guias quando adicionar parâmetros ou alterar tempos e estados. Registre alterações relevantes no CHANGELOG. Não apresente simulações como testes do client real.

## Dados que não devem entrar em commits

- `config.json` com caminhos reais ou nomes de contas;
- atalhos `.lnk`, logs e dumps;
- credenciais, parâmetros de login ou senhas;
- capturas com dados pessoais;
- arquivos do Ragnarok ou recursos extraídos do jogo.

Use exemplos fictícios, como `C:\Games\Ragnarok\Client01.lnk`. O emblema da interface é desenhado pelo código. Não há licença de distribuição definida nesta versão; a escolha de licença pertence ao responsável pelo projeto.
