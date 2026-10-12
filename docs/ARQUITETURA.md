# Funcionamento e limites

## Componentes

| Componente | Responsabilidade |
| --- | --- |
| `monitor.py` / `App` | Interface tkinter, cadastro, estado e diário de eventos |
| Thread do monitor | Verificação periódica, propostas de recuperação e fila global |
| Windows PowerShell | Resolução dos atalhos e consulta CIM dos processos |
| `crash_processes` | Enumeração de janelas visíveis e identificação dos títulos de erro |
| Subprocesso `--capture` | Captura da janela via Win32/GDI e amostragem da região |
| `Activity` | Registro de movimento observado e tempo sem mudanças |
| `terminate_checked` | Verificação de identidade e encerramento do processo correspondente |
| `iniciar-admin.ps1` | Inicialização opcional com elevação para essa execução |

O aplicativo usa somente a biblioteca padrão do Python em tempo de execução. Pillow foi utilizado para preparar a imagem de documentação, mas não é necessário para executar o monitor nem os testes publicados.

## Verificação e identificação

Um cadastro corresponde ao caminho do executável e à lista completa de argumentos, analisada pelo `CommandLineToArgvW`. A comparação não usa substrings de porta ou nome de conta. É possível acompanhar clients que já estavam abertos antes de iniciar o monitor, desde que seus argumentos correspondam ao cadastro.

Falha na consulta de processos suspende ações naquele ciclo. Processos com nome correspondente mas caminho ou argumentos inacessíveis também impedem uma decisão de abertura. Dois cadastros indistinguíveis são rejeitados; múltiplos processos correspondentes suspendem a ação desse cadastro.

## Detecção visual

A captura procura a maior janela visível do PID. A imagem é obtida com `PrintWindow`, recortada por porcentagens e amostrada em RGB de 320 × 180 pixels. A captura roda num processo separado, com timeout de cinco segundos, para evitar bloquear a thread de monitoramento em uma chamada ao client travado.

Uma observação é considerada mudança quando mais de 0,1% dos canais RGB variam acima de oito níveis em relação à observação anterior. A detecção só é armada depois de observar mudança. Captura inválida, preta, minimizada ou indisponível reinicia essa validação.

Isso é uma heurística: movimento pequeno pode não ser detectado, uma cena legitimamente estática pode parecer travada e algum elemento ainda animado pode mascarar um travamento parcial. Captura desatualizada fornecida pelo jogo continua sendo uma limitação.

## Recuperação e fila

O ciclo coleta propostas de reinício e as revalida antes de executar. O intervalo global permite somente uma abertura por vez, com uma espera fixa depois de abrir o atalho. Cadastros sem tentativas recentes recebem prioridade; entre empates vale a ordem da lista. Pendências não são persistidas em disco: são recalculadas nas próximas verificações.

Antes de encerrar, o monitor atualiza a consulta de processos e verifica novamente PID, data de criação e parâmetros. O handle de término também precisa corresponder à data de criação esperada. Isso evita encerrar um processo cujo PID foi reutilizado. Não encerra a árvore inteira de processos nem clica no botão Exit da mensagem.

As tentativas são contadas antes do encerramento/abertura; falhas nesses passos também consomem o limite. O limite é de três tentativas por client numa janela de 15 minutos. Pausar e retomar ou reabrir o monitor reinicia os contadores.

## Tempos

| Parâmetro | Valor |
| --- | --- |
| Pausa entre ciclos | 5 s, além da duração das operações |
| Timeout de consulta PowerShell | 20 s |
| Timeout de captura | 5 s por client |
| Tolerância inicial e de carregamento | 90 s |
| Confirmação de janela de erro | 10 s |
| Congelamento visual | 120 s por padrão; mínimo 30 s |
| Intervalo global entre aberturas | 60 s por padrão; de 15 a 3600 s |
| Limite de tentativas | 3 por client em 15 min |

Capturas e consultas são sequenciais. Com muitos clients ou operações demoradas, o ciclo completo demora mais de cinco segundos. O intervalo global não bloqueia as verificações com um `sleep` de 60 segundos: o monitor consulta o relógio nos ciclos seguintes.

## Limites de validação

Os testes automatizados simulam processos, relógio, captura e abertura. Não substituem a validação da captura e do reinício com o client real. O uso local relatou funcionamento da consulta quando o monitor foi executado como administrador. O ambiente de desenvolvimento bloqueou CIM; os testes não encerram nem abrem jogos reais.
