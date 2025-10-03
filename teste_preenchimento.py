import pandas as pd
import time
import tkinter as tk
from tkinter import ttk

class AppTeste:
    def __init__(self):
        """Cria um app de teste para simular o preenchimento"""
        self.root = tk.Tk()
        self.root.title("🧪 App de Teste - Simulação")
        self.root.geometry("600x500")
        
        # Dados para teste
        self.campos = [
            'Número do Documento',
            'Código do Produto', 
            'Quantidade',
            'Valor Unitário',
            'Valor Total',
            'Placa',
            'KM',
            'Modelo do Veículo'
        ]
        
        self.criar_interface()
    
    def criar_interface(self):
        """Cria a interface do app de teste"""
        # Título
        title = tk.Label(self.root, text="🧪 SIMULADOR DE APLICATIVO", 
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # Instruções
        instrucoes = tk.Label(self.root, 
                             text="Use este app para testar o preenchedor automático!\n" +
                                  "Clique no primeiro campo e execute o preenchedor_automatico.py",
                             font=("Arial", 10),
                             fg="blue")
        instrucoes.pack(pady=5)
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Cria 5 linhas de formulário
        self.entries = []
        for linha in range(5):
            linha_frame = ttk.LabelFrame(main_frame, text=f"📋 Linha {linha + 1}")
            linha_frame.pack(fill="x", pady=5)
            
            linha_entries = []
            for i, campo in enumerate(self.campos):
                # Label
                label = ttk.Label(linha_frame, text=f"{campo}:")
                label.grid(row=i//4, column=(i%4)*2, sticky="w", padx=5, pady=2)
                
                # Entry
                entry = ttk.Entry(linha_frame, width=15)
                entry.grid(row=i//4, column=(i%4)*2+1, padx=5, pady=2)
                linha_entries.append(entry)
            
            self.entries.append(linha_entries)
        
        # Botão de limpeza
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        limpar_btn = ttk.Button(btn_frame, text="🧹 Limpar Tudo", command=self.limpar_tudo)
        limpar_btn.pack(side="left", padx=5)
        
        salvar_btn = ttk.Button(btn_frame, text="💾 Salvar Dados", command=self.salvar_dados)
        salvar_btn.pack(side="left", padx=5)
        
        # Status
        self.status = tk.Label(self.root, text="✅ Pronto para teste!", fg="green")
        self.status.pack(pady=5)
    
    def limpar_tudo(self):
        """Limpa todos os campos"""
        for linha_entries in self.entries:
            for entry in linha_entries:
                entry.delete(0, tk.END)
        self.status.config(text="🧹 Todos os campos limpos!", fg="blue")
    
    def salvar_dados(self):
        """Salva os dados preenchidos"""
        dados = []
        for i, linha_entries in enumerate(self.entries):
            linha_dados = {}
            for j, entry in enumerate(linha_entries):
                valor = entry.get().strip()
                if valor:  # Só salva se tiver conteúdo
                    linha_dados[self.campos[j]] = valor
            
            if linha_dados:  # Só adiciona se a linha tiver dados
                linha_dados['Linha'] = i + 1
                dados.append(linha_dados)
        
        if dados:
            df = pd.DataFrame(dados)
            df.to_csv("dados_teste_preenchidos.csv", index=False, encoding='utf-8')
            self.status.config(text=f"💾 {len(dados)} linha(s) salva(s) em dados_teste_preenchidos.csv", fg="green")
        else:
            self.status.config(text="⚠️ Nenhum dado para salvar!", fg="orange")
    
    def executar(self):
        """Executa o app"""
        print("🧪 Iniciando App de Teste...")
        print("="*50)
        print("📋 Instruções:")
        print("1. Clique no primeiro campo (Número do Documento da Linha 1)")
        print("2. Execute: python preenchedor_automatico.py")
        print("3. Escolha um arquivo CSV de dados extraídos")
        print("4. Configure as opções e inicie o preenchimento")
        print("="*50)
        
        self.root.mainloop()

if __name__ == "__main__":
    app = AppTeste()
    app.executar()