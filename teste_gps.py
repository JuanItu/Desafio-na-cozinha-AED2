# teste_gps.py

import os
import time
import math
import random
import textwrap
from data.mapa_manager import carregar_malha_urbana
from motor.roteador_logistico import RoteadorLogistico
from motor.infraestrutura_minima import OtimizadorInfraestrutura  # <-- Importação do seu Kruskal!

# =====================================================================
# 1. GERADORES DE MAPA
# =====================================================================

def gerar_mapa_bairro(caminho: str):
    """Mapa 6x6 com um bloqueio no centro (36 nós)"""
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 1: BAIRRO FECHADO\n")
        for x in range(6):
            for y in range(6): f.write(f"V {float(x)} {float(y)}\n")
                
        for x in range(6):
            for y in range(6):
                # Obras no cruzamento 2,2
                if x == 2 and y == 2: continue 
                if x < 5 and not (x+1 == 2 and y == 2):
                    f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
                if y < 5 and not (x == 2 and y+1 == 2):
                    f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")

def gerar_mapa_anel(caminho: str):
    """Mapa 20x20 em formato de 'O'. O A* precisa dar a volta no lago! (~200 nós)"""
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 2: A CIDADE ANEL\n")
        validos = set()
        
        # Filtra os vértices que formam a "rosquinha" (Raio interno 4, externo 9)
        for x in range(20):
            for y in range(20):
                dist_centro = math.hypot(x - 10, y - 10)
                if 4.0 <= dist_centro <= 9.0:
                    validos.add((x, y))
                    f.write(f"V {float(x)} {float(y)}\n")
                    
        # Conecta apenas se o vizinho também fizer parte do anel
        for x, y in validos:
            if (x+1, y) in validos:
                f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
            if (x, y+1) in validos:
                f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")

