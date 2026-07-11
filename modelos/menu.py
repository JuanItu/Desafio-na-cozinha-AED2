class Menu:
    registro_global = {} # O nosso Banco de Menus em Memória!

    def __init__(self, nome_menu: str):
        self.nome_menu = nome_menu
        
        # Dicionário relacionando String (Categoria) a uma Lista de Receitas
        # Ex: {"Entradas": [ReceitaA, ReceitaB], "Sobremesas": [ReceitaC]}
        self.pratos_por_categoria = {}
        
        # Estatísticas autocalculadas
        self.lucro_total = 0.0
        self.custo_total = 0.0
        self.tempo_total = 0
        
        # Salva automaticamente no banco de menus
        Menu.registro_global[nome_menu.lower()] = self

    def definir_pratos(self, dicionario_pratos: dict):
        """
        Substitui o cardápio inteiro e recalcula as estatísticas.
        Usado pelo Otimizador ou quando o Chef carrega um menu salvo.
        """
        self.pratos_por_categoria = dicionario_pratos
        self.recalcular_estatisticas()

    def adicionar_prato(self, nome_categoria: str, receita):
        """Permite ao Chef adicionar pratos avulsos manualmente."""
        if nome_categoria not in self.pratos_por_categoria:
            self.pratos_por_categoria[nome_categoria] = []
        self.pratos_por_categoria[nome_categoria].append(receita)
        self.recalcular_estatisticas()

    def remover_prato(self, nome_categoria: str, receita):
        """Permite ao Chef remover pratos manualmente."""
        if nome_categoria in self.pratos_por_categoria:
            if receita in self.pratos_por_categoria[nome_categoria]:
                self.pratos_por_categoria[nome_categoria].remove(receita)
                if not self.pratos_por_categoria[nome_categoria]:
                    del self.pratos_por_categoria[nome_categoria] # Limpa a chave se ficar vazia
                self.recalcular_estatisticas()

    def recalcular_estatisticas(self):
        """
        O Menu calcula a própria vida. Não confia em dados externos.
        """
        self.lucro_total = 0.0
        self.custo_total = 0.0
        self.tempo_total = 0
        
        for lista_receitas in self.pratos_por_categoria.values():
            for prato in lista_receitas:
                self.lucro_total += prato.fator_recomendacao
                self.custo_total += prato.custo
                self.tempo_total += prato.tempo_preparo 

    def exibir_recibo(self):
        """Imprime o menu formatado."""
        print("\n" + "═" * 55)
        print(f" 🌟 MENU: {self.nome_menu.upper()} 🌟")
        print("═" * 55)
        for nome_cat, lista_pratos in self.pratos_por_categoria.items():
            print(f"\n 🍽️  {nome_cat.upper()}:")
            for i, prato in enumerate(lista_pratos, 1):
                print(f"    {i}. {prato.nome_receita} (C: {prato.custo:.2f}¢$ | T: {prato.tempo_preparo}m)")
                
        print("\n" + "─" * 55)
        print(f" 💰 Custo Total : {self.custo_total:.2f} ¢$")
        print(f" ⏳ Tempo Total : {self.tempo_total} min")
        print(f" ⭐ Fator/Lucro : {self.lucro_total:.2f} pts")
        print("═" * 55 + "\n")