import os
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import platform
import io
import re
import csv
from typing import Dict, List, Optional

try:
    import easyocr
    EASYOCR_DISPONIVEL = True
except ImportError:
    EASYOCR_DISPONIVEL = False

try:
    import pytesseract
    TESSERACT_DISPONIVEL = True
except ImportError:
    TESSERACT_DISPONIVEL = False

class ExtratorGratuito:
    def __init__(self):
        """
        Inicializa o extrator gratuito usando OCR tradicional
        """
        self.ocr_engine = None
        self._configurar_ocr()
    
    def _configurar_ocr(self):
        """Configura o melhor OCR disponível"""
        if EASYOCR_DISPONIVEL:
            print("🔧 Configurando EasyOCR...")
            self.ocr_engine = easyocr.Reader(['pt', 'en'], gpu=False)
            self.tipo_ocr = "easyocr"
            print("✅ EasyOCR configurado com sucesso!")
        elif TESSERACT_DISPONIVEL:
            print("🔧 Configurando Tesseract...")
            if platform.system() == "Windows":
                # Tenta encontrar Tesseract no Windows
                caminhos_tesseract = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME'))
                ]
                
                for caminho in caminhos_tesseract:
                    if os.path.exists(caminho):
                        pytesseract.pytesseract.tesseract_cmd = caminho
                        break
            
            self.tipo_ocr = "tesseract"
            print("✅ Tesseract configurado!")
        else:
            raise Exception("❌ Nenhum OCR encontrado! Instale: pip install easyocr OU pip install pytesseract")
    
    def preprocessar_imagem(self, img):
        """Melhora a qualidade da imagem para OCR"""
        # Converte para escala de cinza
        if img.mode != 'L':
            img = img.convert('L')
        
        # Aumenta o contraste
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Aumenta a nitidez
        img = img.filter(ImageFilter.SHARPEN)
        
        # Redimensiona se muito pequena
        width, height = img.size
        if width < 800:
            new_width = 1200
            new_height = int((new_width * height) / width)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    def extrair_texto_ocr(self, img):
        """Extrai texto usando OCR"""
        try:
            img_processada = self.preprocessar_imagem(img)
            
            if self.tipo_ocr == "easyocr":
                resultados = self.ocr_engine.readtext(img_processada)
                texto = " ".join([item[1] for item in resultados if item[2] > 0.3])  # Confiança > 30%
            else:  # tesseract
                # Configuração para português
                config = '--psm 6 -l por'
                texto = pytesseract.image_to_string(img_processada, config=config)
            
            return texto.strip()
        except Exception as e:
            print(f"  ❌ Erro no OCR: {e}")
            return ""
    
    def extrair_dados_com_regex(self, texto):
        """Extrai dados específicos usando expressões regulares"""
        dados = {
            'numero_documento': None,
            'codigo_produto': None,
            'quantidade': None,
            'valor_unitario': None,
            'valor_total': None,
            'placa': None,
            'km': None,
            'modelo_veiculo': None
        }
        
        # Limpa o texto
        texto = re.sub(r'\s+', ' ', texto.upper())
        
        # Número do documento (formato 8XXX)
        match = re.search(r'\b8\d{3,4}\b', texto)
        if match:
            dados['numero_documento'] = match.group()
        
        # Código do produto (número de 4-6 dígitos)
        match = re.search(r'PRODUTO[:\s]*(\d{4,6})', texto)
        if match:
            dados['codigo_produto'] = match.group(1)
        
        # Quantidade (número seguido de L, LTS, LITROS, UN, etc.)
        match = re.search(r'(\d+[\.,]?\d*)\s*(?:L|LTS|LITROS?|UN|UNIDADES?)\b', texto)
        if match:
            dados['quantidade'] = match.group(1).replace(',', '.')
        
        # Valores monetários (R$ XX,XX)
        valores = re.findall(r'R?\$?\s*(\d+[\.,]\d{2})', texto)
        if len(valores) >= 2:
            # Assume que o primeiro é unitário e o último é total
            dados['valor_unitario'] = valores[0].replace(',', '.')
            dados['valor_total'] = valores[-1].replace(',', '.')
        elif len(valores) == 1:
            dados['valor_total'] = valores[0].replace(',', '.')
        
        # Placa (formatos ABC-1234 ou ABC1D23)
        match = re.search(r'\b[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}\b', texto)
        if match:
            dados['placa'] = match.group().replace(' ', '-')
        
        # KM (número seguido de KM)
        match = re.search(r'(\d+[\.,]?\d*)\s*KM', texto)
        if match:
            dados['km'] = match.group(1).replace(',', '.')
        
        # Modelo do veículo (palavras após MODELO, VEICULO, etc.)
        match = re.search(r'(?:MODELO|VEICULO|CARRO)[:\s]+([A-Z][A-Z\s]+?)(?:\s|$)', texto)
        if match:
            dados['modelo_veiculo'] = match.group(1).strip()
        
        return dados
    
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
    
    def processar_pdf(self, caminho_pdf):
        """
        Processa um PDF e extrai dados usando OCR gratuito
        
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
            resultados_finais = {
                'numero_documento': None,
                'codigo_produto': None,
                'quantidade': None,
                'valor_unitario': None,
                'valor_total': None,
                'placa': None,
                'km': None,
                'modelo_veiculo': None
            }
            
            for i in range(documento.page_count):
                print(f"📑 Processando página {i+1}/{documento.page_count}...")
                
                # Converte página para imagem
                pagina = documento[i]
                matriz = fitz.Matrix(3.0, 3.0)  # Alta resolução para OCR
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
                    print(f"  🔍 Analisando segmento {idx_seg+3} com {self.tipo_ocr.upper()}...")
                    
                    # Extrai texto do segmento
                    texto_extraido = self.extrair_texto_ocr(segmento)
                    
                    if texto_extraido:
                        print(f"    📝 Texto extraído: {texto_extraido[:100]}...")
                        
                        # Extrai dados específicos
                        dados_segmento = self.extrair_dados_com_regex(texto_extraido)
                        
                        # Combina resultados (prioriza dados não-nulos)
                        for campo, valor in dados_segmento.items():
                            if valor is not None and str(valor).strip():
                                if resultados_finais[campo] is None:
                                    resultados_finais[campo] = valor
                                    print(f"    ✅ {campo}: {valor}")
                    else:
                        print(f"    ❌ Nenhum texto extraído do segmento")
            
            documento.close()
            return resultados_finais
            
        except Exception as e:
            print(f"❌ Erro ao processar PDF: {str(e)}")
            return resultados_finais
    
    def exibir_resultados(self, dados, arquivo):
        """Exibe os resultados de forma organizada"""
        campos_nomes = {
            'numero_documento': 'Número do Documento',
            'codigo_produto': 'Código do Produto',
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
            if valor is not None and str(valor).strip():
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
        print(f"🔧 Usando {self.tipo_ocr.upper()} - 100% GRATUITO!")
        
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
        nome_arquivo = "dados_extraidos_gratuito.csv"
        
        with open(nome_arquivo, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['arquivo', 'numero_documento', 'codigo_produto', 'quantidade', 
                         'valor_unitario', 'valor_total', 'placa', 'km', 'modelo_veiculo']
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for resultado in resultados:
                writer.writerow(resultado)
        
        print(f"\n💾 Resultados salvos em: {nome_arquivo}")

def main():
    print("🆓 EXTRATOR DE DADOS - VERSÃO 100% GRATUITA")
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
    
    try:
        # Cria o extrator
        extractor = ExtratorGratuito()
        
        # Processa todos os PDFs
        resultados = extractor.processar_todos_pdfs()
        
        if resultados:
            print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
            print(f"📁 {len(resultados)} arquivo(s) processado(s)")
            print(f"💾 Resultados salvos em dados_extraidos_gratuito.csv")
            print(f"💰 CUSTO TOTAL: R$ 0,00 (100% gratuito!)")
        else:
            print(f"\n⚠️  Nenhum arquivo foi processado com sucesso")
            
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")

if __name__ == "__main__":
    main()