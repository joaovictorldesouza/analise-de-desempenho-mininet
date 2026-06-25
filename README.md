# Análise Comparativa de Desempenho em Rede Local

> Trabalho prático da disciplina **Análise de Desempenho de Redes de Computadores**  
> Universidade Federal do Ceará — Campus Quixadá  
> Autor: **João Victor Lima de Souza**

---

## 📋 Descrição

Este projeto quantifica o impacto da **saturação de um link** em uma rede local (LAN) emulada, comparando duas condições experimentais:

| Cenário | Descrição |
|---------|-----------|
| **A — Tráfego Leve** | Linha de base sem carga artificial |
| **B — Alta Congestão** | Link saturado com injeção UDP de 15 Mbps |

As métricas avaliadas foram **latência (ICMP)**, **vazão TCP** e **taxa de perda e jitter UDP**, coletadas com 30 repetições independentes e apresentadas com **Intervalo de Confiança de 95%** (t de Student).

---

## 🏗️ Topologia

```
H1 (Cliente) ──[10 Mbps / fila=10]── S1 (Switch) ──[100 Mbps]── H2 (Servidor)
     10.0.0.1                                                          10.0.0.2
```

- **Gargalo artificial:** link H1–S1 limitado a 10 Mbps com fila máxima de 10 pacotes
- **Mecanismo de descarte:** Tail Drop
- **Emulador:** [Mininet](http://mininet.org/) em instância AWS (Ubuntu Linux)
- **Ferramentas de medição:** `ping` (ICMP) e `iperf3` (TCP e UDP)

---

## 📁 Estrutura do Repositório

```
.
├── experimento_30x.py      # Automação das 30 repetições independentes
├── analise_ic.py           # Análise estatística (IC 95%) e geração de gráficos
│
├── resultados/             # Saída do experimento_30x.py (gerada em execução)
│   ├── run_01/
│   │   ├── ping_cenario_A.txt
│   │   ├── ping_cenario_B.txt
│   │   ├── tcp_cenario_A.txt
│   │   ├── tcp_cenario_B.txt
│   │   ├── udp_cenario_A.txt
│   │   └── udp_cenario_B.txt
│   └── run_02/ ... run_30/
│
└── graficos/               # Saída do analise_ic.py (gerada em execução)
    ├── 01_latencia_ic.png
    ├── 02_vazao_tcp_ic.png
    ├── 03_perdas_udp_ic.png
    └── 04_jitter_udp_ic.png
```

---

## ⚙️ Requisitos

### Sistema
- Linux (testado em Ubuntu 22.04)
- Mininet instalado (`sudo apt install mininet`)
- Python 3.8+

### Dependências Python

```bash
pip install matplotlib numpy scipy
```

---

## 🚀 Como Reproduzir

### 1. Coletar os dados (30 repetições)

```bash
sudo python3 experimento_30x.py
```

Os resultados são salvos em `resultados/run_01/` até `run_30/`. Se o script for interrompido, ele **retoma de onde parou** automaticamente.

Parâmetros opcionais:

```bash
sudo python3 experimento_30x.py --runs 30 --output resultados
```

### 2. Analisar e gerar os gráficos

```bash
python3 analise_ic.py
```

Parâmetros opcionais:

```bash
python3 analise_ic.py --input resultados --output graficos --conf 0.95
```

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `--input` | Pasta com as rodadas | `resultados` |
| `--output` | Pasta para os gráficos | `graficos` |
| `--conf` | Nível de confiança (`0.90`, `0.95`, `0.99`) | `0.95` |

O script também gera `resultados_estatisticos.csv` com todas as médias, margens e intervalos.

---

## 📊 Resultados

### Latência (Ping/ICMP)

| Cenário | Média (ms) | IC 95% |
|---------|-----------|--------|
| A — Tráfego Leve | 2,42 | ± 0,01 |
| B — Alta Congestão | 12,15 | ± 0,28 |

> **+401% de aumento no RTT.** IC estreito confirma consistência nas 30 rodadas — fenômeno de **Bufferbloat**.

### Vazão TCP (Throughput)

| Cenário | Média (Mbps) | IC 95% |
|---------|-------------|--------|
| A — Tráfego Leve | 9,52 | ± 0,00 |
| B — Alta Congestão | 6,13 | ± 1,87 |

> **Queda de ~36%.** IC largo no Cenário B revela disputa instável pelo link — fenômeno de **TCP Starvation**.

### Taxa de Perda UDP

| Cenário | Média (%) | IC 95% |
|---------|----------|--------|
| A — Tráfego Leve | 0,00 | ± 0,00 |
| B — Alta Congestão | 2,63 | ± 2,58 |

> IC largo reflete a natureza estocástica do **Tail Drop** com fila de 10 pacotes.

### Jitter UDP

| Cenário | Média (ms) | IC 95% |
|---------|-----------|--------|
| A — Tráfego Leve | 0,45 | ± 0,24 |
| B — Alta Congestão | 0,27 | ± 0,21 |

> Resultado contraintuitivo: jitter maior no Cenário A. Sem carga, os pacotes disputam o agendador irregularmente. No Cenário B, a fila age como **buffer amortecedor** da variação de chegada.

---

## 🔬 Metodologia Estatística

- **Distribuição:** t de Student (adequada para n = 30)
- **Nível de confiança:** 95%
- **Cálculo:** erro padrão da média × t crítico com n−1 graus de liberdade
- **Biblioteca:** `scipy.stats.t`

```python
from scipy import stats
import numpy as np

def intervalo_confianca(valores, confianca=0.95):
    n      = len(valores)
    media  = np.mean(valores)
    ep     = stats.sem(valores)
    t      = stats.t.ppf((1 + confianca) / 2, df=n - 1)
    margem = t * ep
    return media, margem
```

