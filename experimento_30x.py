import os
import time
import argparse
 
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.clean import cleanup
 
 
# Parâmetros do experimento 
TOTAL_RUNS   = 30          
OUTPUT_DIR   = "resultados" 
PAUSA_ENTRE_RUNS = 10      
 
 
def rodar_uma_vez(h1, h2, run_dir):
    """ Executa um ciclo completo (Cenário A + Cenário B) e salva os 6 arquivos de medição dentro de run_dir. """
 
    # CENÁRIO A: TRÁFEGO LEVE
    info(f'  [A] Medindo Latência ICMP...\n')
    h1.cmd(f'ping -c 10 10.0.0.2 > {run_dir}/ping_cenario_A.txt')
 
    info(f'  [A] Medindo Vazão TCP...\n')
    h1.cmd(f'iperf3 -c 10.0.0.2 -p 5201 -t 10 > {run_dir}/tcp_cenario_A.txt')
 
    info(f'  [A] Medindo Taxa de Perdas UDP (2 Mbps)...\n')
    h1.cmd(f'iperf3 -c 10.0.0.2 -p 5201 -u -b 2M -t 10 > {run_dir}/udp_cenario_A.txt')
 
    # CENÁRIO B: ALTA CARGA
    info(f'  [B] Injetando carga de fundo UDP 15 Mbps...\n')

    h1.cmd('iperf3 -c 10.0.0.2 -p 5202 -u -b 15M -t 45 > /dev/null 2>&1 &')
    time.sleep(5)  
 
    info(f'  [B] Medindo Latência ICMP sob congestão...\n')
    h1.cmd(f'ping -c 10 10.0.0.2 > {run_dir}/ping_cenario_B.txt')
 
    info(f'  [B] Medindo Vazão TCP sob congestão...\n')
    h1.cmd(f'iperf3 -c 10.0.0.2 -p 5201 -t 10 > {run_dir}/tcp_cenario_B.txt')
 
    info(f'  [B] Medindo Taxa de Perdas UDP sob congestão (2 Mbps)...\n')
    h1.cmd(f'iperf3 -c 10.0.0.2 -p 5201 -u -b 2M -t 10 > {run_dir}/udp_cenario_B.txt')
 
    h2.cmd('pkill -f "iperf3 -s -p 5202" ; iperf3 -s -p 5202 -D')
    time.sleep(3)
 
 
def rodar_experimentos(total_runs=TOTAL_RUNS, output_dir=OUTPUT_DIR):
    setLogLevel('info')
    os.makedirs(output_dir, exist_ok=True)
 
    # Determina de qual run retomar 
    runs_existentes = [
        d for d in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, d)) and d.startswith('run_')
    ]
    inicio = len(runs_existentes) + 1
 
    if inicio > total_runs:
        info(f'\nTodas as {total_runs} execuções já foram concluídas em "{output_dir}".\n')
        return
 
    info(f'\n{"="*60}\n')
    info(f'  INICIANDO EXPERIMENTO: {total_runs - inicio + 1} rodadas restantes\n')
    info(f'  (retomando do run {inicio})\n')
    info(f'{"="*60}\n\n')
 
    for run_num in range(inicio, total_runs + 1):
        run_label = f'run_{run_num:02d}'
        run_dir   = os.path.join(output_dir, run_label)
        os.makedirs(run_dir, exist_ok=True)
 
        info(f'\n{"─"*60}\n')
        info(f'  RODADA {run_num}/{total_runs} → {run_dir}\n')
        info(f'{"─"*60}\n')
 
        # Sobe a rede 
        cleanup()   
        net = Mininet(link=TCLink)
 
        h1 = net.addHost('h1', ip='10.0.0.1')
        h2 = net.addHost('h2', ip='10.0.0.2')
        s1 = net.addSwitch('s1', failMode='standalone')
 
        net.addLink(h1, s1, bw=10, delay='1ms', max_queue_size=10)
        net.addLink(s1, h2, bw=100)
 
        net.start()
 
        # Inicia os dois servidores iperf3
        h2.cmd('iperf3 -s -p 5201 -D')
        h2.cmd('iperf3 -s -p 5202 -D')
        time.sleep(2)
 
        try:
            rodar_uma_vez(h1, h2, run_dir)
        except Exception as e:
            info(f'\n  ERRO na rodada {run_num}: {e}\n')
        finally:
            h2.cmd('pkill iperf3')
            net.stop()
            info(f'  Rodada {run_num} concluída.\n')
 
        # Pausa entre rodadas para estabilizar o ambiente
        if run_num < total_runs:
            info(f'  Aguardando {PAUSA_ENTRE_RUNS}s antes da próxima rodada...\n')
            time.sleep(PAUSA_ENTRE_RUNS)
 
    info(f'\n{"="*60}\n')
    info(f'  EXPERIMENTO CONCLUÍDO! {total_runs} rodadas salvas em "{output_dir}/"\n')
    info(f'  Execute agora: python3 analise_ic.py\n')
    info(f'{"="*60}\n')
 
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Experimento de desempenho de rede – 30 repetições')
    parser.add_argument('--runs',   type=int, default=TOTAL_RUNS,   help='Número de repetições (padrão: 30)')
    parser.add_argument('--output', type=str, default=OUTPUT_DIR,   help='Pasta de saída (padrão: resultados)')
    args = parser.parse_args()
 
    rodar_experimentos(total_runs=args.runs, output_dir=args.output)
 
















