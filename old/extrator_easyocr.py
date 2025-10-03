import os
import easyocr
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import re
from typing import Dict, List, Optional
import csv
import io

def segmentar_imagem_horizontal(img, num_segmentos=4, segmentos_desejados=[2, 3]):
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

def preprocessar_imagem_para_ocr(img):
    """Aplica filtros para melhorar a qualidade do OCR"""
    # Converte PIL para numpy array
    img_array = np.array(img)
    
    # Se for colorida, converte para escala de cinza
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Aplica filtros para melhorar a qualidade
    # 1. Redimensiona se necessário (EasyOCR funciona melhor com imagens maiores)
    height, width = gray.shape
    if height < 1000 or width < 1000:
        scale_factor = max(1000/height, 1000/width)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # 2. Melhora o contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast_enhanced = clahe.apply(gray)
    
    # 3. Aplica desfoque gaussiano leve para reduzir ruído
    blurred = cv2.GaussianBlur(contrast_enhanced, (1, 1), 0)
    
    # 4. Binarização adaptativa
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return binary

def extrair_texto_easyocr(imagem_array, reader):
    """
    Extrai texto usando EasyOCR de forma mais robusta
    """
    try:
        # Converte para formato que o EasyOCR aceita
        if len(imagem_array.shape) == 2:  # Escala de cinza
            imagem_array = cv2.cvtColor(imagem_array, cv2.COLOR_GRAY2RGB)
        
        # EasyOCR com configurações mais conservadoras
        resultados = reader.readtext(imagem_array, 
                                   detail=0,  # Retorna apenas texto, sem coordenadas
                                   paragraph=False,  # Não agrupa em parágrafos
                                   width_ths=0.7,  # Threshold para largura
                                   height_ths=0.7)  # Threshold para altura
        
        # Junta todos os textos
        texto_completo = ' '.join(resultados) if resultados else ""
        return texto_completo
    
    except Exception as e:
        print(f"    Erro no EasyOCR: {str(e)}")
        return ""

def extrair_texto_completo(caminho_pdf, reader):
    """Extrai todo o texto do PDF usando EasyOCR"""
    texto_completo = ""
    
    try:
        documento = fitz.open(caminho_pdf)
        print(f"  Processando {documento.page_count} página(s)...")
        
        for i in range(documento.page_count):
            print(f"    Página {i+1}/{documento.page_count}")
            pagina = documento[i]
            
            # Converte página para imagem com alta resolução
            matriz = fitz.Matrix(3.0, 3.0)  # Maior resolução para melhor OCR
            pix = pagina.get_pixmap(matrix=matriz)
            img_data = pix.tobytes("ppm")
            img_original = Image.open(io.BytesIO(img_data))
            
            # Segmenta a imagem (3ª e 4ª partes)
            segmentos = segmentar_imagem_horizontal(img_original, num_segmentos=4, segmentos_desejados=[2, 3])
            
            for idx, segmento in enumerate(segmentos):
                print(f"      Segmento {idx+3}")
                
                # Aplica preprocessamento
                img_processada = preprocessar_imagem_para_ocr(segmento)
                
                # Extrai texto com EasyOCR
                texto_segmento = extrair_texto_easyocr(img_processada, reader)
                
                if texto_segmento.strip():
                    texto_completo += texto_segmento + " "
                    print(f"        Texto extraído: {len(texto_segmento)} caracteres")
                else:
                    print(f"        Nenhum texto encontrado")
        
        documento.close()
        return texto_completo
        
    except Exception as e:
        print(f"Erro ao extrair texto: {str(e)}")
        return ""

def extrair_informacoes_especificas(texto: str) -> Dict[str, Optional[str]]:
    """
    Extrai informações específicas do texto usando expressões regulares otimizadas
    """
    informacoes = {
        'numero_serie': None,
        'codigo_produto': None,
        'quantidade': None,
        'valor_unitario': None,
        'valor_total': None,
        'placa': None,
        'km': None,
        'modelo_veiculo': None
    }
    
    # Limpa e normaliza o texto
    texto_limpo = ' '.join(texto.upper().split())
    texto_limpo = re.sub(r'[^\w\s\.,\-:]', ' ', texto_limpo)  # Remove caracteres especiais
    
    print(f"  Texto para análise: {texto_limpo[:200]}...")
    
    # Padrões melhorados para EasyOCR
    padroes = {
        'numero_serie': [
            r'SERIE\s*:?\s*(\d+)',
            r'FOLHA\s*(\d+)',
            r'N\s*SERIE\s*(\d+)',
            r'(\d+)\s*SERIE'
        ],
        
        'codigo_produto': [
            r'(\d{8,})',  # Códigos longos
            r'CODIGO\s*:?\s*(\d+)',
            r'(\d{4,8})\s*(?=\w)'  # Números de 4-8 dígitos antes de letras
        ],
        
        'quantidade': [
            r'QUANT\w*\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'QTD\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d+(?:[,\.]\d+)?)\s*U\b'  # Número seguido de "U" (unidade)
        ],
        
        'valor_unitario': [
            r'VALOR\s*UNIT\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'V\s*UNIT\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'(\d+[,\.]\d{2})\s*(?=\d+[,\.]\d{2}\s*(?:TOTAL|T))'  # Valor antes do total
        ],
        
        'valor_total': [
            r'VALOR\s*TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'(\d{2,3}[,\.]\d{2})\s*(?:$|\s|TOTAL)'
        ],
        
        'placa': [
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d{4})',
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d[A-Z]\d{2})',  # Mercosul
            r'([A-Z]{3}\s*\d{4})',
            r'([A-Z]{3}\s*\d[A-Z]\d{2})'
        ],
        
        'km': [
            r'KM\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d+(?:[,\.]\d+)?)\s*KM',
            r'QUILOMETRAGEM\s*:?\s*(\d+(?:[,\.]\d+)?)'
        ]
    }
    
    # Extrai cada informação
    for campo, lista_padroes in padroes.items():
        for padrao in lista_padroes:
            match = re.search(padrao, texto_limpo)
            if match:
                valor = match.group(1).strip()
                informacoes[campo] = valor
                print(f"    ✅ {campo}: {valor}")
                break
        
        if not informacoes[campo]:
            print(f"    ❌ {campo}: Não encontrado")
    
    # Busca modelo do veículo próximo à placa
    if informacoes['placa']:
        # Procura texto após placa
        placa_escapada = re.escape(informacoes['placa'])
        padrao_modelo = rf"PLACA\s*:?\s*{placa_escapada}\s*([A-Z]\w+)"
        match_modelo = re.search(padrao_modelo, texto_limpo)
        if match_modelo:
            informacoes['modelo_veiculo'] = match_modelo.group(1)
            print(f"    ✅ modelo_veiculo: {match_modelo.group(1)}")
        else:
            print(f"    ❌ modelo_veiculo: Não encontrado")
    
    return informacoes

