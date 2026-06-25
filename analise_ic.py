import os
import re
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
 
 
# Configuração
INPUT_DIR   = "resultados"
OUTPUT_DIR  = "graficos"
CONF_LEVEL  = 0.95 
 
# Paleta de cores 
COR_A  = "#27AE60"   # verde
COR_B  = "#E74C3C"   # vermelho
COR_IC = "#1E2761"   # navy
 

 
def parse_ping(filepath):
    """Extrai RTT médio (ms) de um arquivo de saída do ping."""
    try:
        with open(filepath) as f:
            conteudo = f.read()
        # Linha: rtt min/avg/max/mdev = 2.148/2.421/4.639/0.739 ms
        m = re.search(r'rtt min/avg/max/mdev\s*=\s*[\d.]+/([\d.]+)/', conteudo)
        return float(m.group(1)) if m else None
    except Exception:
        return None
 
 
def parse_tcp(filepath):
    """Extrai throughput do receiver (Mbits/sec) de saída do iperf3 TCP."""
    try:
        with open(filepath) as f:
            conteudo = f.read()
        # Última linha de summary do receiver
        # Ex: [  5]   0.00-10.23  sec  11.6 MBytes  9.53 Mbits/sec   receiver
        matches = re.findall(
            r'\[\s*\d+\]\s+[\d.]+-[\d.]+\s+sec\s+[\d.]+\s+\S+\s+([\d.]+)\s+Mbits/sec\s+receiver',
            conteudo
        )
        return float(matches[-1]) if matches else None
    except Exception:
        return None
 
 
def parse_udp(filepath):
    """
    Extrai do arquivo iperf3 UDP:
      - taxa de perda (%) do receiver
      - jitter (ms) do receiver
      - throughput do receiver (Mbits/sec)
    Retorna (perda, jitter, throughput) ou (None, None, None).
    """
    try:
        with open(filepath) as f:
            conteudo = f.read()
 
        # Linha receiver UDP:
        # [  5]   0.00-10.00  sec  2.38 MBytes  2.00 Mbits/sec  0.011 ms  0/1727 (0%)  receiver
        m = re.search(
            r'\[\s*\d+\]\s+[\d.]+-[\d.]+\s+sec\s+[\d.]+\s+\S+\s+'
            r'([\d.]+)\s+Mbits/sec\s+'
            r'([\d.]+)\s+ms\s+'           # jitter
            r'\d+/\d+\s+\(([\d.]+)%\)'   # lost/total (%)
            r'\s+receiver',
            conteudo
        )
        if m:
            throughput = float(m.group(1))
            jitter     = float(m.group(2))
            perda      = float(m.group(3))
            return perda, jitter, throughput
        return None, None, None
    except Exception:
        return None, None, None
 
 
# Coleta de dados 
 
def coletar_dados(input_dir):
    """ Percorre todas as pastas run_XX dentro de input_dir e retorna um dicionário com listas de valores para cada métrica. """
    dados = {
        "ping_A":      [],
        "ping_B":      [],
        "tcp_A":       [],
        "tcp_B":       [],
        "udp_perda_A": [],
        "udp_perda_B": [],
        "udp_jitter_A":[],
        "udp_jitter_B":[],
    }
 
    runs = sorted([
        d for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and d.startswith("run_")
    ])
 
    print(f"\nLendo {len(runs)} rodadas de '{input_dir}/'...\n")
 
    erros = []
    for run in runs:
        run_path = os.path.join(input_dir, run)
 
        v = parse_ping(os.path.join(run_path, "ping_cenario_A.txt"))
        if v is not None: dados["ping_A"].append(v)
        else: erros.append(f"{run}/ping_cenario_A.txt")
 
        v = parse_ping(os.path.join(run_path, "ping_cenario_B.txt"))
        if v is not None: dados["ping_B"].append(v)
        else: erros.append(f"{run}/ping_cenario_B.txt")
 
        v = parse_tcp(os.path.join(run_path, "tcp_cenario_A.txt"))
        if v is not None: dados["tcp_A"].append(v)
        else: erros.append(f"{run}/tcp_cenario_A.txt")
 
        v = parse_tcp(os.path.join(run_path, "tcp_cenario_B.txt"))
        if v is not None: dados["tcp_B"].append(v)
        else: erros.append(f"{run}/tcp_cenario_B.txt")
 
        perda, jitter, _ = parse_udp(os.path.join(run_path, "udp_cenario_A.txt"))
        if perda is not None:
            dados["udp_perda_A"].append(perda)
            dados["udp_jitter_A"].append(jitter)
        else:
            erros.append(f"{run}/udp_cenario_A.txt")
 
        perda, jitter, _ = parse_udp(os.path.join(run_path, "udp_cenario_B.txt"))
        if perda is not None:
            dados["udp_perda_B"].append(perda)
            dados["udp_jitter_B"].append(jitter)
        else:
            erros.append(f"{run}/udp_cenario_B.txt")
 
    if erros:
        print(f"  ⚠  Arquivos não encontrados ou inválidos ({len(erros)}):")
        for e in erros:
            print(f"     • {e}")
 
    return dados
 
 
