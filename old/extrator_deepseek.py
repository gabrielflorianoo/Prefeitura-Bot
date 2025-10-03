import os
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
import platform
import io
import base64
import json
import requests
from typing import Dict, List, Optional, Tuple
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
    
    def extrair_dados_com_openrouter(self, images) -> Dict[str, Optional[str]]:
        """
        Envia várias imagens em UMA única requisição para a API, anotando qual imagem corresponde a qual região.

        Args:
            images: pode ser:
                - uma lista de tuplas (label, PIL.Image)
                - uma lista de PIL.Image (assume ordem padrão)
                - um único PIL.Image (compatibilidade com versões anteriores)

        Retorna:
            Dicionário com os dados extraídos (conforme contrato do prompt)
        """
        # Normaliza o parâmetro para uma lista de (label, Image)
        imagens_list: List[Tuple[str, Image.Image]] = []

        if isinstance(images, Image.Image):
            imagens_list = [("imagem_0", images)]
        elif isinstance(images, list):
            # Lista de PIL.Image ou lista de tuplas
            if images and isinstance(images[0], tuple) and len(images[0]) == 2:
                imagens_list = images  # já é (label, Image)
            else:
                # assume lista de imagens sem labels
                imagens_list = [(f"imagem_{i}", img) for i, img in enumerate(images)]
        else:
            print("  Parâmetro 'images' em formato inesperado. Retornando resultado vazio.")
            return self._criar_resultado_vazio()

        # Prompt base para instruções e formato de resposta
        prompt_base = """
        Analise atentamente as imagens anexadas (cada imagem representa uma porção do mesmo documento).
        As imagens estão etiquetadas; respeite a correspondência entre etiqueta e imagem.

        EXTRAI APENAS E EXATAMENTE os campos JSON solicitados (use null quando não encontrar):
        {
            "data_documento": "DD/MM/AAAA ou null",
            "hora_saida": "HH:MM ou null",
            "tipo_combustível": "valor ou null",
            "quantidade": "valor ou null",
            "valor_unitario": "valor ou null",
            "valor_total": "valor ou null",
            "numero_documento": "valor ou null",
            "placa": "valor ou null",
            "km": "valor ou null",
            "modelo_veiculo": "valor ou null"
        }

        REGRAS IMPORTANTES:
        - A primeira imagem corresponde à etiqueta informada primeiro, a segunda à etiqueta informada segundo, e assim por diante.
        - Para campos numéricos e monetários mantenha a formatação do documento (vírgula para decimais, ponto para milhares quando presente).
        - Se houver dúvida sobre mais de 1 campo, indique claramente na resposta que o usuário deve conferir.
        - Para o tipo de combustivel use G para Gasolina, D para Diesel S500 e DS para Diesel S10, caso encontre algum outro use apenas a primeira letra.
        - Sempre retorne nomes em MAIÚSCULAS e do mesmo jeito que está no documento.
        """

        # Constrói uma descrição curta das etiquetas para enviar antes das imagens
        mapping_lines = []
        for idx, (label, _) in enumerate(imagens_list, start=1):
            mapping_lines.append(f"Imagem {idx}: {label}")
        mapping_text = "\n".join(mapping_lines)

        prompt = prompt_base + "\n\nEtiquetas das imagens:\n" + mapping_text

        # Converte imagens para base64 e monta o conteúdo com texto + imagens
        content_items = [
            {"type": "text", "text": prompt}
        ]

        for idx, (label, img) in enumerate(imagens_list):
            b64 = self.image_to_base64(img)
            content_items.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
                "text": f"{label}"
            })

        modelos_disponiveis = [
            # "meta-llama/llama-3.2-90b-vision-instruct",
            "mistralai/mistral-small-3.2-24b-instruct:free",
            "moonshotai/kimi-vl-a3b-thinking:free",
        ]

        for modelo in modelos_disponiveis:
            try:
                payload = {
                    "model": modelo,
                    "messages": [
                        {"role": "user", "content": content_items}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.1
                }

                print(f"  Enviando {len(imagens_list)} imagens para OpenRouter ({modelo}) em UMA requisição...")
                response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=120)

                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        print(f"  Resposta da API recebida com sucesso usando {modelo}!")

                        # Extrai JSON da resposta
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
                            print("  Não foi encontrado JSON válido na resposta")
                            continue
                    else:
                        print("  Resposta sem choices válidos")
                        continue
                else:
                    print(f"  Erro HTTP {response.status_code} com {modelo}: {response.text}")
                    if response.status_code == 404:
                        print(f"  Modelo {modelo} não disponível, tentando próximo...")
                    continue
            except requests.exceptions.RequestException as e:
                print(f"  Erro de conexão com {modelo}: {e}")
                continue
            except Exception as e:
                print(f"  Erro inesperado com {modelo}: {e}")
                continue

        print("  ❌ Todos os modelos falharam. Retornando resultado vazio.")
        return self._criar_resultado_vazio()
    
    def _criar_resultado_vazio(self):
        """Cria um dicionário com todos os campos como None"""
        return {
            'data_documento': None,
            'hora_saida': None,
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

                # Envia TODAS as regiões em UMA única requisição (etiquetando cada imagem)
                labeled_images = []
                for idx_reg, segmento in enumerate(regioes):
                    label = labels[idx_reg] if idx_reg < len(labels) else f"regiao_{idx_reg}"
                    labeled_images.append((label, segmento))

                dados_pagina = self.extrair_dados_com_openrouter(labeled_images)

                # Combina resultados (prioriza dados não-nulos e normaliza valores)
                for campo, valor in dados_pagina.items():
                    chave = campo if isinstance(campo, str) else str(campo)
                    if valor is None or (isinstance(valor, str) and valor.strip().lower() == 'null'):
                        continue

                    try:
                        valor_norm = self._normalizar_valor(valor)
                    except Exception:
                        valor_norm = valor

                    if chave in resultados_finais:
                        if resultados_finais[chave] is None:
                            resultados_finais[chave] = valor_norm
                            print(f"    ✅ {chave}: {valor_norm}")
                    else:
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
            'hora_saida': 'Hora da Saida',
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
                'hora_saida': 'Hora da Saida',
                'tipo_combustível': 'Tipo de Combustível',
                'quantidade': 'Quantidade',
                'valor_unitario': 'Valor Unitário',
                'valor_total': 'Valor Total',
                'numero_documento': 'Número do Documento',
                'placa': 'Placa',
                'km': 'KM',
                'modelo_veiculo': 'Modelo do Veículo'
            }

        # Mostra as imagens recortadas dos campos não encontrados
        # Primeiro tenta usar IPython.display.display (se estiver disponível no ambiente)
        try:
            from IPython.display import display as display_fn
        except Exception:
            display_fn = None

        # Tenta recortar novamente as regiões do PDF para exibir
        try:
            path_arquivo = Path("tests") / arquivo
            documento = fitz.open(path_arquivo)
            pagina = documento[0]
            matriz = fitz.Matrix(2.0, 2.0)
            pix = pagina.get_pixmap(matrix=matriz)
            img_data = pix.tobytes("ppm")
            img_original = Image.open(io.BytesIO(img_data))
            regioes = self.recortar_regioes_fixas(img_original)
            labels = ['Número do Documento', 'Data e Hora', 'Corpo do Documento', 'Placa/KM/Modelo']

            print("\n🖼️ Exibindo imagens dos campos não encontrados:")

            for idx, nome_exibicao in enumerate(campos_nomes.values()):
                if nome_exibicao in dados_nao_encontrados and idx < len(regioes):
                    img = regioes[idx]
                    print(f"🖼️ {nome_exibicao}:")
                    try:
                        if display_fn is not None:
                            # Notebook / IPython: exibe inline
                            display_fn(img)
                        else:
                            # Salva imagem temporária e abre com o visualizador padrão do SO
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                tmp_path = tmp.name
                                img.save(tmp_path, format='PNG')
                            print(f"  → Imagem salva em: {tmp_path}")
                            try:
                                if platform.system().lower().startswith('windows'):
                                    os.startfile(tmp_path)
                                else:
                                    opener = 'xdg-open' if platform.system().lower().startswith('linux') else 'open'
                                    os.system(f"{opener} \"{tmp_path}\"")
                            except Exception as e:
                                print(f"⚠️ Não foi possível abrir a imagem com o visualizador do sistema: {e}")
                    except Exception as e:
                        print(f"⚠️ Erro ao exibir a imagem: {e}")

            documento.close()
        except Exception as e:
            print(f"⚠️ Não foi possível exibir imagens: {e}")
    
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
            fieldnames = ['arquivo', 'data_documento', 'hora_saida', 'tipo_combustível', 'quantidade', 
                         'valor_unitario', 'valor_total', 'numero_documento', 'placa', 'km', 'modelo_veiculo']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for resultado in resultados:
                writer.writerow(resultado)
        
        print(f"\n💾 Resultados salvos em: {nome_arquivo}")

def main():
    print("🚀 EXTRATOR DE DADOS COM META LLAMA VISION AI")
    print("=" * 60)
    print("🎯 Campos a extrair:")
    print("   • Data do Documento")
    print("   • Hora da Saida")
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
        'hora_saida': '00:00',
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