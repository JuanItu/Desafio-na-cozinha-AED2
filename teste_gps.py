# teste_gps.py

import os
import time
import math
import random
import textwrap
from data.mapa_manager import carregar_malha_urbana
from motor.roteador_logistico import RoteadorLogistico
from motor.infraestrutura_minima import OtimizadorInfraestrutura
from modelos.logistica import CozinhaRegisto, PontoRetiradaRegisto 
from motor.fluxo_capacidade import MotorFluxoMCMF
from motor.roteador_entregas import RoteadorEntregasTSP

# =====================================================================
# 1. GERADORES DE MAPA (Mantidos idênticos)
# =====================================================================

def gerar_mapa_bairro(caminho: str):
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 1: BAIRRO FECHADO\n")
        for x in range(6):
            for y in range(6): f.write(f"V {float(x)} {float(y)}\n")
        for x in range(6):
            for y in range(6):
                if x == 2 and y == 2: continue 
                if x < 5 and not (x+1 == 2 and y == 2):
                    f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
                if y < 5 and not (x == 2 and y+1 == 2):
                    f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")

def gerar_mapa_anel(caminho: str):
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 2: A CIDADE ANEL\n")
        validos = set()
        for x in range(20):
            for y in range(20):
                dist_centro = math.hypot(x - 10, y - 10)
                if 4.0 <= dist_centro <= 9.0:
                    validos.add((x, y))
                    f.write(f"V {float(x)} {float(y)}\n")
        for x, y in validos:
            if (x+1, y) in validos:
                f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
            if (x, y+1) in validos:
                f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")

def gerar_mapa_metropole(caminho: str):
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 3: METRÓPOLE SÃO PAULO\n")
        for x in range(50):
            for y in range(50): f.write(f"V {float(x)} {float(y)}\n")
        for x in range(50):
            for y in range(50):
                if x < 49 and random.random() > 0.05:
                    f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
                if y < 49 and random.random() > 0.05:
                    f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")
                if x == y and x < 49:
                    f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y+1)} 0.8\n")