# Estatísticas 
 
def ic(valores, confianca=CONF_LEVEL):
    """
    Calcula média e margem do Intervalo de Confiança usando
    distribuição t de Student (adequado para n < 30 e para n = 30).
 
    Retorna (média, margem) ou (None, None) se n < 2.
    """
    n = len(valores)
    if n < 2:
        return (valores[0] if n == 1 else None), None
 
    arr   = np.array(valores, dtype=float)
    media = arr.mean()
    ep    = stats.sem(arr) 
    t     = stats.t.ppf((1 + confianca) / 2, df=n - 1)
    margem = t * ep
    return media, margem
 
 
def resumo_estatistico(dados, confianca):
    """Imprime tabela de resumo e retorna lista de dicionários para CSV."""
    linhas = []
    metricas = [
        ("Latência – Cenário A (ms)",       dados["ping_A"]),
        ("Latência – Cenário B (ms)",       dados["ping_B"]),
        ("Vazão TCP – Cenário A (Mbps)",    dados["tcp_A"]),
        ("Vazão TCP – Cenário B (Mbps)",    dados["tcp_B"]),
        ("Perda UDP – Cenário A (%)",       dados["udp_perda_A"]),
        ("Perda UDP – Cenário B (%)",       dados["udp_perda_B"]),
        ("Jitter UDP – Cenário A (ms)",     dados["udp_jitter_A"]),
        ("Jitter UDP – Cenário B (ms)",     dados["udp_jitter_B"]),
    ]
 
    print(f"\n{'─'*72}")
    print(f"  Resumo Estatístico  (IC {int(confianca*100)}%  –  t de Student)")
    print(f"{'─'*72}")
    print(f"  {'Métrica':<40} {'N':>4} {'Média':>9} {'±Margem':>9}  Intervalo")
    print(f"{'─'*72}")
 
    for nome, vals in metricas:
        n = len(vals)
        if n == 0:
            print(f"  {nome:<40} {'—':>4}   sem dados")
            continue
        media, margem = ic(vals, confianca)
        if margem is not None:
            print(f"  {nome:<40} {n:>4} {media:>9.4f} {margem:>9.4f}  [{media-margem:.4f}, {media+margem:.4f}]")
        else:
            print(f"  {nome:<40} {n:>4} {media:>9.4f}  (n=1, sem IC)")
        linhas.append({
            "Métrica": nome,
            "N": n,
            "Média": round(media, 6) if media is not None else "",
            "Margem IC": round(margem, 6) if margem is not None else "",
            "IC Inferior": round(media - margem, 6) if margem else "",
            "IC Superior": round(media + margem, 6) if margem else "",
        })
 
    print(f"{'─'*72}\n")
    return linhas
 
 
# Gráficos 
 
