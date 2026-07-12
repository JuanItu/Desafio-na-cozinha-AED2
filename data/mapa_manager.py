# data/mapa_manager.py

import os
from modelos.logistica import NoLogistico

def carregar_malha_urbana(caminho_arquivo: str) -> dict[tuple[float, float], NoLogistico]:
    """
    Lê o arquivo .txt e constrói o dicionário (Hash Map) de Spatial Hashing.
    Retorna: dict[(x, y) -> NoLogistico]
    """
    malha_urbana: dict[tuple[float, float], NoLogistico] = {}
    
    if not os.path.exists(caminho_arquivo):
        print(f"  ⚠ Arquivo de mapa não encontrado: {caminho_arquivo}")
        return malha_urbana
        
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            # Ignora linhas vazias ou comentários
            if not linha or linha.startswith('#'):
                continue
            
            partes = linha.split()
            tipo = partes[0].upper()
            
            if tipo == 'V':
                # Formato: V X Y
                x, y = float(partes[1]), float(partes[2])
                malha_urbana[(x, y)] = NoLogistico(x, y)
                
            elif tipo == 'A':
                # Formato: A X1 Y1 X2 Y2 Peso
                x1, y1 = float(partes[1]), float(partes[2])
                x2, y2 = float(partes[3]), float(partes[4])
                peso = float(partes[5])
                
                origem = malha_urbana.get((x1, y1))
                destino = malha_urbana.get((x2, y2))
                
                if origem and destino:
                    # Adiciona a rua nos dois sentidos (Bi-direcional)
                    origem.adicionar_via(destino, peso)
                    destino.adicionar_via(origem, peso)

    return malha_urbana