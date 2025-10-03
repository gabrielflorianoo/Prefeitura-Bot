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

        1. **Número do Documento**: Número do documento que geralmente inicia com 8 (ex de formato: 8XXX).
        2. **Data do documento**: Data em que o documento foi emitido (formato: DD/MM/AAAA).
        3. **Tipo de Combustível**: O tipo do combustível (ex: Gasolina, Etanol, Etanol S10, Diesel, etc).
        4. **Quantidade**: Quantidade do produto (em litros ou unidades).
        5. **Valor Unitário**: Preço por unidade (R$), ele sempre terá 3 casas decimais, use virgulas e pontos conforme o documento.
        6. **Valor Total**: Valor total da compra (R$), ele sempre terá 3 casas decimais, use virgulas e pontos conforme o documento.
        7. **Placa**: Placa do veículo (formato ABC-1234 ou ABC1D23).
        8. **KM**: Quilometragem do veículo.
        9. **Modelo do Veículo**: Modelo/marca do carro, ele está em frente ao "OBS" logo acima do "MOTOTISTA" e abaixo da placa e km, 
        
        se não encontrar, retorne null, não confundir com o nome do motorista que também está acima do modelo do carro.

        INSTRUÇÕES IMPORTANTES:
        - Retorne APENAS um JSON válido com os campos exatos.
        - Use null para campos não encontrados.
        - Para valores monetários, use apenas números e com formatação do Brasil (ex: "35.198,75").
        - Para o número do documento, ele fica localizado junto com o número de Série, este geralmente de número 1, geralmente no formato "8XXX" ou similar.
        - Para placa, mantenha o formato original.
        - Para número do documento, procure especificamente números que começam com 8 (formato 8XXX).
        - Seja preciso e extraia apenas o que está claramente visível.
        - Retorne nomes com todos os caracteres em maiúsculo.
        - Caso não tenha certeza sobre mais que 1 campo em 1 arquivo, retorne uma mensagem falando para o usuário conferir o documento.
        - Retorne junto o numero de certeza da IA como um todo para cada arquivo.

        Formato de resposta esperado:
        {
            "numero_documento": "valor ou null",
            "tipo_combustível": "valor ou null", 
            "quantidade": "valor ou null",
            "valor_unitario": "valor ou null",
            "valor_total": "valor ou null",
            "placa": "valor ou null",
            "km": "valor ou null",
            "modelo_veiculo": "valor ou null",
            "certeza_ia": "valor ou null"
        }
        """
        
        # Usando modelos de visão GRATUITOS/BARATOS disponíveis no OpenRouter
        modelos_disponiveis = [
            # "x-ai/grok-4-fast:free",
            # "meta-llama/llama-3.2-90b-vision-instruct",
            "mistralai/mistral-small-3.2-24b-instruct:free",
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
            'numero_documento': None,
            'tipo_combustível': None,
            'quantidade': None,
            'valor_unitario': None,
            'valor_total': None,
            'placa': None,
            'km': None,
            'modelo_veiculo': None
        }
    
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
                
                # Segmenta a imagem (3ª e 4ª partes onde estão os dados)
                segmentos = self.segmentar_imagem_horizontal(
                    img_original, 
                    num_segmentos=4, 
                    segmentos_desejados=[2, 3]
                )
                
                # Processa cada segmento
                for idx_seg, segmento in enumerate(segmentos):
                    print(f"  🔍 Analisando segmento {idx_seg+3}...")
                    
                    # Extrai dados do segmento usando Grok Vision
                    dados_segmento = self.extrair_dados_com_openrouter(segmento)
                    
                    # Combina resultados (prioriza dados não-nulos)
                    for campo, valor in dados_segmento.items():
                        if valor is not None and valor != "null" and str(valor).strip():
                            if resultados_finais[campo] is None:
                                resultados_finais[campo] = valor
                                print(f"    ✅ {campo}: {valor}")
            
            documento.close()
            return resultados_finais
            
        except Exception as e:
            print(f"❌ Erro ao processar PDF: {str(e)}")
            return self._criar_resultado_vazio()

    def exibir_alertas(self, dados, arquivo):
        """Exibe um alerta ao usuário, caso a IA fique com uma incerteza muito grande"""
        certeza = dados.get("certeza_ia")
        numero_documento = dados.get("numero_documento")
        try:
            certeza_val = float(str(certeza).replace(",", "."))
        except (TypeError, ValueError):
            certeza_val = None

        if certeza_val is not None and certeza_val < 0.8:
            print(f"\n⚠️  Atenção: A IA está com incerteza alta ({certeza}) para o arquivo '{arquivo}' (Número do Documento: {numero_documento}). Por favor, revise manualmente este arquivo.")

    def exibir_resultados(self, dados, arquivo):
        """Exibe os resultados de forma organizada"""
        campos_nomes = {
            'numero_documento': 'Número do Documento',
            'tipo_combustível': 'Tipo de Combustível',
            'quantidade': 'Quantidade',
            'valor_unitario': 'Valor Unitário',
            'valor_total': 'Valor Total',
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
            fieldnames = ['arquivo', 'numero_documento', 'tipo_combustível', 'quantidade', 
                         'valor_unitario', 'valor_total', 'placa', 'km', 'modelo_veiculo']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for resultado in resultados:
                writer.writerow(resultado)
        
        print(f"\n💾 Resultados salvos em: {nome_arquivo}")

def main():
    print("🚀 EXTRATOR DE DADOS COM GROK VISION AI")
    print("=" * 60)
    print("🎯 Campos a extrair:")
    print("   • Número do Documento (formato 8XXX)")
    print("   • Código do Produto") 
    print("   • Quantidade")
    print("   • Valor Unitário")
    print("   • Valor Total")
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

if __name__ == "__main__":
    main()