FONTE_TITULO  = {'fontsize': 15, 'fontweight': 'bold', 'color': '#1E2761'}
FONTE_EIXO    = {'fontsize': 11, 'color': '#334155'}
FONTE_VALOR   = {'fontsize': 11, 'fontweight': 'bold'}
 
def _salvar(fig, nome, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    caminho = os.path.join(output_dir, nome)
    fig.savefig(caminho, dpi=180, bbox_inches='tight')
    plt.close(fig)
    print(f"  ✔  {caminho}")
 
 
def _barras_ic(ax, medias, margens, rotulos, cores, ylabel, titulo, confianca):
    """ Desenha gráfico de barras com barras de erro (IC) padronizado. """
    x = np.arange(len(rotulos))
    barras = ax.bar(
        x, medias,
        color=cores,
        width=0.45,
        zorder=3,
        edgecolor='white',
        linewidth=0.8,
    )
 
    for xi, (med, marg) in enumerate(zip(medias, margens)):
        if marg is not None and med is not None:
            ax.errorbar(
                xi, med, yerr=marg,
                fmt='none',
                ecolor=COR_IC,
                elinewidth=2.5,
                capsize=8,
                capthick=2.5,
                zorder=4,
            )

            ax.text(
                xi, med + marg + max(medias) * 0.03,
                f'{med:.2f} ± {marg:.2f}',
                ha='center', va='bottom',
                **FONTE_VALOR, color='#1E2761',
            )
 
    ax.set_xticks(x)
    ax.set_xticklabels(rotulos, **FONTE_EIXO)
    ax.set_ylabel(ylabel, **FONTE_EIXO)
    ax.set_title(titulo, **FONTE_TITULO, pad=14)
 
    ax.set_ylim(0, max(m for m in medias if m) * 1.35)
    ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#CBD5E1', zorder=0)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
 

    ic_patch = mpatches.Patch(color=COR_IC, label=f'Barra de erro: IC {int(confianca*100)}% (t de Student)')
    ax.legend(handles=[ic_patch], fontsize=9, loc='upper right',
              framealpha=0.7, edgecolor='#CBD5E1')
 
 
def grafico_latencia(dados, confianca, output_dir):
    med_A, marg_A = ic(dados["ping_A"], confianca)
    med_B, marg_B = ic(dados["ping_B"], confianca)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    _barras_ic(
        ax,
        medias   = [med_A, med_B],
        margens  = [marg_A, marg_B],
        rotulos  = ["Cenário A\n(Tráfego Leve)", "Cenário B\n(Alta Congestão)"],
        cores    = [COR_A, COR_B],
        ylabel   = "RTT Médio (ms)",
        titulo   = f"Impacto da Congestão na Latência (Ping/ICMP)\n"
                   f"IC {int(confianca*100)}%  –  n = {len(dados['ping_A'])} rodadas",
        confianca = confianca,
    )
    fig.tight_layout()
    _salvar(fig, "01_latencia_ic.png", output_dir)
 
 
def grafico_vazao_tcp(dados, confianca, output_dir):
    med_A, marg_A = ic(dados["tcp_A"], confianca)
    med_B, marg_B = ic(dados["tcp_B"], confianca)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    _barras_ic(
        ax,
        medias   = [med_A, med_B],
        margens  = [marg_A, marg_B],
        rotulos  = ["Cenário A\n(Tráfego Leve)", "Cenário B\n(Alta Congestão)"],
        cores    = [COR_A, COR_B],
        ylabel   = "Largura de Banda (Mbps)",
        titulo   = f"Impacto da Congestão na Vazão TCP (Throughput)\n"
                   f"IC {int(confianca*100)}%  –  n = {len(dados['tcp_A'])} rodadas",
        confianca = confianca,
    )
    fig.tight_layout()
    _salvar(fig, "02_vazao_tcp_ic.png", output_dir)
 
 
def grafico_perdas_udp(dados, confianca, output_dir):
    med_A, marg_A = ic(dados["udp_perda_A"], confianca)
    med_B, marg_B = ic(dados["udp_perda_B"], confianca)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    _barras_ic(
        ax,
        medias   = [med_A if med_A else 0.001, med_B],  # evita ylim=0
        margens  = [marg_A, marg_B],
        rotulos  = ["Cenário A\n(Tráfego Leve)", "Cenário B\n(Alta Congestão)"],
        cores    = [COR_A, COR_B],
        ylabel   = "Pacotes Perdidos (%)",
        titulo   = f"Impacto da Congestão na Taxa de Perdas (UDP)\n"
                   f"IC {int(confianca*100)}%  –  n = {len(dados['udp_perda_A'])} rodadas",
        confianca = confianca,
    )
    fig.tight_layout()
    _salvar(fig, "03_perdas_udp_ic.png", output_dir)
 
 
def grafico_jitter_udp(dados, confianca, output_dir):
    if not dados["udp_jitter_A"] or not dados["udp_jitter_B"]:
        print("  ⚠  Dados de jitter insuficientes, gráfico ignorado.")
        return
 
    med_A, marg_A = ic(dados["udp_jitter_A"], confianca)
    med_B, marg_B = ic(dados["udp_jitter_B"], confianca)
 
    fig, ax = plt.subplots(figsize=(8, 5))
    _barras_ic(
        ax,
        medias   = [med_A, med_B],
        margens  = [marg_A, marg_B],
        rotulos  = ["Cenário A\n(Tráfego Leve)", "Cenário B\n(Alta Congestão)"],
        cores    = [COR_A, COR_B],
        ylabel   = "Jitter (ms)",
        titulo   = f"Impacto da Congestão no Jitter UDP\n"
                   f"IC {int(confianca*100)}%  –  n = {len(dados['udp_jitter_A'])} rodadas",
        confianca = confianca,
    )
    fig.tight_layout()
    _salvar(fig, "04_jitter_udp_ic.png", output_dir)
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main():
    parser = argparse.ArgumentParser(description='Análise estatística – IC dos experimentos de rede')
    parser.add_argument('--input',  default=INPUT_DIR,  help='Pasta com as rodadas (padrão: resultados)')
    parser.add_argument('--output', default=OUTPUT_DIR,  help='Pasta para salvar os gráficos (padrão: graficos)')
    parser.add_argument('--conf',   type=float, default=CONF_LEVEL,
                        help='Nível de confiança: 0.90, 0.95 ou 0.99 (padrão: 0.95)')
    args = parser.parse_args()
 
    if not os.path.isdir(args.input):
        print(f"\n  ERRO: pasta '{args.input}' não encontrada.")
        print(f"  Execute primeiro: sudo python3 experimento_30x.py\n")
        return
 
    dados = coletar_dados(args.input)
 
    # Verifica se tem dados suficientes
    n_min = min(len(v) for v in dados.values() if v)
    n_max = max(len(v) for v in dados.values() if v)
    print(f"  Rodadas válidas: mínimo = {n_min}, máximo = {n_max}")
    if n_min < 2:
        print("  ERRO: são necessárias pelo menos 2 rodadas válidas para calcular o IC.")
        return
 
    # Resumo estatístico no terminal e CSV
    linhas = resumo_estatistico(dados, args.conf)
 
    csv_path = "resultados_estatisticos.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        campos = ["Métrica", "N", "Média", "Margem IC", "IC Inferior", "IC Superior"]
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    print(f"  ✔  {csv_path}\n")
 
    # Gráficos
    print("Gerando gráficos...\n")
    grafico_latencia(dados, args.conf, args.output)
    grafico_vazao_tcp(dados, args.conf, args.output)
    grafico_perdas_udp(dados, args.conf, args.output)
    grafico_jitter_udp(dados, args.conf, args.output)
 
    print(f"\n  Concluído! Gráficos salvos em '{args.output}/'")
    print(f"  Atualize os slides com os novos arquivos de '{args.output}/'.\n")
 
 
if __name__ == '__main__':
    main()
 
















