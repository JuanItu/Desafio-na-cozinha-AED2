from modelos.categoria import Categoria
from modelos.ingredientes import Ingredientes, QuantidadeIngredientes
from datetime import datetime

class Receita:
    registro_global = {}
    registro_excluidas = {} # O nosso "Arquivo Morto"

    def __init__(self, nome_receita, custo=0.0, tempo_preparo=0, fator_recomendacao=0.0, trie_global=None, tabela_hash=None):
        nome_key = nome_receita.lower()
        
        if nome_key in Receita.registro_global:
            raise ValueError(f"A receita '{nome_receita}' já existe e não foi adicionada.")

        self.nome_receita = nome_receita
        self.custo = custo
        self.tempo_preparo = tempo_preparo
        self.fator_recomendacao = fator_recomendacao
        
        self.lista_categoria_receitas = []
        self.lista_quantidade_ingredientes = []
        
        # --- PREPARAÇÃO DO MODO INVESTIGAÇÃO ---
        self.historico_estados = []
        self.ultima_atualizacao = datetime.now()
        self.data_exclusao = None
        
        Receita.registro_global[nome_key] = self
        if trie_global is not None:
            trie_global.insert(nome_key, self)
        if tabela_hash is not None:              
            tabela_hash.inserir(nome_key, self)

    def salvar_snapshot(self, motivo="Atualização Geral"):
        """Tira uma 'foto' do estado atual da receita e guarda no histórico."""
        self.ultima_atualizacao = datetime.now()
        
        categorias = [c.nome_categoria for c in self.lista_categoria_receitas]
        ingredientes = [f"{qi.quantidade_necessaria}{qi.unidade_utilizada} {qi.ingrediente.nome_ingrediente}" 
                        for qi in self.lista_quantidade_ingredientes]
                        
        snapshot = {
            "data": self.ultima_atualizacao.strftime("%d/%m/%Y %H:%M:%S"),
            "motivo": motivo,
            "nome": self.nome_receita,
            "custo": self.custo,
            "tempo": self.tempo_preparo,
            "categorias": categorias,
            "ingredientes": ingredientes
        }
        
        self.historico_estados.append(snapshot)
        
        # Limita o histórico a 5 versões para economizar memória
        if len(self.historico_estados) > 5:
            self.historico_estados.pop(0)

    def atualizar_fator_recomendacao(self, novo_fator) -> bool:
        self.fator_recomendacao = novo_fator
        return True 

    def excluir(self, trie_global=None, tabela_hash=None) -> bool:
        # Limpa as categorias
        for cat in self.lista_categoria_receitas:
            cat.remover_receita(self)
            
        # Limpa os ingredientes
        for relacao in self.lista_quantidade_ingredientes:
            relacao.ingrediente.remover_receita(self)
            
        nome_key = self.nome_receita.lower()
        
        # Atualiza os motores de busca
        if trie_global is not None: trie_global.remove(nome_key, self)
        if tabela_hash is not None: tabela_hash.remover(nome_key, self)
            
        # Remove do Banco de Dados Principal e vai para a Lixeira
        if nome_key in Receita.registro_global:
            del Receita.registro_global[nome_key]
            
        self.data_exclusao = datetime.now()
        self.salvar_snapshot("Exclusão da Receita")
        Receita.registro_excluidas[nome_key] = self 
        return True

    def adicionar_categoria(self, nome_categoria, trie_global=None, tabela_hash=None) -> bool:
        cat = Categoria.get_ou_criar(nome_categoria, trie_global, tabela_hash)
        if cat not in self.lista_categoria_receitas:
            self.lista_categoria_receitas.append(cat)
            cat.adicionar_receita(self)
            return True 
        return False

    def adicionar_ingrediente(self, nome_ingrediente, unidade, quantidade, trie_global=None, tabela_hash=None) -> bool:
        ingrediente_obj = Ingredientes.get_ou_criar(nome_ingrediente, trie_global, tabela_hash)
        relacao = QuantidadeIngredientes(ingrediente_obj, unidade, quantidade)
        
        self.lista_quantidade_ingredientes.append(relacao)
        ingrediente_obj.adicionar_receita(self)
        return True

    def atualizar_custo(self, novo_custo) -> bool:
        self.custo = novo_custo
        return True
    
    def atualizar_tempo(self, novo_tempo) -> bool:
        self.tempo_preparo = novo_tempo
        return True

    def mudar_nome(self, novo_nome, trie_global=None, tabela_hash=None):
        nome_antigo_key = self.nome_receita.lower()
        novo_nome_key = novo_nome.lower()
        
        if novo_nome_key in Receita.registro_global:
            raise ValueError(f"A receita '{novo_nome}' já existe!")
            
        if trie_global: trie_global.remove(nome_antigo_key, self)
        if tabela_hash: tabela_hash.remover(nome_antigo_key, self)
            
        del Receita.registro_global[nome_antigo_key]
        self.nome_receita = novo_nome
        Receita.registro_global[novo_nome_key] = self
        
        if trie_global: trie_global.insert(novo_nome_key, self)
        if tabela_hash: tabela_hash.inserir(novo_nome_key, self)

    def __str__(self): return self.nome_receita
    def __repr__(self): return f"<Receita: {self.nome_receita}>"