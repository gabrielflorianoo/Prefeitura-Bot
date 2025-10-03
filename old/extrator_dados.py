import os
import pytesseract
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageEnhance
import platform
import io
import cv2
import numpy as np
import re
from typing import Dict, List, Optional

# Configuração do Tesseract para Windows
if platform.system() == "Windows":
    possiveis_caminhos_tesseract = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe',
        r'C:\tools\tesseract\tesseract.exe'
    ]
    
    for caminho in possiveis_caminhos_tesseract:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            print(f"Tesseract encontrado em: {caminho}")
            break

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

def preprocessar_imagem(img):
    """Aplica filtros básicos para melhorar o OCR"""
    # Converte PIL para OpenCV
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # Converte para escala de cinza
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # Aplica threshold para binarização
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Converte de volta para PIL
    img_final = Image.fromarray(threshold)
    
    return img_final

def extrair_texto_completo(caminho_pdf):
    """Extrai todo o texto do PDF usando OCR"""
    texto_completo = ""
    
    try:
        documento = fitz.open(caminho_pdf)
        
        for i in range(documento.page_count):
            pagina = documento[i]
            
            # Converte página para imagem
            matriz = fitz.Matrix(2.0, 2.0)
            pix = pagina.get_pixmap(matrix=matriz)
            img_data = pix.tobytes("ppm")
            img_original = Image.open(io.BytesIO(img_data))
            
            # Segmenta a imagem (3ª e 4ª partes)
            segmentos = segmentar_imagem_horizontal(img_original, num_segmentos=4, segmentos_desejados=[2, 3])
            
            for segmento in segmentos:
                try:
                    # Aplica preprocessamento
                    img_processada = preprocessar_imagem(segmento)
                    
                    # Extrai texto com OCR
                    config_tesseract = '--psm 6 -l por'
                    try:
                        texto = pytesseract.image_to_string(img_processada, config=config_tesseract)
                    except:
                        config_tesseract = '--psm 6 -l eng'
                        texto = pytesseract.image_to_string(img_processada, config=config_tesseract)
                    
                    texto_completo += texto + "\n"
                    
                except Exception as e:
                    continue
        
        documento.close()
        return texto_completo
        
    except Exception as e:
        print(f"Erro ao extrair texto: {str(e)}")
        return ""

