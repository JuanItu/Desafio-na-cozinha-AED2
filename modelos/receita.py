from modelos.categoria import Categoria
from modelos.ingredientes import Ingredientes, QuantidadeIngredientes

class Receita:
    registro_global = {}

    def __init__(self, nome_receita, custo=0.0, tempo_preparo=0, fator_recomendacao=0.0, trie_global=None):
        nome_key = nome_receita.lower()
        
        # 1. REGRA DE CRIAÇÃO: Verifica se já existe antes de fazer qualquer coisa
        if nome_key in Receita.registro_global:
            # Ao lançar este erro, a criação é abortada. 
            # O `main` captura isso, sabe que falhou e NÃO altera a flag do algoritmo.
            raise ValueError(f"A receita '{nome_receita}' já existe e não foi adicionada.")

        self.nome_receita = nome_receita
        self.custo = custo
        self.tempo_preparo = tempo_preparo
        self.fator_recomendacao = fator_recomendacao
        
        self.lista_categoria_receitas = []
        self.lista_quantidade_ingredientes = []
        
        # 2. LISTA DE HASHES/VERSÕES: Nasce com uma string básica ou pode usar a serialização depois
        self.historico_versoes_hash = ["versao_inicial"]
        
        # 3. REGISTRO E TRIE: Como passou pela verificação, adicionamos com sucesso!
        Receita.registro_global[nome_key] = self
        if trie_global is not None:
            trie_global.insert(nome_key, self)

    # --- MÉTODOS DE SINALIZAÇÃO PARA O ALGORITMO ---

    def atualizar_fator_recomendacao(self, novo_fator) -> bool:
        """
        Altera o fator e retorna True para sinalizar ao 'main' 
        que o algoritmo de recomendação ficou desatualizado.
        """
        self.fator_recomendacao = novo_fator
        return True 

    def excluir(self, trie_global=None) -> bool:
        """
        Limpa as relações bidirecionais, remove da Trie, do Registro Geral 
        e retorna True para avisar o 'main' que a exclusão foi um sucesso e o algoritmo desatualizou.
        """
        # Limpa as categorias
        for cat in self.lista_categoria_receitas:
            cat.remover_receita(self)
            
        # Limpa os ingredientes
        for relacao in self.lista_quantidade_ingredientes:
            relacao.ingrediente.remover_receita(self)
            
        nome_key = self.nome_receita.lower()
        
        # Atualiza a Trie (Motor de Busca)
        if trie_global is not None: 
            trie_global.remove(nome_key, self)
            
        # Remove do Banco de Dados
        if nome_key in Receita.registro_global:
            del Receita.registro_global[nome_key]
            
        # Sinaliza sucesso para o main
        return True

    # --- MÉTODOS DE RELACIONAMENTO ---

    def adicionar_categoria(self, nome_categoria) -> bool:
        cat = Categoria.get_ou_criar(nome_categoria)
        if cat not in self.lista_categoria_receitas:
            self.lista_categoria_receitas.append(cat)
            cat.adicionar_receita(self)
            return True # Mudou o perfil, o main pode querer saber
        return False

    def adicionar_ingrediente(self, nome_ingrediente, unidade, quantidade) -> bool:
        ingrediente_obj = Ingredientes.get_ou_criar(nome_ingrediente)
        relacao = QuantidadeIngredientes(ingrediente_obj, unidade, quantidade)
        
        self.lista_quantidade_ingredientes.append(relacao)
        ingrediente_obj.adicionar_receita(self)
        
        # Aqui você poderia atualizar o self.historico_versoes_hash com a nova composição se desejar
        
        return True # A composição mudou, avisa o main

    # --- OUTROS MÉTODOS ---

    def atualizar_custo_ou_tempo(self, novo_custo, novo_tempo) -> bool:
        self.custo = novo_custo
        self.tempo_preparo = novo_tempo
        return True

    def mudar_nome(self, novo_nome, trie_global=None):
        nome_antigo_key = self.nome_receita.lower()
        novo_nome_key = novo_nome.lower()
        
        if novo_nome_key in Receita.registro_global:
            raise ValueError(f"A receita '{novo_nome}' já existe!")
            
        # Poda a Trie antiga
        if trie_global: 
            trie_global.remove(nome_antigo_key, self)
            
        # Atualiza o registro
        del Receita.registro_global[nome_antigo_key]
        self.nome_receita = novo_nome
        Receita.registro_global[novo_nome_key] = self
        
        # Insere na Trie nova
        if trie_global: 
            trie_global.insert(novo_nome_key, self)

    def __str__(self): return self.nome_receita
    def __repr__(self): return f"<Receita: {self.nome_receita}>"