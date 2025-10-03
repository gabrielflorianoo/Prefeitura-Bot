import pandas as pd
import pyautogui
import time
import os
import sys
from pathlib import Path
import keyboard
import threading

class PreenchedorAutomatico:
    def __init__(self):
        """Inicializa o preenchedor automático"""
        self.dados = None
        self.linha_atual = 0
        self.modo_automatico = True
        self.pausado = False
        self.tempo_espera = 0.3  # Tempo entre ações
        self.arquivo_csv = None
        
        # Configurações do pyautogui
        pyautogui.FAILSAFE = True  # Move mouse para canto superior esquerdo para parar
        pyautogui.PAUSE = 0.1  # Pausa pequena entre ações
        
        print("🤖 Preenchedor Automático Iniciado!")
        print("⚠️  ATENÇÃO: Para parar de emergência, mova o mouse para o canto superior esquerdo da tela")
    
    def listar_arquivos_csv(self):
        """Lista todos os arquivos CSV disponíveis"""
        csvs = []
        
        # Procura na pasta atual
        for arquivo in os.listdir("."):
            if arquivo.endswith(".csv") and "extraidos" in arquivo.lower():
                csvs.append(arquivo)
        
        return csvs
    
    def selecionar_arquivo_csv(self):
        """Permite ao usuário selecionar qual CSV usar"""
        csvs = self.listar_arquivos_csv()
        
        if not csvs:
            print("❌ Nenhum arquivo CSV de dados extraídos encontrado!")
            print("💡 Certifique-se que existe um arquivo CSV com 'extraidos' no nome")
            return False
        
        print("📋 Arquivos CSV disponíveis:")
        for i, csv in enumerate(csvs, 1):
            print(f"   {i}. {csv}")
        
        while True:
            try:
                escolha = input(f"\nEscolha um arquivo (1-{len(csvs)}): ")
                indice = int(escolha) - 1
                if 0 <= indice < len(csvs):
                    self.arquivo_csv = csvs[indice]
                    print(f"✅ Arquivo selecionado: {self.arquivo_csv}")
                    return True
                else:
                    print("❌ Número inválido!")
            except ValueError:
                print("❌ Digite apenas números!")
    
    def carregar_dados_csv(self):
        """Carrega dados do arquivo CSV"""
        if not self.arquivo_csv:
            if not self.selecionar_arquivo_csv():
                return False
        
        try:
            self.dados = pd.read_csv(self.arquivo_csv, encoding='utf-8')
            print(f"✅ Dados carregados: {len(self.dados)} linhas encontradas")
            
            # Mostra prévia dos dados
            print("\n📋 Prévia dos dados:")
            print(self.dados.head(2).to_string(index=False))
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return False
    
    def mostrar_configuracoes(self):
        """Mostra configurações atuais"""
        print(f"\n⚙️  CONFIGURAÇÕES ATUAIS:")
        print(f"   📁 Arquivo: {self.arquivo_csv}")
        print(f"   📊 Total de linhas: {len(self.dados) if self.dados is not None else 0}")
        print(f"   🏃 Modo: {'Automático' if self.modo_automatico else 'Manual'}")
        print(f"   ⏱️  Tempo entre campos: {self.tempo_espera}s")
        print(f"   📍 Linha atual: {self.linha_atual + 1}")
    
    def configurar_opcoes(self):
        """Permite configurar opções do preenchimento"""
        while True:
            print(f"\n🔧 CONFIGURAÇÕES")
            print("1. Alterar modo (Automático/Manual)")
            print("2. Alterar tempo de espera")
            print("3. Alterar linha inicial")
            print("4. Mostrar dados atuais")
            print("5. Continuar para preenchimento")
            
            opcao = input("\nEscolha uma opção (1-5): ")
            
            if opcao == "1":
                self.modo_automatico = not self.modo_automatico
                print(f"✅ Modo alterado para: {'Automático' if self.modo_automatico else 'Manual'}")
                
            elif opcao == "2":
                try:
                    novo_tempo = float(input("Digite o tempo de espera em segundos (0.1-5.0): "))
                    if 0.1 <= novo_tempo <= 5.0:
                        self.tempo_espera = novo_tempo
                        print(f"✅ Tempo alterado para: {novo_tempo}s")
                    else:
                        print("❌ Tempo deve estar entre 0.1 e 5.0 segundos")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
            elif opcao == "3":
                try:
                    nova_linha = int(input(f"Digite a linha inicial (1-{len(self.dados)}): "))
                    if 1 <= nova_linha <= len(self.dados):
                        self.linha_atual = nova_linha - 1
                        print(f"✅ Linha inicial alterada para: {nova_linha}")
                    else:
                        print(f"❌ Linha deve estar entre 1 e {len(self.dados)}")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
            elif opcao == "4":
                self.mostrar_configuracoes()
                
            elif opcao == "5":
                break
                
            else:
                print("❌ Opção inválida!")
    
    def digitar_com_seguranca(self, texto):
        """Digita texto com verificação de segurança"""
        if texto is None or pd.isna(texto):
            texto = ""
        else:
            texto = str(texto).strip()
        
        # Limpa o campo atual primeiro (Ctrl+A + Delete)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.press('delete')
        time.sleep(0.1)
        
        # Digita o texto
        if texto:
            pyautogui.typewrite(texto, interval=0.05)
        
        time.sleep(self.tempo_espera)
    
    def preencher_linha(self, linha_dados):
        """Preenche uma linha de dados"""
        campos_ordem = [
            'numero_documento',
            'codigo_produto', 
            'quantidade',
            'valor_unitario',
            'valor_total',
            'placa',
            'km',
            'modelo_veiculo'
        ]
        
        print(f"\n📝 Preenchendo linha {self.linha_atual + 1}:")
        
        for i, campo in enumerate(campos_ordem):
            if campo in linha_dados:
                valor = linha_dados[campo]
                print(f"   {i+1}. {campo}: {valor}")
                
                # Digita o valor
                self.digitar_com_seguranca(valor)
                
                # Vai para o próximo campo (Tab)
                if i < len(campos_ordem) - 1:  # Não dá Tab no último campo
                    pyautogui.press('tab')
                    time.sleep(self.tempo_espera)
            else:
                print(f"   {i+1}. {campo}: CAMPO NÃO ENCONTRADO")
                # Mesmo assim dá Tab para pular o campo
                if i < len(campos_ordem) - 1:
                    pyautogui.press('tab')
                    time.sleep(self.tempo_espera)
    
    def aguardar_confirmacao(self):
        """Aguarda confirmação do usuário para continuar"""
        if self.modo_automatico:
            print("⏳ Aguardando 3 segundos para próxima linha... (ESC para pausar)")
            for i in range(3):
                if keyboard.is_pressed('esc'):
                    self.pausado = True
                    print("\n⏸️  PAUSADO! Pressione SPACE para continuar ou Q para sair")
                    while self.pausado:
                        if keyboard.is_pressed('space'):
                            self.pausado = False
                            print("▶️  Continuando...")
                            time.sleep(0.5)
                            break
                        elif keyboard.is_pressed('q'):
                            return False
                        time.sleep(0.1)
                time.sleep(1)
        else:
            input("\n⏳ Pressione Enter para ir para próxima linha (ou Ctrl+C para sair)...")
        
        return True
    
    def iniciar_preenchimento(self):
        """Inicia o processo de preenchimento"""
        if not self.carregar_dados_csv():
            return
        
        self.configurar_opcoes()
        self.mostrar_configuracoes()
        
        print(f"\n🚀 INICIANDO PREENCHIMENTO!")
        print("="*50)
        print("⚠️  IMPORTANTE:")
        print("   • Clique no primeiro campo do seu aplicativo")
        print("   • O script começará em 5 segundos")
        print("   • ESC para pausar (modo automático)")
        print("   • Mouse no canto superior esquerdo para parar emergência")
        print("="*50)
        
        # Countdown
        for i in range(5, 0, -1):
            print(f"🕐 Iniciando em {i} segundos...")
            time.sleep(1)
        
        print("🤖 INICIADO! Preenchendo dados...")
        
        try:
            while self.linha_atual < len(self.dados):
                linha_dados = self.dados.iloc[self.linha_atual]
                
                # Preenche a linha atual
                self.preencher_linha(linha_dados)
                
                # Atualiza contador
                self.linha_atual += 1
                
                # Se não é a última linha, aguarda confirmação
                if self.linha_atual < len(self.dados):
                    if not self.aguardar_confirmacao():
                        break
                    
                    # Vai para próxima linha (Enter ou seta para baixo)
                    print("⬇️  Indo para próxima linha...")
                    pyautogui.press('enter')  # ou 'down' dependendo do seu app
                    time.sleep(self.tempo_espera * 2)
            
            print(f"\n🎉 PREENCHIMENTO CONCLUÍDO!")
            print(f"📊 {self.linha_atual} linha(s) processada(s)")
            
        except KeyboardInterrupt:
            print(f"\n⏹️  Preenchimento interrompido pelo usuário")
            print(f"📍 Parou na linha: {self.linha_atual + 1}")
        
        except Exception as e:
            print(f"\n❌ Erro durante preenchimento: {e}")
            print(f"📍 Parou na linha: {self.linha_atual + 1}")
    
    def mostrar_ajuda(self):
        """Mostra ajuda sobre como usar"""
        print("\n📖 COMO USAR O PREENCHEDOR AUTOMÁTICO:")
        print("="*50)
        print("1️⃣  Abra seu aplicativo de trabalho")
        print("2️⃣  Posicione o cursor no PRIMEIRO CAMPO da primeira linha")
        print("3️⃣  Execute este script e siga as instruções")
        print("4️⃣  O script irá:")
        print("   • Preencher cada campo")
        print("   • Pressionar TAB para próximo campo") 
        print("   • Pressionar ENTER para próxima linha")
        print("\n⚙️  MODOS DISPONÍVEIS:")
        print("   🤖 Automático: Preenche tudo sozinho com pausas")
        print("   👤 Manual: Espera você pressionar Enter entre linhas")
        print("\n🛑 CONTROLES:")
        print("   ESC: Pausar (modo automático)")
        print("   SPACE: Continuar (quando pausado)")
        print("   Q: Sair (quando pausado)")
        print("   Mouse canto superior esquerdo: Parada de emergência")
        print("="*50)

def main():
    print("🤖 PREENCHEDOR AUTOMÁTICO DE DADOS")
    print("="*50)
    
    preenchedor = PreenchedorAutomatico()
    
    while True:
        print(f"\n📋 MENU PRINCIPAL:")
        print("1. Iniciar preenchimento")
        print("2. Mostrar ajuda")
        print("3. Sair")
        
        opcao = input("\nEscolha uma opção (1-3): ")
        
        if opcao == "1":
            preenchedor.iniciar_preenchimento()
            
        elif opcao == "2":
            preenchedor.mostrar_ajuda()
            
        elif opcao == "3":
            print("👋 Saindo...")
            break
            
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Programa encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione Enter para sair...")