def extrair_informacoes_especificas(texto: str) -> Dict[str, Optional[str]]:
    """
    Extrai informações específicas do texto usando expressões regulares
    
    Args:
        texto (str): Texto extraído do PDF
    
    Returns:
        Dict com as informações encontradas
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
    
    # Limpa o texto removendo espaços extras e quebras de linha
    texto_limpo = ' '.join(texto.split())
    
    # Padrões para extrair informações
    padroes = {
        # Número de série - procura por "SERIE" seguido de números
        'numero_serie': [
            r'S[EÉ]RIE\s*:?\s*(\d+)',
            r'N[°º]?\s*S[EÉ]RIE\s*:?\s*(\d+)',
            r'FOLHA\s*(\d+)'
        ],
        
        # Código do produto - números longos que podem ser códigos
        'codigo_produto': [
            r'(\d{8,})',  # 8 ou mais dígitos seguidos
            r'C[ÓO]DIGO\s*:?\s*(\d+)',
            r'PRODUTO\s*:?\s*(\d+)'
        ],
        
        # Quantidade - procura por padrões de quantidade
        'quantidade': [
            r'QUANT\w*\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'QTD\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'QUANTIDADE\s*:?\s*(\d+(?:[,\.]\d+)?)'
        ],
        
        # Valor unitário - padrões de valores monetários
        'valor_unitario': [
            r'VALOR\s*UNIT\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'V\.?\s*UNIT\w*\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'UNIT[AÁ]RIO\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})'
        ],
        
        # Valor total - padrões de valores totais
        'valor_total': [
            r'VALOR\s*TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'V\.?\s*TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})',
            r'TOTAL\s*:?\s*R?\$?\s*(\d+[,\.]\d{2})'
        ],
        
        # Placa do veículo - padrões brasileiros
        'placa': [
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d{4})',
            r'PLACA\s*:?\s*([A-Z]{3}[-\s]?\d[A-Z]\d{2})',  # Mercosul
            r'([A-Z]{3}[-\s]?\d{4})',
            r'([A-Z]{3}[-\s]?\d[A-Z]\d{2})'
        ],
        
        # KM - quilometragem
        'km': [
            r'KM\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'QUILOMETRAGEM\s*:?\s*(\d+(?:[,\.]\d+)?)',
            r'(\d+(?:[,\.]\d+)?)\s*KM'
        ]
    }
    
    # Busca cada informação usando os padrões
    for campo, lista_padroes in padroes.items():
        for padrao in lista_padroes:
            match = re.search(padrao, texto_limpo, re.IGNORECASE)
            if match:
                informacoes[campo] = match.group(1).strip()
                break
    
    # Busca modelo do veículo (texto próximo à placa)
    if informacoes['placa']:
        # Procura por texto após a placa que pode ser o modelo
        padrao_modelo = rf"PLACA\s*:?\s*{re.escape(informacoes['placa'])}\s*([A-Z\s]+)"
        match_modelo = re.search(padrao_modelo, texto_limpo, re.IGNORECASE)
        if match_modelo:
            modelo_candidato = match_modelo.group(1).strip()
            # Filtra palavras que provavelmente são modelo de carro
            palavras_modelo = modelo_candidato.split()
            if palavras_modelo and len(palavras_modelo[0]) > 2:
                informacoes['modelo_veiculo'] = palavras_modelo[0]
    
    return informacoes

def processar_pdf_e_extrair_dados(caminho_pdf):
    """
    Processa um PDF e extrai as informações específicas solicitadas
    
    Args:
        caminho_pdf (str): Caminho para o arquivo PDF
    
    Returns:
        Dict com as informações extraídas
    """
    print(f"\nProcessando: {caminho_pdf}")
    print("-" * 50)
    
    # Extrai texto completo do PDF
    texto_completo = extrair_texto_completo(caminho_pdf)
    
    if not texto_completo.strip():
        print("❌ Não foi possível extrair texto do PDF")
        return None
    
    # Extrai informações específicas
    informacoes = extrair_informacoes_especificas(texto_completo)
    
    # Exibe os resultados
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
    
    dados_encontrados = []
    dados_nao_encontrados = []
    
    for campo, nome_exibicao in campos_nomes.items():
        valor = informacoes[campo]
        if valor:
            print(f"✅ {nome_exibicao}: {valor}")
            dados_encontrados.append(nome_exibicao)
        else:
            print(f"❌ {nome_exibicao}: Não encontrado")
            dados_nao_encontrados.append(nome_exibicao)
    
    # Mensagem resumo
    if dados_nao_encontrados:
        print(f"\n⚠️  Não foi possível extrair as seguintes informações:")
        for campo in dados_nao_encontrados:
            print(f"   - {campo}")
    
    if dados_encontrados:
        print(f"\n✅ Informações extraídas com sucesso: {len(dados_encontrados)}/{len(campos_nomes)}")
    else:
        print(f"\n❌ Não foi possível extrair nenhuma das informações solicitadas")
    
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
    
    print(f"📄 Encontrados {len(arquivos_pdf)} arquivo(s) PDF")
    
    todos_resultados = []
    
    for pdf in arquivos_pdf:
        resultado = processar_pdf_e_extrair_dados(pdf)
        if resultado:
            resultado['arquivo'] = pdf.name
            todos_resultados.append(resultado)
    
    # Salva resultados em arquivo
    if todos_resultados:
        salvar_resultados(todos_resultados)
    
    return todos_resultados

def salvar_resultados(resultados):
    """Salva os resultados em um arquivo CSV"""
    import csv
    
    nome_arquivo = "dados_extraidos.csv"
    
    with open(nome_arquivo, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['arquivo', 'numero_serie', 'codigo_produto', 'quantidade', 
                     'valor_unitario', 'valor_total', 'placa', 'km', 'modelo_veiculo']
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for resultado in resultados:
            writer.writerow(resultado)
    
    print(f"\n💾 Resultados salvos em: {nome_arquivo}")

if __name__ == "__main__":
    print("🔍 Extrator de Dados Específicos de PDFs")
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