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
        self.tempo_espera = 0.1  # Tempo padrão mais rápido
        self.tempo_digitacao = 0.01  # Velocidade de digitação
        self.arquivo_csv = None
        
        # Configurações do pyautogui
        pyautogui.FAILSAFE = True  # Move mouse para canto superior esquerdo para parar
        pyautogui.PAUSE = 0.05  # Pausa menor entre ações para mais velocidade
        
        print("🤖 Preenchedor Automático Iniciado!")
        print("⚠️  ATENÇÃO: Para parar de emergência, mova o mouse para o canto superior esquerdo da tela")
        
        # Perfis de velocidade predefinidos
        self.perfis_velocidade = {
            "muito_lento": {
                "nome": "🐌 Muito Lento",
                "tempo_espera": 0.5,
                "tempo_digitacao": 0.1,
                "pausa_global": 0.3,
                "descricao": "Para aplicativos muito lentos ou conexões remotas"
            },
            "lento": {
                "nome": "🚶 Lento", 
                "tempo_espera": 0.3,
                "tempo_digitacao": 0.05,
                "pausa_global": 0.2,
                "descricao": "Para aplicativos normais ou sistemas empresariais"
            },
            "rapido": {
                "nome": "🏃 Rápido",
                "tempo_espera": 0.1,
                "tempo_digitacao": 0.01,
                "pausa_global": 0.05,
                "descricao": "Velocidade padrão para a maioria dos aplicativos"
            },
            "muito_rapido": {
                "nome": "⚡ Muito Rápido",
                "tempo_espera": 0.05,
                "tempo_digitacao": 0.005,
                "pausa_global": 0.02,
                "descricao": "Para aplicativos modernos e responsivos"
            },
            "ultra_rapido": {
                "nome": "🚀 Ultra Rápido",
                "tempo_espera": 0.02,
                "tempo_digitacao": 0.001,
                "pausa_global": 0.01,
                "descricao": "Velocidade máxima - cuidado com erros"
            }
        }
    
    def aplicar_perfil_velocidade(self, perfil_nome):
        """Aplica um perfil de velocidade predefinido"""
        if perfil_nome in self.perfis_velocidade:
            perfil = self.perfis_velocidade[perfil_nome]
            self.tempo_espera = perfil["tempo_espera"]
            self.tempo_digitacao = perfil["tempo_digitacao"]
            pyautogui.PAUSE = perfil["pausa_global"]
            print(f"✅ Perfil aplicado: {perfil['nome']}")
            print(f"   {perfil['descricao']}")
            return True
        return False
    
    def obter_tamanho_arquivo(self, arquivo):
        """Retorna o tamanho do arquivo em formato legível"""
        try:
            tamanho_bytes = os.path.getsize(arquivo)
            if tamanho_bytes < 1024:
                return f"({tamanho_bytes} bytes)"
            elif tamanho_bytes < 1024 * 1024:
                return f"({tamanho_bytes / 1024:.1f} KB)"
            else:
                return f"({tamanho_bytes / (1024 * 1024):.1f} MB)"
        except:
            return "(tamanho desconhecido)"
    
    def listar_arquivos_csv(self):
        """Lista todos os arquivos CSV disponíveis"""
        csvs = []
        
        # Procura na pasta atual
        for arquivo in os.listdir("."):
            if arquivo.endswith(".csv"):
                csvs.append(arquivo)
        
        # Ordena os arquivos (extraidos primeiro, depois alfabético)
        csvs.sort(key=lambda x: (0 if "extraidos" in x.lower() else 1, x.lower()))
        
        return csvs
    
    def selecionar_arquivo_csv(self):
        """Permite ao usuário selecionar qual CSV usar"""
        csvs = self.listar_arquivos_csv()
        
        if not csvs:
            print("❌ Nenhum arquivo CSV encontrado na pasta atual!")
            print("💡 Certifique-se que existe pelo menos um arquivo .csv")
            return False
        
        print("📋 Arquivos CSV disponíveis:")
        for i, csv in enumerate(csvs, 1):
            # Adiciona ícone especial para arquivos de dados extraídos
            icone = "🎯" if "extraidos" in csv.lower() else "📄"
            tamanho = self.obter_tamanho_arquivo(csv)
            print(f"   {i}. {icone} {csv} {tamanho}")
        
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
            # Tenta diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            dados_carregados = False
            
            for encoding in encodings:
                try:
                    self.dados = pd.read_csv(self.arquivo_csv, encoding=encoding)
                    print(f"✅ Arquivo carregado com encoding: {encoding}")
                    dados_carregados = True
                    break
                except UnicodeDecodeError:
                    continue
            
            if not dados_carregados:
                print("❌ Não foi possível carregar o arquivo com nenhum encoding")
                return False
            
            print(f"✅ Dados carregados: {len(self.dados)} linhas encontradas")
            
            # Remove coluna 'arquivo' se existir (não é um campo para preencher)
            colunas_para_preencher = [col for col in self.dados.columns if col.lower() != 'arquivo']
            
            print(f"📊 Colunas que serão preenchidas ({len(colunas_para_preencher)}):")
            for i, col in enumerate(colunas_para_preencher[:8], 1):  # Mostra até 8 colunas
                print(f"   {i}. {col}")
            
            if len(colunas_para_preencher) > 8:
                print(f"   ⚠️ Atenção: CSV tem {len(colunas_para_preencher)} colunas, mas apenas as primeiras 8 serão usadas")
            
            # Mostra prévia dos dados
            print("\n📋 Prévia dos dados:")
            # Mostra apenas as colunas que serão preenchidas
            colunas_preview = colunas_para_preencher[:8]
            print(self.dados[colunas_preview].head(2).to_string(index=False))
            
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
        print(f"   ⌨️  Velocidade digitação: {self.tempo_digitacao}s por caractere")
        print(f"   ⚡ Pausa global: {pyautogui.PAUSE}s")
        print(f"   📍 Linha atual: {self.linha_atual + 1}")
        
        # Calcula velocidade estimada
        velocidade = "🐌 Muito Lento"
        if self.tempo_espera <= 0.02:
            velocidade = "🚀 Ultra Rápido"
        elif self.tempo_espera <= 0.05:
            velocidade = "⚡ Muito Rápido"
        elif self.tempo_espera <= 0.1:
            velocidade = "🏃 Rápido"
        elif self.tempo_espera <= 0.3:
            velocidade = "🚶 Lento"
        
        print(f"   🎯 Velocidade atual: {velocidade}")
    
    def configurar_opcoes(self):
        """Permite configurar opções do preenchimento"""
        while True:
            print(f"\n🔧 CONFIGURAÇÕES")
            print("1. Alterar modo (Automático/Manual)")
            print("2. Alterar velocidade de preenchimento")
            print("3. Alterar linha inicial")
            print("4. Configurações avançadas de velocidade")
            print("5. Mostrar dados atuais")
            print("6. Continuar para preenchimento")
            
            opcao = input("\nEscolha uma opção (1-6): ")
            
            if opcao == "1":
                self.modo_automatico = not self.modo_automatico
                print(f"✅ Modo alterado para: {'Automático' if self.modo_automatico else 'Manual'}")
                
            elif opcao == "2":
                self.configurar_velocidade_basica()
                    
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
                self.configurar_velocidade_avancada()
                    
            elif opcao == "5":
                self.mostrar_configuracoes()
                
            elif opcao == "6":
                break
                
            else:
                print("❌ Opção inválida!")
    
    def configurar_velocidade_basica(self):
        """Configuração rápida de velocidade"""
        print(f"\n⚡ PERFIS DE VELOCIDADE")
        print("="*50)
        
        for i, (chave, perfil) in enumerate(self.perfis_velocidade.items(), 1):
            print(f"{i}. {perfil['nome']}")
            print(f"   {perfil['descricao']}")
            print(f"   Tempo entre campos: {perfil['tempo_espera']}s")
            print()
        
        while True:
            try:
                opcao = int(input(f"Escolha um perfil (1-{len(self.perfis_velocidade)}): "))
                if 1 <= opcao <= len(self.perfis_velocidade):
                    perfil_chave = list(self.perfis_velocidade.keys())[opcao - 1]
                    self.aplicar_perfil_velocidade(perfil_chave)
                    break
                else:
                    print("❌ Opção inválida!")
            except ValueError:
                print("❌ Digite um número válido!")
    
    def configurar_velocidade_avancada(self):
        """Configuração detalhada de velocidade"""
        print(f"\n🔧 CONFIGURAÇÃO AVANÇADA DE VELOCIDADE")
        print(f"Configurações atuais:")
        print(f"   • Tempo entre campos: {self.tempo_espera}s")
        print(f"   • Velocidade de digitação: {self.tempo_digitacao}s por caractere")
        print(f"   • Pausa global PyAutoGUI: {pyautogui.PAUSE}s")
        
        while True:
            print(f"\n1. Alterar tempo entre campos ({self.tempo_espera}s)")
            print(f"2. Alterar velocidade de digitação ({self.tempo_digitacao}s)")
            print(f"3. Alterar pausa global ({pyautogui.PAUSE}s)")
            print("4. Voltar")
            
            opcao = input("\nEscolha (1-4): ")
            
            if opcao == "1":
                try:
                    novo_tempo = float(input("Tempo entre campos (0.01-2.0s): "))
                    if 0.01 <= novo_tempo <= 2.0:
                        self.tempo_espera = novo_tempo
                        print(f"✅ Tempo entre campos: {novo_tempo}s")
                    else:
                        print("❌ Tempo deve estar entre 0.01 e 2.0 segundos")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
            elif opcao == "2":
                try:
                    novo_tempo = float(input("Velocidade de digitação (0.001-0.2s): "))
                    if 0.001 <= novo_tempo <= 0.2:
                        self.tempo_digitacao = novo_tempo
                        print(f"✅ Velocidade de digitação: {novo_tempo}s")
                    else:
                        print("❌ Tempo deve estar entre 0.001 e 0.2 segundos")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
            elif opcao == "3":
                try:
                    novo_tempo = float(input("Pausa global (0.01-0.5s): "))
                    if 0.01 <= novo_tempo <= 0.5:
                        pyautogui.PAUSE = novo_tempo
                        print(f"✅ Pausa global: {novo_tempo}s")
                    else:
                        print("❌ Tempo deve estar entre 0.01 e 0.5 segundos")
                except ValueError:
                    print("❌ Digite um número válido!")
                    
            elif opcao == "4":
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
        time.sleep(0.02)  # Pausa mínima
        pyautogui.press('delete')
        time.sleep(0.02)
        
        # Digita o texto com velocidade configurável
        if texto:
            pyautogui.typewrite(texto, interval=self.tempo_digitacao)
        
        time.sleep(self.tempo_espera)
    
    def preencher_linha(self, linha_dados):
        """Preenche uma linha de dados usando ordem das colunas do CSV"""
        print(f"\n📝 Preenchendo linha {self.linha_atual + 1}:")
        
        # Pega todas as colunas do CSV (exceto 'arquivo' se existir)
        colunas_csv = [col for col in self.dados.columns if col.lower() != 'arquivo']
        
        # Limita a 8 campos (máximo que o formulário aceita)
        colunas_para_preencher = colunas_csv[:8]
        
        print(f"� Preenchendo {len(colunas_para_preencher)} campo(s) do CSV:")
        
        for i, coluna in enumerate(colunas_para_preencher):
            valor = linha_dados[coluna] if coluna in linha_dados else ""
            
            # Mostra qual campo está sendo preenchido
            print(f"   {i+1}. {coluna}: {valor}")
            
            # Digita o valor
            self.digitar_com_seguranca(valor)
            
            # Vai para o próximo campo (Tab) - exceto no último
            if i < len(colunas_para_preencher) - 1:
                pyautogui.press('tab')
                time.sleep(self.tempo_espera)
        
        # Se tem menos de 8 colunas, preenche os campos restantes com vazio
        campos_restantes = 8 - len(colunas_para_preencher)
        if campos_restantes > 0:
            print(f"   ⏭️  Pulando {campos_restantes} campo(s) vazios...")
            for i in range(campos_restantes):
                if i < campos_restantes - 1:  # Não dá Tab no último campo
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
                    time.sleep(self.tempo_espera * 1.5)  # Um pouco mais de tempo para mudança de linha
            
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
        print("   • Preencher campos na ORDEM das colunas do CSV")
        print("   • Pressionar TAB para próximo campo") 
        print("   • Pressionar ENTER para próxima linha")
        print("\n📊 FUNCIONAMENTO:")
        print("   • Usa QUALQUER CSV (não precisa ter nomes específicos)")
        print("   • Preenche na ordem: Coluna1 → Coluna2 → Coluna3...")
        print("   • Ignora coluna 'arquivo' se existir")
        print("   • Máximo de 8 campos por linha")
        print("\n⚡ PERFIS DE VELOCIDADE:")
        print("   🐌 Muito Lento: Para apps lentos ou conexões remotas")
        print("   🚶 Lento: Para sistemas empresariais tradicionais")
        print("   🏃 Rápido: Velocidade padrão (recomendado)")
        print("   ⚡ Muito Rápido: Para aplicativos modernos")
        print("   🚀 Ultra Rápido: Velocidade máxima (cuidado com erros)")
        print("\n⚙️  MODOS DISPONÍVEIS:")
        print("   🤖 Automático: Preenche tudo sozinho com pausas")
        print("   👤 Manual: Espera você pressionar Enter entre linhas")
        print("\n🛑 CONTROLES:")
        print("   ESC: Pausar (modo automático)")
        print("   SPACE: Continuar (quando pausado)")
        print("   Q: Sair (quando pausado)")
        print("   Mouse canto superior esquerdo: Parada de emergência")
        print("\n💡 DICAS DE VELOCIDADE:")
        print("   • Teste com velocidade LENTA primeiro")
        print("   • Aumente gradualmente se o app acompanhar")
        print("   • Use MUITO RÁPIDO apenas em apps modernos")
        print("   • Configure velocidade avançada se necessário")
        print("="*50)
    
    def listar_e_mostrar_csvs(self):
        """Lista todos os CSVs e mostra informações detalhadas"""
        csvs = self.listar_arquivos_csv()
        
        if not csvs:
            print("❌ Nenhum arquivo CSV encontrado na pasta atual!")
            return
        
        print(f"\n📊 ARQUIVOS CSV ENCONTRADOS ({len(csvs)} arquivo(s)):")
        print("="*60)
        
        for i, csv in enumerate(csvs, 1):
            # Ícone baseado no tipo de arquivo
            if "extraidos" in csv.lower():
                icone = "🎯"
                tipo = "Dados Extraídos"
            elif "teste" in csv.lower():
                icone = "🧪"
                tipo = "Arquivo de Teste"
            else:
                icone = "📄"
                tipo = "CSV Genérico"
            
            tamanho = self.obter_tamanho_arquivo(csv)
            
            print(f"\n{i}. {icone} {csv}")
            print(f"   📋 Tipo: {tipo}")
            print(f"   📏 Tamanho: {tamanho}")
            
            # Tenta mostrar informações básicas do arquivo
            try:
                df_temp = pd.read_csv(csv, encoding='utf-8', nrows=0)  # Só as colunas
                print(f"   📊 Colunas ({len(df_temp.columns)}): {', '.join(df_temp.columns[:5])}")
                if len(df_temp.columns) > 5:
                    print(f"        ... e mais {len(df_temp.columns) - 5} colunas")
                
                # Conta linhas
                df_count = pd.read_csv(csv, encoding='utf-8')
                print(f"   📈 Linhas: {len(df_count)}")
                
            except Exception as e:
                print(f"   ⚠️ Erro ao ler arquivo: {str(e)[:50]}...")
        
        print("\n" + "="*60)
        
        # Opção de selecionar um arquivo para ver detalhes
        while True:
            opcao = input(f"\nDeseja ver detalhes de algum arquivo? (1-{len(csvs)} ou 'n' para voltar): ")
            
            if opcao.lower() in ['n', 'nao', 'não', 'no']:
                break
            
            try:
                indice = int(opcao) - 1
                if 0 <= indice < len(csvs):
                    self.mostrar_detalhes_csv(csvs[indice])
                    break
                else:
                    print("❌ Número inválido!")
            except ValueError:
                print("❌ Digite um número ou 'n'!")
    
    def mostrar_detalhes_csv(self, arquivo):
        """Mostra detalhes completos de um arquivo CSV"""
        print(f"\n📋 DETALHES DE: {arquivo}")
        print("="*50)
        
        try:
            df = pd.read_csv(arquivo, encoding='utf-8')
            
            print(f"📊 Informações Gerais:")
            print(f"   • Linhas: {len(df)}")
            print(f"   • Colunas: {len(df.columns)}")
            print(f"   • Tamanho: {self.obter_tamanho_arquivo(arquivo)}")
            
            print(f"\n📋 Colunas:")
            for i, col in enumerate(df.columns, 1):
                # Conta valores não-nulos
                nao_nulos = df[col].notna().sum()
                porcentagem = (nao_nulos / len(df)) * 100 if len(df) > 0 else 0
                print(f"   {i:2d}. {col} ({nao_nulos}/{len(df)} preenchidos - {porcentagem:.1f}%)")
            
            print(f"\n📋 Primeiras 3 linhas:")
            print(df.head(3).to_string(index=False))
            
            if len(df) > 3:
                print(f"\n... e mais {len(df) - 3} linha(s)")
            
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
        
        print("\n" + "="*50)

def main():
    print("🤖 PREENCHEDOR AUTOMÁTICO DE DADOS")
    print("="*50)
    
    preenchedor = PreenchedorAutomatico()
    
    while True:
        print(f"\n📋 MENU PRINCIPAL:")
        print("1. Iniciar preenchimento")
        print("2. Listar todos os arquivos CSV")
        print("3. Mostrar ajuda")
        print("4. Sair")
        
        opcao = input("\nEscolha uma opção (1-4): ")
        
        if opcao == "1":
            preenchedor.iniciar_preenchimento()
            
        elif opcao == "2":
            preenchedor.listar_e_mostrar_csvs()
            
        elif opcao == "3":
            preenchedor.mostrar_ajuda()
            
        elif opcao == "4":
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