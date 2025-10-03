import os
import pytesseract
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import re
from typing import Dict, List, Optional
import csv
import io

# Configuração do Tesseract para Windows
if os.name == 'nt':  # Windows
    possiveis_caminhos_tesseract = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    
    for caminho in possiveis_caminhos_tesseract:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            break

def segmentar_imagem_horizontal(img, num_segmentos=4, segmentos_desejados=[2, 3]):
    """Segmenta a imagem horizontalmente"""
    width, height = img.size
    altura_segmento = height // num_segmentos
    
    segmentos = []
    for i in segmentos_desejados:
        y_inicio = i * altura_segmento
        y_fim = (i + 1) * altura_segmento if i < num_segmentos - 1 else height
        segmento = img.crop((0, y_inicio, width, y_fim))
        segmentos.append(segmento)
    
    return segmentos

def preprocessar_imagem_avancada(img):
    """Aplica filtros avançados para melhorar OCR"""
    # Converte para array numpy
    img_array = np.array(img)
    
    # Converte para escala de cinza se necessário
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # 1. Aumenta a resolução
    height, width = gray.shape
    if height < 1500:
        scale = 1500 / height
        new_width = int(width * scale)
        new_height = int(height * scale)
        gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    # 2. Melhora contraste com CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    
    # 3. Desfoque para reduzir ruído
    blurred = cv2.GaussianBlur(contrast, (1, 1), 0)
    
    # 4. Threshold adaptativo
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # 5. Operações morfológicas para limpar
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned

def extrair_texto_com_tesseract(imagem):
    """Extrai texto usando Tesseract otimizado"""
    try:
        # Tenta primeiro com português
        configs = [
            '--psm 6 -l por -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/ ',
            '--psm 8 -l por',
            '--psm 6 -l eng',
            '--psm 4 -l por'
        ]
        
        melhor_texto = ""
        maior_tamanho = 0
        
        for config in configs:
            try:
                if isinstance(imagem, np.ndarray):
                    img_pil = Image.fromarray(imagem)
                else:
                    img_pil = imagem
                
                texto = pytesseract.image_to_string(img_pil, config=config)
                
                if len(texto.strip()) > maior_tamanho:
                    maior_tamanho = len(texto.strip())
                    melhor_texto = texto
                    
            except Exception:
                continue
        
        return melhor_texto
    
    except Exception as e:
        print(f"    Erro no Tesseract: {str(e)}")
        return ""

def extrair_texto_completo(caminho_pdf):
    """Extrai texto do PDF com preprocessamento avançado"""
    texto_completo = ""
    
    try:
        documento = fitz.open(caminho_pdf)
        print(f"  Processando {documento.page_count} página(s)...")
        
        for i in range(documento.page_count):
            print(f"    Página {i+1}")
            pagina = documento[i]
            
            # Converte com alta resolução
            matriz = fitz.Matrix(3.0, 3.0)
            pix = pagina.get_pixmap(matrix=matriz)
            img_data = pix.tobytes("ppm")
            img_original = Image.open(io.BytesIO(img_data))
            
            # Segmenta
            segmentos = segmentar_imagem_horizontal(img_original, 4, [2, 3])
            
            for idx, segmento in enumerate(segmentos):
                print(f"      Segmento {idx+3}")
                
                # Aplica preprocessamento avançado
                img_processada = preprocessar_imagem_avancada(segmento)
                
                # Extrai texto
                texto = extrair_texto_com_tesseract(img_processada)
                
                if texto.strip():
                    texto_completo += texto + " "
                    print(f"        ✅ {len(texto.strip())} caracteres extraídos")
                else:
                    print(f"        ❌ Nenhum texto encontrado")
        
        documento.close()
        return texto_completo
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return ""

