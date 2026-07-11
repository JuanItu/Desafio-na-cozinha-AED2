import sys
import os

# Descobre onde o trie2.py está, sobe um nível ('..') e pega o caminho absoluto
diretorio_pai = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Adiciona esse caminho nas rotas de busca do Python
if diretorio_pai not in sys.path:
    sys.path.append(diretorio_pai)
    
# Força a saída padrão (os prints) a usar UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Imports dos modelos/classes
from modelos.receita import *
from modelos.categoria import *
from modelos.ingredientes import *

# 1. O Nó da Trie
class TrieNode:
    __slots__ = ['children', 'objetos'] # Desativa a criação do dicionário de atributos do Python
    
    def __init__(self):
        self.children = {}
        self.objetos = None

# 2. A Estrutura da Trie
class TrieBuscaGeral:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, chave: str, objeto):
        #Insere um objeto na Trie (assumindo chaves de 'a' a 'z' minúsculas)
        current = self.root
        for char in chave:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        
        # Só instanciar a lista se ela realmente for necessária
        if current.objetos is None:
            current.objetos = []
            
        current.objetos.append(objeto)

    def get_node(self, sequencia: str) -> TrieNode:
        #Pesquisa uma sequência de caracteres e devolve o nó final correspondente.
        #Retorna None se o caminho não existir.
        
        current = self.root
        for char in sequencia:
            if char not in current.children:
                return None
            current = current.children[char]
        return current

    def get_all_separated_alphabetically(self, node: TrieNode) -> dict:
        #A partir de um nó, desce na árvore e retorna um dicionário com 3 listas 
        #(uma para cada classe), já em ordem alfabética.
        
        # Estrutura para separar os resultados
        resultados = {
            'Ingredientes': [],
            'Receita': [],
            'Categoria': []
        }
        
        if node is not None:
            self._coletar_em_ordem(node, resultados)
            
        return resultados

    def _coletar_em_ordem(self, node: TrieNode, resultados: dict):
        #Função recursiva auxiliar que varre a Trie alfabeticamente.
        
        # 1. Se tem objetos neste nó, nós os separamos
        if node.objetos is not None:
            for obj in node.objetos:
                if isinstance(obj, Ingredientes):
                    resultados['Ingredientes'].append(obj)
                elif isinstance(obj, Receita):
                    resultados['Receita'].append(obj)
                elif isinstance(obj, Categoria):
                    resultados['Categoria'].append(obj)
                    
        # 2. Ordenamos as chaves (as letras) para garantir a descida em ordem alfabética.
        # Mesmo que tenham sido inseridas fora de ordem, o sorted() garante o A-Z.
        letras_ordenadas = sorted(node.children.keys())
        
        for char in letras_ordenadas:
            filho = node.children[char]
            self._coletar_em_ordem(filho, resultados)
            
    def remove(self, chave: str, objeto) -> None:
        """Método público para remover um objeto da Trie."""
        self._remove_recursivo(self.root, chave, objeto, 0)

    def _remove_recursivo(self, node: 'TrieNode', chave: str, objeto, index: int) -> bool:
        #Desce até o objeto, remove-o, e na volta vai apagando os nós fantasmas.
        #Retorna True se o nó atual ficou inútil e pode ser deletado pelo pai.
        
        # 1. Caso Base: Chegamos no final do caminho da palavra
        if index == len(chave):
            # Se o nó tem objetos e o nosso objeto está lá dentro
            if node.objetos is not None and objeto in node.objetos:
                node.objetos.remove(objeto)
                
                # Se a lista ficou vazia, voltamos ela pra None pra economizar RAM
                if not node.objetos:
                    node.objetos = None
                    
            # A regra da poda: Posso ser deletado se não tenho objetos E não tenho filhos
            return node.objetos is None and len(node.children) == 0

        # 2. Descendo a árvore: Pega a próxima letra
        char = chave[index]
        
        # Se a palavra não existe na árvore, não faz nada
        if char not in node.children:
            return False 

        # 3. Chamada recursiva: manda descer até o final e espera a resposta na volta
        pode_deletar_filho = self._remove_recursivo(node.children[char], chave, objeto, index + 1)

        # 4. A Poda (Na volta da recursão)
        if pode_deletar_filho:
            del node.children[char] # DELETA O NÓ FANTASMA DA MEMÓRIA!
            
            # Agora que perdi um filho, será que EU também fiquei inútil?
            return node.objetos is None and len(node.children) == 0

        return False

# --- Testando a Implementação ---
#   APAGAR DEPOIS
#   APAGAR DEPOIS
#   APAGAR DEPOIS
if __name__ == "__main__":
    trie = TrieBuscaGeral()
    
    # Inserindo dados misturados e fora de ordem
    trie.insert("banana", Ingredientes("Banana-Prata", 0, []))
    trie.insert("bacaxi", Receita("Erro de ortografia", 20, 20, 20, [], ["bacaxi", "erro", "falha"]))
    trie.insert("bala", Categoria("Bala de morango", []))
    trie.insert("balao", Ingredientes("Balão azul", 0, []))
    trie.insert("barco", Receita("Barco a vela", 30, 30, 30, ["nop", "no", "no no no"], []))
    
    prefixo = "ba"
    
    # 1. Pegamos o nó exato que representa o prefixo "ba"
    no_prefixo = trie.get_node(prefixo)
    
    if no_prefixo:
        print(f"Nó encontrado para o prefixo '{prefixo}'. Coletando e separando...")
        
        # 2. A partir desse nó, coletamos tudo ordenado e separado
        dados_separados = trie.get_all_separated_alphabetically(no_prefixo)
        
        print("\nResultados Ordenados (Alfabeticamente baseados na chave):")
        print("Ingredientes:", dados_separados['Ingredientes']) # Esperado: Balao, Banana
        print("Receita:", dados_separados['Receita']) # Esperado: Bacaxi, Barco
        print("Categoria:", dados_separados['Categoria']) # Esperado: Bala
    else:
        print("Prefixo não encontrado.")