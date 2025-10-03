import os
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
import platform
import io
import base64
import json
import requests
from typing import Dict, List, Optional
import csv
import re

class OpenRouterExtractor:
    def __init__(self, api_key: str = None):
        """
        Inicializa o extrator OpenRouter
        
        Args:
            api_key: Chave da API OpenRouter (se None, tentará pegar da variável de ambiente)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("API Key do OpenRouter não encontrada. Defina OPENROUTER_API_KEY ou passe como parâmetro.")
        
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/your-app",  # Opcional
            "X-Title": "PDF Data Extractor"  # Opcional
        }
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Converte imagem PIL para base64"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def segmentar_imagem_horizontal(self, img, num_segmentos=4, segmentos_desejados=[2, 3]):
        """Segmenta a imagem horizontalmente e retorna apenas os segmentos desejados"""
        width, height = img.size
        altura_segmento = height // num_segmentos
        
        segmentos = []
        
        for i in segmentos_desejados:
            y_inicio = i * altura_segmento
            y_fim = (i + 1) * altura_segmento if i < num_segmentos - 1 else height
            segmento = img.crop((0, y_inicio, width, y_fim))
            segmentos.append(segmento)
        
        return segmentos

    def recortar_regioes_fixas(self, img: Image.Image) -> List[Image.Image]:
        """Recorta as quatro regiões fixas indicadas pelo usuário.

        Regiões (x, y, largura, altura):
        - Número do documento: 470x0, 375x330
        - Data e hora: 980x325, 220x220
        - Corpo do documento (tudo exceto placa/km/modelo): 0x800, 1200x1800
        - Placa/KM/Modelo: 0x1275, 425x330

        Retorna lista de imagens PIL na ordem: [num_doc, data_hora, corpo, placa_km_modelo]
        """
        w, h = img.size

        regions = []

        # Número do documento
        x, y, rw, rh = 470, 0, 375, 330
        regions.append(img.crop((x, y, x + rw, y + rh)))

        # Data e hora
        x, y, rw, rh = 980, 325, 220, 220
        regions.append(img.crop((x, y, x + rw, y + rh)))

        # Corpo do documento
        x, y, rw, rh = 0, 800, 1200, 1800
        # Limita ao tamanho da imagem
        x2 = min(x + rw, w)
        y2 = min(y + rh, h)
        regions.append(img.crop((x, y, x2, y2)))

        # Placa, KM e Modelo
        x, y, rw, rh = 0, 1275, 425, 330
        x2 = min(x + rw, w)
        y2 = min(y + rh, h)
        regions.append(img.crop((x, y, x2, y2)))

        return regions
    
    def extrair_dados_com_openrouter(self, image: Image.Image) -> Dict[str, Optional[str]]:
        """
        Usa OpenRouter para extrair dados específicos da imagem
        
        Args:
            image: Imagem PIL
        
        Returns:
            Dicionário com os dados extraídos
        """
        # Converte imagem para base64
        img_base64 = self.image_to_base64(image)
        
        # Prompt específico para extração de dados
        prompt = """
        Analise esta imagem de um documento fiscal/nota e extraia EXATAMENTE as seguintes informações:

        1. **Número do Documento**: Número do documento que possui 4 dígitos (ex de formato: XXXX).
        2. **Data do documento**: Data em que o documento foi emitido (formato: DD/MM/AAAA).
        3. **Hora do documento**: Hora em que o documento foi emitido (formato: HH:MM).
        4. **Tipo de Combustível**: O tipo do combustível (ex: Gasolina, Etanol, Etanol S10, Diesel, etc).
        5. **Quantidade**: Quantidade do produto (em litros ou unidades).
        6. **Valor Unitário**: Preço por unidade (R$), ele sempre terá 3 casas decimais, use virgulas e pontos conforme o documento.
        7. **Valor Total**: Valor total da compra (R$), ele sempre terá 3 casas decimais, use virgulas e pontos conforme o documento.
        8. **Placa**: Placa do veículo (formato ABC-1234 ou ABC1D23).
        9. **KM**: Quilometragem do veículo.
        10. **Modelo do Veículo**: Modelo/marca do carro, ele está em frente ao "OBS" logo acima do "MOTOTISTA" e abaixo da placa e km,

        se não encontrar, retorne null, não confundir com o nome do motorista que também está acima do modelo do carro.

        INSTRUÇÕES IMPORTANTES:
        - Retorne APENAS um JSON válido com os campos exatos.
        - Use null para campos não encontrados.
        - Para valores monetários, use apenas números e com formatação do Brasil (ex: "35198,75").
        - Para o número do documento, ele fica localizado junto com o número de Série e "NF-e", e o número do documento é o de 4 dígitos que vem logo acima, na parte mais inferior do documento.
        - Caso não encontre a hora do documento, retorne 00:00.
        - Para quantidade, valor unitário e valor total, mantenha o formato original do documento
        - Para placa, mantenha o formato original e a placa sempre tera o formato ABC1234, ABC1D23 , 1234 ou AB1234, caso encontre um resultado diferente ou não consiga indentificar, retorne null.
        - Faça a conta de quantidade * valor unitário e veja se bate com o valor total, se não bater, retorne null para valor total e retorne um aviso.
        - Para o combustível, os numeros 3 = D (Diesel S500), 4 = DS (Diesel S10), 5 = G (Gasolina), retorne apenas a sigla (ex: DS, G, D, etc).
        - A placa, km e modelo do veículo estão localizados na parte inferior do documento, na seção "DADOS ADICIONAIS", logo acima do "MOTOTISTA".
        - Seja preciso e extraia apenas o que está claramente visível.
        - Retorne nomes com todos os caracteres em maiúsculo.
        - Caso não tenha certeza sobre mais que 1 campo em 1 arquivo, retorne uma mensagem falando para o usuário conferir o documento.

        Formato de resposta esperado:
        {
            "data_documento": "DD/MM/AAAA ou null",
            "hora_documento": "HH:MM ou null",
            "tipo_combustível": "valor ou null",
            "quantidade": "valor ou null",
            "valor_unitario": "valor ou null",
            "valor_total": "valor ou null",
            "numero_documento": "valor ou null",
            "placa": "valor ou null",
            "km": "valor ou null",
            "modelo_veiculo": "valor ou null",
        }
        """
        
        # Usando modelos de visão GRATUITOS/BARATOS disponíveis no OpenRouter
        modelos_disponiveis = [
            # "x-ai/grok-4-fast:free",
            "meta-llama/llama-3.2-90b-vision-instruct",
            # "mistralai/mistral-small-3.2-24b-instruct:free",
            # "google/gemini-flash-1.5",
        ]
        
        # Tenta diferentes modelos até encontrar um que funcione
        for modelo in modelos_disponiveis:
            try:
                # Payload para a API
                payload = {
                    "model": modelo,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.1  # Baixa temperatura para mais precisão
                }
                
                print(f"  Enviando imagem para OpenRouter ({modelo})...")
                response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        print(f"  Resposta da API recebida com sucesso usando {modelo}!")
                        
                        # Busca por JSON na resposta
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        
                        if json_start != -1 and json_end != -1:
                            json_str = content[json_start:json_end]
                            try:
                                dados_extraidos = json.loads(json_str)
                                return dados_extraidos
                            except json.JSONDecodeError as e:
                                print(f"  Erro ao decodificar JSON: {e}")
                                continue
                        else:
                            print(f"  Não foi encontrado JSON válido na resposta")
                            continue
                    else:
                        print(f"  Resposta sem choices válidos")
                        continue
                else:
                    print(f"  Erro HTTP {response.status_code} com {modelo}: {response.text}")
                    # Se for 404, provavelmente o modelo não está disponível
                    if response.status_code == 404:
                        print(f"  Modelo {modelo} não disponível, tentando próximo...")
                    continue
            except requests.exceptions.RequestException as e:
                print(f"  Erro de conexão com {modelo}: {e}")
                continue
            except Exception as e:
                print(f"  Erro inesperado com {modelo}: {e}")
                continue
        
        # Se chegou aqui, nenhum modelo funcionou
        print("  ❌ Todos os modelos falharam. Retornando resultado vazio.")
        return self._criar_resultado_vazio()
    
    def _criar_resultado_vazio(self):
        """Cria um dicionário com todos os campos como None"""
        return {
            'data_documento': None,
            'hora_documento': None,
            'tipo_combustível': None,
            'quantidade': None,
            'valor_unitario': None,
            'valor_total': None,
            'numero_documento': None,
            'placa': None,
            'km': None,
            'modelo_veiculo': None,
        }

    def _normalizar_valor(self, valor):
        """Normaliza strings numéricas para uma forma consistente (usa ponto como separador decimal).

        - Se receber None, retorna None
        - Remove espaços
        - Se tiver ponto e vírgula como separadores (ex: '1.234,56'), transforma em '1234.56'
        - Se tiver apenas vírgula como separador decimal, troca por ponto
        - Remove caracteres indesejados
        Retorna string normalizada ou valor original quando não puder normalizar.
        """
        if valor is None:
            return None

        # Se já for numérico (int/float), retorna como string
        if isinstance(valor, (int, float)):
            return str(valor)

        s = str(valor).strip()
        if not s:
            return None

        # Remove espaços e caracteres invisíveis
        s = s.replace('\u00a0', '').replace('\n', ' ').strip()

        # Caso contenha letras:
        # - Se contém apenas letras (ex.: 'AMB RENAULT'), retorna em maiúsculas
        # - Se contém letras e dígitos (ex.: placas como 'FEI6365'), preserva e retorna em maiúsculas
        if any(c.isalpha() for c in s):
            if re.search(r'\d', s):
                # Letras e dígitos: mantém caracteres alfanuméricos e símbolos úteis
                s_clean = re.sub(r'[^A-Za-z0-9\- ]', '', s)
                return s_clean.upper().strip()
            else:
                return s.upper()

        # Normaliza números com milhares e decimais
        # Ex: '1.234,56' -> '1234.56'; '134,58' -> '134.58'; '22,850' -> '22.850' (ambíguo) -> treat comma as decimal
        # Se houver tanto '.' quanto ',', assume '.' é separador de milhares e ',' decimal
        try:
            if '.' in s and ',' in s:
                s2 = s.replace('.', '').replace(',', '.')
            elif ',' in s and '.' not in s:
                s2 = s.replace(',', '.')
            else:
                s2 = s

            # Remove quaisquer caracteres que não sejam dígitos, ponto, ou sinal
            s2 = re.sub(r'[^0-9\.-]', '', s2)

            # Evita strings vazias
            if s2 == '' or s2 == '.' or s2 == '-':
                return None

            return s2
        except Exception:
            return s
    
    def processar_pdf(self, caminho_pdf):
        """
        Processa um PDF e extrai dados usando OpenRouter
        
        Args:
            caminho_pdf: Caminho para o arquivo PDF
        
        Returns:
            Dicionário com os dados extraídos
        """
        print(f"\n📄 Processando: {caminho_pdf}")
        print("-" * 60)
        
        try:
            # Abre o PDF
            documento = fitz.open(caminho_pdf)
            
            # Processa cada página
            resultados_finais = self._criar_resultado_vazio()
            
            for i in range(documento.page_count):
                print(f"📑 Processando página {i+1}/{documento.page_count}...")
                
                # Converte página para imagem
                pagina = documento[i]
                matriz = fitz.Matrix(2.0, 2.0)  # Alta resolução
                pix = pagina.get_pixmap(matrix=matriz)
                img_data = pix.tobytes("ppm")
                img_original = Image.open(io.BytesIO(img_data))
                
                print(f"  📐 Imagem original: {img_original.size}")
                
                # Recorta regiões fixas onde os campos normalmente aparecem
                regioes = self.recortar_regioes_fixas(img_original)

                labels = ['numero_documento', 'data_hora', 'corpo_doc', 'placa_km_modelo']

                # Processa cada região recortada
                for idx_reg, segmento in enumerate(regioes):
                    label = labels[idx_reg] if idx_reg < len(labels) else f"regiao_{idx_reg}"
                    print(f"  🔍 Analisando região '{label}' (índice {idx_reg})...")
                    
                    # Extrai dados da região usando OpenRouter
                    dados_segmento = self.extrair_dados_com_openrouter(segmento)
                    
                    # Combina resultados (prioriza dados não-nulos)
                    for campo, valor in dados_segmento.items():
                        # Normaliza chaves e valores
                        chave = campo if isinstance(campo, str) else str(campo)
                        # Ignora valores vazios ou 'null'
                        if valor is None or (isinstance(valor, str) and valor.strip().lower() == 'null'):
                            continue

                        # Normaliza o valor (numéricos e strings)
                        try:
                            valor_norm = self._normalizar_valor(valor)
                        except Exception:
                            valor_norm = valor

                        # Se a chave já existe no resultado final, prioriza o primeiro valor não-nulo
                        if chave in resultados_finais:
                            if resultados_finais[chave] is None:
                                resultados_finais[chave] = valor_norm
                                print(f"    ✅ {chave}: {valor_norm}")
                        else:
                            # Aceita chaves extras (por exemplo hora_documento) e adiciona ao dicionário
                            resultados_finais[chave] = valor_norm
                            print(f"    ℹ️  Chave adicional encontrada e salva: {chave}: {valor_norm}")
            
            documento.close()
            return resultados_finais
            
        except Exception as e:
            print(f"❌ Erro ao processar PDF: {str(e)}")
            return self._criar_resultado_vazio()

    def exibir_resultados(self, dados, arquivo):
        """Exibe os resultados de forma organizada (robusto a chaves ausentes)."""
        campos_nomes = {
            'data_documento': 'Data do Documento',
            'hora_documento': 'Hora do Documento',
            'tipo_combustível': 'Tipo de Combustível',
            'quantidade': 'Quantidade',
            'valor_unitario': 'Valor Unitário',
            'valor_total': 'Valor Total',
            'numero_documento': 'Número do Documento',
            'placa': 'Placa',
            'km': 'KM',
            'modelo_veiculo': 'Modelo do Veículo',
        }

        print(f"\n📋 RESULTADOS PARA: {arquivo}")
        print("=" * 60)

        dados_encontrados = []
        dados_nao_encontrados = []

        for campo, nome_exibicao in campos_nomes.items():
            valor = dados.get(campo)
            if valor is not None and str(valor).strip() and str(valor).lower() != 'null':
                print(f"✅ {nome_exibicao}: {valor}")
                dados_encontrados.append(nome_exibicao)
            else:
                print(f"❌ {nome_exibicao}: Não encontrado")
                dados_nao_encontrados.append(nome_exibicao)

        total_campos = len(campos_nomes)
        encontrados = len(dados_encontrados)
        print(f"\n📊 RESUMO: {encontrados}/{total_campos} campos extraídos")
        if dados_nao_encontrados:
            print(f"⚠️  Campos não encontrados: {', '.join(dados_nao_encontrados)}")

        campos_nomes = {
                'data_documento': 'Data do Documento',
                'hora_documento': 'Hora do Documento',
                'tipo_combustível': 'Tipo de Combustível',
                'quantidade': 'Quantidade',
                'valor_unitario': 'Valor Unitário',
                'valor_total': 'Valor Total',
                'numero_documento': 'Número do Documento',
                'placa': 'Placa',
                'km': 'KM',
                'modelo_veiculo': 'Modelo do Veículo'
            }
        
        print(f"\n📋 RESULTADOS PARA: {arquivo}")
        print("=" * 60)
        
        dados_encontrados = []
        dados_nao_encontrados = []
        
        for campo, nome_exibicao in campos_nomes.items():
            valor = dados[campo]
            if valor is not None and valor != "null" and str(valor).strip():
                print(f"✅ {nome_exibicao}: {valor}")
                dados_encontrados.append(nome_exibicao)
            else:
                print(f"❌ {nome_exibicao}: Não encontrado")
                dados_nao_encontrados.append(nome_exibicao)
        
        # Resumo
        total_campos = len(campos_nomes)
        encontrados = len(dados_encontrados)
        
        print(f"\n📊 RESUMO: {encontrados}/{total_campos} campos extraídos")
        
        if dados_nao_encontrados:
            print(f"⚠️  Campos não encontrados: {', '.join(dados_nao_encontrados)}")

        # Exibe alertas de incerteza
        self.exibir_alertas(dados, arquivo)
    
    def processar_todos_pdfs(self, pasta="tests"):
        """Processa todos os PDFs de uma pasta"""
        pasta_tests = Path(pasta)
        
        if not pasta_tests.exists():
            print(f"❌ Pasta '{pasta}' não encontrada!")
            return []
        
        arquivos_pdf = list(pasta_tests.glob("*.pdf"))
        
        if not arquivos_pdf:
            print(f"❌ Nenhum arquivo PDF encontrado na pasta '{pasta}'!")
            return []
        
        print(f"🎯 Encontrados {len(arquivos_pdf)} arquivo(s) PDF")
        print(f"🤖 Usando Grok Vision AI para extração de dados")
        
        todos_resultados = []
        
        for pdf in arquivos_pdf:
            resultado = self.processar_pdf(pdf)
            resultado['arquivo'] = pdf.name
            todos_resultados.append(resultado)
            
            self.exibir_resultados(resultado, pdf.name)
        
        # Salva resultados
        if todos_resultados:
            self.salvar_resultados(todos_resultados)
        
        return todos_resultados
    
    def salvar_resultados(self, resultados):
        """Salva os resultados em um arquivo CSV"""
        nome_arquivo = "dados_extraidos_grok.csv"
        
        with open(nome_arquivo, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['arquivo', 'data_documento', 'hora_documento', 'tipo_combustível', 'quantidade', 
                         'valor_unitario', 'valor_total', 'numero_documento', 'placa', 'km', 'modelo_veiculo']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for resultado in resultados:
                writer.writerow(resultado)
        
        print(f"\n💾 Resultados salvos em: {nome_arquivo}")

def main():
    print("🚀 EXTRATOR DE DADOS COM GROK VISION AI")
    print("=" * 60)
    print("🎯 Campos a extrair:")
    print("   • Data do Documento")
    print("   • Hora do Documento")
    print("   • Tipo de Combustível")
    print("   • Quantidade")
    print("   • Valor Unitário")
    print("   • Valor Total")
    print("   • Número do Documento (formato XXXX)")
    print("   • Placa")
    print("   • KM")
    print("   • Modelo do Veículo")
    print("=" * 60)
    
    # Verifica se há API key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ ERRO: Variável de ambiente OPENROUTER_API_KEY não encontrada!")
        print("💡 Para configurar:")
        print("   setx OPENROUTER_API_KEY \"sua_api_key_aqui\"")
        print("   (Reinicie o terminal após configurar)")
        return
    
    try:
        # Cria o extrator
        extractor = OpenRouterExtractor(api_key)
        
        # Processa todos os PDFs
        resultados = extractor.processar_todos_pdfs()
        
        if resultados:
            print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
            print(f"📁 {len(resultados)} arquivo(s) processado(s)")
            print(f"💾 Resultados salvos em dados_extraidos_grok.csv")
        else:
            print(f"\n⚠️  Nenhum arquivo foi processado com sucesso")
            
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")


def test_parsing_simulado():
    """Rotina de teste que simula uma resposta da API para validar parsing e normalização."""
    extractor = OpenRouterExtractor(api_key=os.getenv('OPENROUTER_API_KEY', 'test'))
    # Simula a resposta que o usuário mostrou
    resposta_simulada = {
        'numero_documento': '5708',
        'hora_documento': '00:00',
        'tipo_combustível': 'DS',
        'quantidade': '22,850',
        'valor_unitario': '5,890',
        'valor_total': '134,58',
        'placa': 'FEI6365',
        'km': '465625',
        'modelo_veiculo': 'AMB. RENAULT'
    }

    # Força a normalização/merge como faria processar_pdf
    resultados = extractor._criar_resultado_vazio()
    for k, v in resposta_simulada.items():
        if v is None or (isinstance(v, str) and v.strip().lower() == 'null'):
            continue
        resultados[k] = extractor._normalizar_valor(v)

    print('\n🔬 Resultado do teste simulado:')
    for k, v in resultados.items():
        print(f' - {k}: {v}')


if __name__ == "__main__":
    # Se a variável de ambiente TEST_SIM estiver definida, executa o teste simulado
    if os.getenv('TEST_SIM') == '1':
        test_parsing_simulado()
    else:
        main()

# Entrypoint já definido acima; evita execução duplicada