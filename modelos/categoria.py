class Categoria:
    registro_global = {}

    def __init__(self, nome_categoria, trie_global=None, tabela_hash=None):
        self.nome_categoria = nome_categoria
        self.lista_categoria_receitas = [] 
        
        Categoria.registro_global[nome_categoria.lower()] = self
        if trie_global: trie_global.insert(nome_categoria.lower(), self)
        if tabela_hash: tabela_hash.inserir(nome_categoria.lower(), self)

    @classmethod
    def get_ou_criar(cls, nome_categoria, trie_global=None, tabela_hash=None):
        nome_key = nome_categoria.lower()
        if nome_key not in cls.registro_global:
            return cls(nome_categoria, trie_global, tabela_hash)
        return cls.registro_global[nome_key]

    def adicionar_receita(self, receita):
        if receita not in self.lista_categoria_receitas:
            self.lista_categoria_receitas.append(receita)

    def remover_receita(self, receita):
        if receita in self.lista_categoria_receitas:
            self.lista_categoria_receitas.remove(receita)
            
    def excluir(self, trie_global=None, tabela_hash=None):
        for rec in list(self.lista_categoria_receitas):
            rec.lista_categoria_receitas.remove(self)
            rec.salvar_snapshot(f"Categoria '{self.nome_categoria}' foi apagada do sistema")
            
        nome_key = self.nome_categoria.lower()
        if trie_global: trie_global.remove(nome_key, self)
        if tabela_hash: tabela_hash.remover(nome_key, self)
        if nome_key in Categoria.registro_global:
            del Categoria.registro_global[nome_key]

    def mudar_nome(self, novo_nome, trie_global=None, tabela_hash=None):
        nome_antigo_key = self.nome_categoria.lower()
        novo_nome_key = novo_nome.lower()
        if novo_nome_key in Categoria.registro_global: raise ValueError(f"A categoria '{novo_nome}' já existe!")
            
        if trie_global: trie_global.remove(nome_antigo_key, self) 
        if tabela_hash: tabela_hash.remover(nome_antigo_key, self)
            
        del Categoria.registro_global[nome_antigo_key]
        self.nome_categoria = novo_nome
        Categoria.registro_global[novo_nome_key] = self
        
        if trie_global: trie_global.insert(novo_nome_key, self) 
        if tabela_hash: tabela_hash.inserir(novo_nome_key, self)

    def __str__(self): return self.nome_categoria
    def __repr__(self): return self.nome_categoria