def gerar_mapa_metropole(caminho: str):
    """Mapa 50x50 com ruas bloqueadas aleatoriamente e rodovia diagonal (2500 nós)"""
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write("# MAPA 3: METRÓPOLE SÃO PAULO\n")
        
        for x in range(50):
            for y in range(50): f.write(f"V {float(x)} {float(y)}\n")
                
        for x in range(50):
            for y in range(50):
                # 5% de chance de uma rua estar interditada
                if x < 49 and random.random() > 0.05:
                    f.write(f"A {float(x)} {float(y)} {float(x+1)} {float(y)} 1.0\n")
                if y < 49 and random.random() > 0.05:
                    f.write(f"A {float(x)} {float(y)} {float(x)} {float(y+1)} 1.0\n")
                
                # Rodovia Expressa Diagonal (Velocidade maior = Custo de peso 0.8)
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
        print("║   LABORATÓRIO DE GPS (A* ROUTING ENGINE)    ║")
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
        
        # Sub-Menu de Rotas e Infraestrutura
        while True:
            print("\n" + "─" * 47)
            lista_chaves = list(malha.keys())
            amostra = random.sample(lista_chaves, min(12, len(lista_chaves)))
            
            print("  [ PONTOS DISPONÍVEIS NA REGIÃO ]")
            for i, coord in enumerate(amostra, 1):
                print(f"    {i:02d}. Cruzamento {coord}")
            print("    0. Voltar ao Menu de Mapas")
            print("    99. RODAR TESTE DE INFRAESTRUTURA (LAZY KRUSKAL - MST)")
            
            try:
                entrada_usuario = input("\n  Selecione a ORIGEM (ou 99 para MST / 0 para sair): ").strip()
                if not entrada_usuario: continue
                escolha_origem = int(entrada_usuario)
                
                if escolha_origem == 0: 
                    break
                
                # ═════════════════════════════════════════════════════════════
                # EXECUÇÃO DO SEU LAZY KRUSKAL
                # ═════════════════════════════════════════════════════════════
                if escolha_origem == 99:
                    # Escolhe uma quantidade de nós proporcional ao tamanho do mapa
                    qtd_hubs = min(20, len(malha) // 2)
                    print(f"\n  [ TESTE DE ESTRESSE: LAZY KRUSKAL MST ]")
                    print(f"  Sorteando {qtd_hubs} cruzamentos para simular Cozinhas e Hubs...")
                    
                    pontos_infraestrutura = random.sample(list(malha.values()), qtd_hubs)
                    
                    t_ini_mst = time.perf_counter()
                    mst, custo_mst, astars_rodados = OtimizadorInfraestrutura.gerar_mst_logistica(pontos_infraestrutura)
                    t_fim_mst = time.perf_counter()
                    
                    # Cálculo teórico de quantas arestas um Kruskal tradicional O(V²) calcularia
                    max_arestas_possiveis = (qtd_hubs * (qtd_hubs - 1)) // 2
                    poupados = max_arestas_possiveis - astars_rodados
                    
                    print("  " + "═" * 60)
                    print(f"  🌳 MST Calculada em {(t_fim_mst - t_ini_mst)*1000:.2f} ms!")
                    print(f"  📍 Pontos Conectados: {qtd_hubs}")
                    print(f"  🛣️  Arestas Finais na Árvore: {len(mst)}")
                    print(f"  💰 Custo Total da Infraestrutura Física: {custo_mst:.2f}")
                    print("  " + "─" * 60)
                    print(f"  🧠 EFICIÊNCIA DO SEU MOTOR (Lazy Evaluation):")
                    print(f"     - Caminhos A* Executados : {astars_rodados}")
                    print(f"     - Caminhos A* Poupados   : {poupados} 🚀")
                    print("  " + "═" * 60)
                    
                    # ═════════════════════════════════════════════════════════════
                    # NOVO: EXIBIÇÃO VISUAL DA ÁRVORE GERADORA MÍNIMA
                    # ═════════════════════════════════════════════════════════════
                    print("\n  [ REPRESENTAÇÃO VISUAL DA ÁRVORE (Lista de Adjacência) ]")
                    
                    # 1. Monta o Dicionário de Adjacências
                    adj_mst = {}
                    for p1, p2, custo_aresta, rota in mst:
                        if p1 not in adj_mst: adj_mst[p1] = []
                        if p2 not in adj_mst: adj_mst[p2] = []
                        
                        # Como a MST é não-direcionada, adicionamos a via para os dois lados
                        adj_mst[p1].append((p2, custo_aresta))
                        adj_mst[p2].append((p1, custo_aresta))
                        
                    # 2. Imprime de forma elegante
                    # Ordena as chaves pelas coordenadas só para ficar bonito no terminal
                    nos_ordenados = sorted(adj_mst.keys(), key=lambda n: (n.x, n.y))
                    
                    for no in nos_ordenados:
                        vizinhos = adj_mst[no]
                        # Formata os vizinhos: (X,Y) [Custo]
                        vizinhos_str = " | ".join([f"({v.x:.0f},{v.y:.0f}) [Custo: {c:.1f}]" for v, c in vizinhos])
                        print(f"  🌳 Nó ({no.x:2.0f},{no.y:2.0f}) se conecta com ➔ {vizinhos_str}")
                    
                    print("  " + "═" * 60)
                    
                    input("\nPressione ENTER para continuar...")
                    continue
                
                # Fluxo Normal de Teste de Rota do A*
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
                        print(f"  {nome_alg} | ✗ IMPOSSÍVEL (Sem caminho)")
                    else:
                        print(f"  {nome_alg} | ⏱️ {tempo_ms:8.3f} ms | 📏 Custo: {custo:6.2f} | 📍 {len(caminho):4d} passos")
                
                print("  " + "─" * 60)
                
                # Imprime os passos da última rota gerada (w=2.0) só por curiosidade
                if caminho:
                    print("  📍 Trajeto sugerido pelo A* Rápido:")
                    rota_str = " -> ".join([f"({no.x:.0f},{no.y:.0f})" for no in caminho])
                    print(textwrap.indent(textwrap.fill(rota_str, width=80), "     "))
                
            except (ValueError, IndexError):
                print("  ⚠ Entrada inválida! Tente novamente.")
            
            input("\n  [Pressione ENTER para sortear novos pontos]")

if __name__ == "__main__":
    main()