# =====================================================================
# 2. INTERFACE DE TESTE
# =====================================================================

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    pasta_data = "data"
    if not os.path.exists(pasta_data): os.makedirs(pasta_data)
    caminho_mapa = os.path.join(pasta_data, "mapa_teste.txt")

    while True:
        limpar_tela()
        print("╔═════════════════════════════════════════════╗")
        print("║   LABORATÓRIO LOGÍSTICO (GPS, MST E FLUXO)  ║")
        print("╚═════════════════════════════════════════════╝")
        print("  1. Carregar Bairro Fechado (Pequeno, Obstáculo central)")
        print("  2. Carregar Cidade Anel (Média, Lago no centro)")
        print("  3. Carregar Metrópole SP (Gigante, 2.500 nós, Aleatória)")
        print("  0. Sair")
        
        opcao = input("\n  Escolha o cenário para gerar: ").strip()
        
        if opcao == "0": break
        elif opcao == "1": gerar_mapa_bairro(caminho_mapa)
        elif opcao == "2": gerar_mapa_anel(caminho_mapa)
        elif opcao == "3": gerar_mapa_metropole(caminho_mapa)
        else: continue
            
        print(f"\n  [ PROCESSANDO MAPA... ]")
        t0 = time.perf_counter()
        malha = carregar_malha_urbana(caminho_mapa)
        t1 = time.perf_counter()
        
        print(f"  ✓ Mapa carregado em {(t1-t0)*1000:.2f} ms!")
        print(f"  ✓ Total de Cruzamentos (Nós): {len(malha)}")
        
        # Variáveis globais da sessão de teste para guardar os estados!
        cache_rotas_global = {}
        mst_salva = []
        
        # Sub-Menu de Rotas e Infraestrutura
        while True:
            print("\n" + "─" * 47)
            lista_chaves = list(malha.keys())
            amostra = random.sample(lista_chaves, min(12, len(lista_chaves)))
            
            print("  [ PONTOS DISPONÍVEIS NA REGIÃO ]")
            for i, coord in enumerate(amostra, 1):
                print(f"    {i:02d}. Cruzamento {coord}")
            print("    0. Voltar ao Menu de Mapas")
            print("   77. RODAR TESTE DE ROTA DE ENTREGAS (TSP)")
            print("   88. RODAR TESTE DE CAPACIDADE (FLUXO MÁXIMO MCMF)")
            print("   99. RODAR TESTE DE INFRAESTRUTURA (LAZY KRUSKAL MST)")
            
            try:
                entrada_usuario = input("\n  Selecione a ORIGEM (77, 88, 99 ou 0 para sair): ").strip()
                if not entrada_usuario: continue
                escolha_origem = int(entrada_usuario)
                
                if escolha_origem == 0: 
                    break
                
                # ═════════════════════════════════════════════════════════════
                # TESTE 88: FLUXO MÁXIMO DE CUSTO MÍNIMO (MCMF)
                # ═════════════════════════════════════════════════════════════
                if escolha_origem == 88:
                    qtd_cozinhas = min(4, len(malha) // 4)
                    qtd_hubs = min(10, len(malha) // 2)
                    
                    print(f"\n  [ TESTE DE ESTRESSE: FLUXO MÁXIMO ]")
                    print(f"  🏢 Sorteando {qtd_cozinhas} Cozinhas e {qtd_hubs} Hubs Logísticos...")
                    
                    amostra_fluxo = random.sample(list(malha.values()), qtd_cozinhas + qtd_hubs)
                    
                    # 1. Instancia as Cozinhas com capacidades aleatórias (Pratos/Hora)
                    cozinhas = []
                    for no in amostra_fluxo[:qtd_cozinhas]:
                        cap_coz = random.randint(30, 80)
                        cozinhas.append(CozinhaRegisto(no, cap_coz))
                        
                    # 2. Instancia os Hubs com capacidades aleatórias (Entregadores)
                    hubs = []
                    for no in amostra_fluxo[qtd_cozinhas:]:
                        cap_hub = random.randint(10, 25)
                        hubs.append(PontoRetiradaRegisto(no, cap_hub))
                        
                    t_ini_fluxo = time.perf_counter()
                    
                    # 3. Dispara o Motor (Passando o Cache!)
                    motor_fluxo = MotorFluxoMCMF(cache_rotas=cache_rotas_global)
                    
                    print("  ⚙️ Construindo Grafo Virtual de Fluxo (Vertex Splitting)...")
                    motor_fluxo.construir_grafo_virtual(cozinhas, hubs)
                    
                    print("  🚀 Empurrando pedidos pela rede (Bellman-Ford Preguiçoso)...")
                    fluxo_total, custo_total = motor_fluxo.calcular_fluxo_maximo_custo_minimo()
                    
                    t_fim_fluxo = time.perf_counter()
                    
                    # --- Relatório Final ---
                    cap_coz_max = sum(c.capacidade_pratos_hora for c in cozinhas)
                    cap_hub_max = sum(h.capacidade_entregadores for h in hubs)
                    
                    print("  " + "═" * 60)
                    print(f"  📊 RESULTADOS DO DELIVERY ({(t_fim_fluxo - t_ini_fluxo)*1000:.2f} ms)")
                    print(f"  🍳 Teto de Produção   : {cap_coz_max} pratos/hora")
                    print(f"  🛵 Teto Logístico     : {cap_hub_max} entregadores")
                    print("  " + "─" * 60)
                    print(f"  ✅ PEDIDOS ENTREGUES  : {fluxo_total} pratos (Fluxo Máximo)")
                    print(f"  💸 CUSTO OPERACIONAL  : {custo_total:.2f} ¢$ (Custo Mínimo)")
                    
                    # Análise de Gargalo
                    if fluxo_total == cap_coz_max:
                        print("  ⚠️ GARGALO DA REDE: A produção das Cozinhas esgotou!")
                    elif fluxo_total == cap_hub_max:
                        print("  ⚠️ GARGALO DA REDE: Faltaram entregadores nos Hubs!")
                    else:
                        print("  ⚠️ GARGALO DA REDE: Limitações viárias isolaram alguns Hubs.")
                    
                    print("  " + "═" * 60)
                    print(f"  🧠 Status do Cache de Rotas: {len(cache_rotas_global)} conexões memorizadas")
                    print("  " + "═" * 60)
                    
                    input("\nPressione ENTER para continuar...")
                    continue

                # ═════════════════════════════════════════════════════════════
                # TESTE 77: ROTEAMENTO MULTI-ENTREGAS (MÓDULO 8 - TSP HÍBRIDO)
                # ═════════════════════════════════════════════════════════════
                if escolha_origem == 77:
                    qtd_entregas = 12
                    print(f"\n  [ TESTE DE INFRAESTRUTURA: CIRCUITO DE ENTREGAS TSP ]")
                    print(f"  Sorteando 1 Ponto de Despacho e {qtd_entregas} Clientes isolados...")
                    
                    amostra_tsp = random.sample(list(malha.values()), qtd_entregas + 1)
                    ponto_despacho = amostra_tsp[0]
                    clientes_entrega = amostra_tsp[1:]
                    
                    t_ini_tsp = time.perf_counter()
                    
                    # Dispara o nosso Roteador do Caixeiro Viajante Híbrido!
                    circuito, custo_tsp, astars_tsp = RoteadorEntregasTSP.resolver_tsp_hibrido(
                        ponto_despacho, clientes_entrega, cache_rotas_global
                    )
                    
                    t_fim_tsp = time.perf_counter()
                    
                    print("  " + "═" * 60)
                    print(f"  🏁 CIRCUITO CALCULADO EM {(t_fim_tsp - t_ini_tsp)*1000:.2f} ms")
                    print(f"  📍 Origem do Despacho : {ponto_despacho.coordenadas}")
                    print("  " + "─" * 60)
                    
                    # ANÁLISE INTELIGENTE DE CONECTIVIDADE
                    if custo_tsp == float('inf'):
                        print("  ❌ ROTA IMPOSSÍVEL: O Ponto de Despacho ou uma via principal está completamente isolada!")
                        print("     Nenhum entregador consegue completar o circuito fechado.")
                    else:
                        # O circuito tem a origem no início e no fim, por isso subtraímos 2 para saber os clientes reais
                        qtd_visitados = len(circuito) - 2
                        clientes_visitados = set(circuito) - {ponto_despacho}
                        clientes_isolados = set(clientes_entrega) - clientes_visitados
                        
                        print(f"  📦 Clientes Visitados : {qtd_visitados} de {qtd_entregas}")
                        if clientes_isolados:
                            print(f"  ⚠️ Clientes Isolados  : {len(clientes_isolados)} (Ignorados por falta de acesso viário)")
                            
                        print(f"  💰 Custo Real da Rota : {custo_tsp:.2f} (Distância Viária)")
                        print("  " + "─" * 60)
                        print(f"  🧠 EFICIÊNCIA DO LAZY INSERTION:")
                        print(f"     - Caminhos A* Reais Executados: {astars_tsp}")
                        print(f"     - Status Atual do Cache Global: {len(cache_rotas_global)} rotas")
                        print("  " + "═" * 60)
                        print("  🗺️  Ordem Sequencial do Itinerário de Entrega:")
                        
                        itinerario_str = " ➔ ".join([f"({no.x:.0f},{no.y:.0f})" for no in circuito])
                        print(textwrap.indent(textwrap.fill(itinerario_str, width=80), "     "))
                    
                    print("  " + "═" * 60)
                    
                    input("\nPressione ENTER para continuar...")
                    continue

                # ═════════════════════════════════════════════════════════════
                # TESTE 99: LAZY KRUSKAL COM CACHE E EXIBIÇÃO VISUAL
                # ═════════════════════════════════════════════════════════════
                if escolha_origem == 99:
                    qtd_hubs = min(20, len(malha) // 2)
                    print(f"\n  [ TESTE DE ESTRESSE: LAZY KRUSKAL MST ]")
                    print(f"  Sorteando {qtd_hubs} cruzamentos para simular Cozinhas e Hubs...")
                    
                    pontos_infraestrutura = random.sample(list(malha.values()), qtd_hubs)
                    
                    t_ini_mst = time.perf_counter()
                    mst_salva, custo_mst, astars_rodados = OtimizadorInfraestrutura.gerar_mst_logistica(
                        pontos_infraestrutura, cache_rotas_global
                    )
                    t_fim_mst = time.perf_counter()
                    
                    max_arestas_possiveis = (qtd_hubs * (qtd_hubs - 1)) // 2
                    poupados = max_arestas_possiveis - astars_rodados
                    
                    print("  " + "═" * 60)
                    print(f"  🌳 MST Calculada em {(t_fim_mst - t_ini_mst)*1000:.2f} ms!")
                    print(f"  📍 Pontos Conectados: {qtd_hubs}")
                    print(f"  💰 Custo da Infraestrutura: {custo_mst:.2f}")
                    print(f"  🧠 Inteligência: {astars_rodados} A* Executados | {poupados} Poupados")
                    
                    # Exibição Visual da MST
                    print("\n  [ REPRESENTAÇÃO VISUAL DA ÁRVORE (Lista de Adjacência) ]")
                    adj_mst = {}
                    for p1, p2, custo_aresta, rota in mst_salva:
                        if p1 not in adj_mst: adj_mst[p1] = []
                        if p2 not in adj_mst: adj_mst[p2] = []
                        adj_mst[p1].append((p2, custo_aresta))
                        adj_mst[p2].append((p1, custo_aresta))
                        
                    nos_ordenados = sorted(adj_mst.keys(), key=lambda n: (n.x, n.y))
                    for no in nos_ordenados:
                        vizinhos = adj_mst[no]
                        vizinhos_str = " | ".join([f"({v.x:.0f},{v.y:.0f}) [{c:.1f}]" for v, c in vizinhos])
                        print(f"  🌳 Nó ({no.x:2.0f},{no.y:2.0f}) liga com ➔ {vizinhos_str}")
                    print("  " + "═" * 60)
                    
                    input("\nPressione ENTER para continuar...")
                    continue
                
                # Fluxo Normal de Teste de Rota do A* (Mantido idêntico)
                escolha_destino = int(input("  Selecione o NÚMERO do cruzamento de DESTINO: "))
                if escolha_destino == 0: break
                
                origem = malha[amostra[escolha_origem - 1]]
                destino = malha[amostra[escolha_destino - 1]]
                
                pesos_teste = [0.0, 1.0, 1.5, 2.0]
                
                print(f"\n  [ COMPARATIVO DE ROTAS: {origem.coordenadas} -> {destino.coordenadas} ]")
                print("  " + "─" * 60)
                
                for peso in pesos_teste:
                    t_ini = time.perf_counter()
                    caminho, custo = RoteadorLogistico.buscar_rota_a_estrela(origem, destino, peso_heuristica=peso)
                    t_fim = time.perf_counter()
                    
                    if peso == 0.0: nome_alg = "Dijkstra (Cego) "
                    elif peso == 1.0: nome_alg = "A* Perfeito     "
                    else: nome_alg = f"A* Rápido (w={peso})"
                    
                    tempo_ms = (t_fim - t_ini) * 1000
                    
                    if not caminho:
                        print(f"  {nome_alg} | ✗ IMPOSSÍVEL")
                    else:
                        print(f"  {nome_alg} | ⏱️ {tempo_ms:8.3f} ms | 📏 Custo: {custo:6.2f} | 📍 {len(caminho):4d} passos")
                
                print("  " + "─" * 60)
                
            except (ValueError, IndexError):
                print("  ⚠ Entrada inválida! Tente novamente.")
            
            input("\n  [Pressione ENTER para sortear novos pontos]")

if __name__ == "__main__":
    main()