def processar_pdf_e_extrair_dados(caminho_pdf, reader):
    """Processa um PDF e extrai as informações específicas"""
    print(f"\n📄 Processando: {caminho_pdf.name}")
    print("-" * 60)
    
    # Extrai texto completo do PDF
    texto_completo = extrair_texto_completo(caminho_pdf, reader)
    
    if not texto_completo.strip():
        print("❌ Não foi possível extrair texto do PDF")
        return None
    
    print(f"  Texto total extraído: {len(texto_completo)} caracteres")
    
    # Extrai informações específicas
    informacoes = extrair_informacoes_especificas(texto_completo)
    
    # Conta sucessos e falhas
    campos_nomes = {
        'numero_serie': 'Nº Série',
        'codigo_produto': 'Código do Produto',
        'quantidade': 'Quantidade',
        'valor_unitario': 'Valor Unitário',
        'valor_total': 'Valor Total',
        'placa': 'Placa',
        'km': 'KM',
        'modelo_veiculo': 'Modelo do Veículo'
    }
    
    encontrados = sum(1 for v in informacoes.values() if v)
    total = len(informacoes)
    
    print(f"\n📊 Resultado: {encontrados}/{total} informações encontradas")
    
    if encontrados < total:
        nao_encontrados = [nome for campo, nome in campos_nomes.items() if not informacoes[campo]]
        print(f"⚠️  Não foi possível extrair: {', '.join(nao_encontrados)}")
    
    return informacoes

def processar_todos_pdfs():
    """Processa todos os PDFs da pasta tests"""
    pasta_tests = Path("tests")
    
    if not pasta_tests.exists():
        print("❌ Pasta 'tests' não encontrada!")
        return
    
    arquivos_pdf = list(pasta_tests.glob("*.pdf"))
    
    if not arquivos_pdf:
        print("❌ Nenhum arquivo PDF encontrado na pasta tests!")
        return
    
    print(f"📂 Encontrados {len(arquivos_pdf)} arquivo(s) PDF")
    
    # Inicializa EasyOCR (português e inglês)
    print("🚀 Inicializando EasyOCR (pode demorar na primeira vez)...")
    try:
        reader = easyocr.Reader(['pt', 'en'], gpu=False)  # Força uso da CPU
        print("✅ EasyOCR inicializado!")
    except Exception as e:
        print(f"❌ Erro ao inicializar EasyOCR: {str(e)}")
        print("Tentando apenas com inglês...")
        try:
            reader = easyocr.Reader(['en'], gpu=False)
            print("✅ EasyOCR inicializado com inglês!")
        except Exception as e2:
            print(f"❌ Erro crítico: {str(e2)}")
            return []
    
    todos_resultados = []
    
    for pdf in arquivos_pdf:
        resultado = processar_pdf_e_extrair_dados(pdf, reader)
        if resultado:
            resultado['arquivo'] = pdf.name
            todos_resultados.append(resultado)
    
    # Salva resultados
    if todos_resultados:
        salvar_resultados(todos_resultados)
    
    return todos_resultados

def salvar_resultados(resultados):
    """Salva os resultados em um arquivo CSV"""
    nome_arquivo = "dados_extraidos_easyocr.csv"
    
    fieldnames = ['arquivo', 'numero_serie', 'codigo_produto', 'quantidade', 
                 'valor_unitario', 'valor_total', 'placa', 'km', 'modelo_veiculo']
    
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for resultado in resultados:
            writer.writerow(resultado)
    
    print(f"\n💾 Resultados salvos em: {nome_arquivo}")

if __name__ == "__main__":
    print("🔍 Extrator de Dados com EasyOCR")
    print("=" * 50)
    print("Campos a extrair:")
    print("• Nº Série")
    print("• Código do Produto") 
    print("• Quantidade")
    print("• Valor Unitário")
    print("• Valor Total")
    print("• Placa")
    print("• KM")
    print("• Modelo do Veículo")
    print("=" * 50)
    
    try:
        resultados = processar_todos_pdfs()
        
        if resultados:
            print(f"\n🎉 Processamento concluído! {len(resultados)} arquivo(s) processado(s)")
        else:
            print(f"\n⚠️  Nenhum arquivo foi processado com sucesso")
            
    except Exception as e:
        print(f"\n❌ Erro durante o processamento: {str(e)}")
        import traceback
        traceback.print_exc()