def extrair_informacoes_especificas(texto: str) -> Dict[str, Optional[str]]:
    """Extrai informações específicas com padrões melhorados"""
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
    
    # Normaliza texto
    texto_limpo = ' '.join(texto.upper().split())
    print(f"  📝 Analisando texto: {len(texto_limpo)} caracteres")
    
    # Padrões otimizados
    padroes = {
        'numero_serie': [
            r'SERIE\s*:?\s*(\d+)',
            r'FOLHA\s*:?\s*(\d+)',
            r'N\s*(?:°|º)?\s*SERIE\s*:?\s*(\d+)',
            r'(\d+)\s*(?=.*SERIE)'
        ],
        
        'codigo_produto': [
            r'(\d{8,12})',  # Códigos de 8-12 dígitos
            r'CODIGO\s*:?\s*(\d{4,})',
            r'COD\s*:?\s*(\d{4,})',
            r'(\d{6,})\s*(?=[A-Z])'  # Número longo antes de letras
        ],
        
        'quantidade': [
            r'QUANT\w*\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'QTD\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d+(?:[,\.]\d+)?)\s*(?:U\b|UNIT|UNID)',
            r'(\d+)\s*(?=.*(?:VALOR|PRECO))'
        ],
        
        'valor_unitario': [
            r'(?:VALOR\s*)?UNIT\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'V\s*(?:UNIT|U)\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'(\d+[,\.]\d{2})\s*(?=.*(?:\d+[,\.]\d{2}).*TOTAL)'
        ],
        
        'valor_total': [
            r'(?:VALOR\s*)?TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'TOTAL\s*:?\s*(\d+[,\.]\d{2})',
            r'(\d{2,3}[,\.]\d{2})\s*(?:$|FINAL|FIM)',
            r'R\$\s*(\d+[,\.]\d{2})\s*(?=.*TOTAL)'
        ],
        
        'placa': [
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d{4})',
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d[A-Z]\d{2})',
            r'([A-Z]{3}\s*\d{4})\s*(?![\d])',
            r'([A-Z]{3}\d{4})'
        ],
        
        'km': [
            r'KM\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d+(?:[,\.]\d+)?)\s*KM',
            r'QUILOMETRAGEM\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d{1,6})\s*(?=.*KM)'
        ]
    }
    
    # Busca cada campo
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
    
    # Modelo do veículo (busca próximo à placa)
    if informacoes['placa']:
        placa = re.escape(informacoes['placa'])
        padroes_modelo = [
            rf"PLACA\s*:?\s*{placa}\s*([A-Z][A-Z\s]+?)(?:\s|$)",
            rf"{placa}\s*([A-Z][A-Z\s]+?)(?:\s|$)"
        ]
        
        for padrao in padroes_modelo:
            match = re.search(padrao, texto_limpo)
            if match:
                modelo = match.group(1).strip().split()[0]  # Primeira palavra
                if len(modelo) > 2:
                    informacoes['modelo_veiculo'] = modelo
                    print(f"    ✅ modelo_veiculo: {modelo}")
                    break
    
    return informacoes

def processar_pdf(caminho_pdf):
    """Processa um PDF e extrai dados"""
    print(f"\n📄 {caminho_pdf.name}")
    print("-" * 50)
    
    # Extrai texto
    texto = extrair_texto_completo(caminho_pdf)
    
    if not texto.strip():
        print("❌ Nenhum texto extraído")
        return None
    
    # Extrai informações
    dados = extrair_informacoes_especificas(texto)
    
    # Conta resultados
    encontrados = sum(1 for v in dados.values() if v)
    total = len(dados)
    
    print(f"\n📊 {encontrados}/{total} informações encontradas")
    
    return dados

def main():
    """Função principal"""
    print("🔍 Extrator de Dados Otimizado")
    print("=" * 50)
    
    pasta = Path("tests")
    if not pasta.exists():
        print("❌ Pasta 'tests' não encontrada!")
        return
    
    pdfs = list(pasta.glob("*.pdf"))
    if not pdfs:
        print("❌ Nenhum PDF encontrado!")
        return
    
    print(f"📂 {len(pdfs)} arquivo(s) encontrado(s)")
    
    resultados = []
    for pdf in pdfs:
        resultado = processar_pdf(pdf)
        if resultado:
            resultado['arquivo'] = pdf.name
            resultados.append(resultado)
    
    # Salva resultados
    if resultados:
        with open('dados_extraidos_otimizado.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['arquivo'] + list(resultados[0].keys())[:-1])
            writer.writeheader()
            writer.writerows(resultados)
        
        print(f"\n💾 Resultados salvos em: dados_extraidos_otimizado.csv")
        print(f"🎉 {len(resultados)} arquivo(s) processado(s) com sucesso!")
    else:
        print("\n❌ Nenhum arquivo processado com sucesso")

if __name__ == "__main__":
    main()