import os
import pytesseract
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import platform
import io
import cv2
import numpy as np

# Configuração do Tesseract para Windows
if platform.system() == "Windows":
    # Caminhos comuns do Tesseract no Windows
    possiveis_caminhos_tesseract = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe',
        r'C:\tools\tesseract\tesseract.exe'  # Caminho padrão do Chocolatey
    ]
    
    for caminho in possiveis_caminhos_tesseract:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            print(f"Tesseract encontrado em: {caminho}")
            break
    else:
        print("Aviso: Tesseract não encontrado nos caminhos padrão.")
        print("Certifique-se de que está instalado e no PATH do sistema.")

def segmentar_imagem_horizontal(img, num_segmentos=4, segmentos_desejados=[2, 3]):
    """
    Segmenta a imagem horizontalmente e retorna apenas os segmentos desejados
    
    Args:
        img: Imagem PIL
        num_segmentos: Número de segmentos horizontais (padrão: 4)
        segmentos_desejados: Lista com índices dos segmentos desejados (0-indexado, padrão: [2,3] = 3ª e 4ª partes)
    
    Returns:
        Lista de imagens PIL dos segmentos selecionados
    """
    width, height = img.size
    altura_segmento = height // num_segmentos
    
    segmentos = []
    
    print(f"  Segmentando imagem {width}x{height} em {num_segmentos} partes horizontais")
    print(f"  Altura de cada segmento: {altura_segmento}px")
    
    for i in segmentos_desejados:
        # Calcula as coordenadas do segmento
        y_inicio = i * altura_segmento
        y_fim = (i + 1) * altura_segmento if i < num_segmentos - 1 else height
        
        # Recorta o segmento
        segmento = img.crop((0, y_inicio, width, y_fim))
        segmentos.append(segmento)
        
        print(f"  Segmento {i+1}: y={y_inicio}-{y_fim} (altura: {y_fim-y_inicio}px)")
    
    return segmentos

def preprocessar_imagem(img, metodo='simples'):
    """
    Aplica filtros de pré-processamento na imagem para melhorar o OCR
    
    Args:
        img (PIL.Image): Imagem original
        metodo (str): Tipo de processamento ('completo', 'simples', 'agressivo')
    
    Returns:
        PIL.Image: Imagem processada
    """
    print(f"  Aplicando filtros de pré-processamento ({metodo})...")
    
    # Converte PIL para OpenCV
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # 1. Redimensiona se a imagem for muito pequena
    height, width = img_cv.shape[:2]
    if height < 1500 or width < 1500:
        scale_factor = max(1500/height, 1500/width)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        img_cv = cv2.resize(img_cv, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        print(f"    Redimensionada para: {new_width}x{new_height}")
    
    # 2. Converte para escala de cinza
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    if metodo == 'simples':
        # Processamento básico
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        final = threshold
        
    elif metodo == 'agressivo':
        # Processamento mais intenso
        # Desfoque bilateral para preservar bordas
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # CLAHE mais intenso
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(bilateral)
        
        # Threshold adaptativo
        threshold = cv2.adaptiveThreshold(
            contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 2
        )
        
        # Operações morfológicas mais agressivas
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opening = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        # Filtro mediano
        final = cv2.medianBlur(closing, 3)
        
    else:  # 'completo'
        # 3. Aplica desfoque gaussiano para reduzir ruído
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 4. Melhora o contraste usando CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced = clahe.apply(blurred)
        
        # 5. Aplica threshold adaptativo para binarização
        threshold = cv2.adaptiveThreshold(
            contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 6. Remove ruído com operações morfológicas
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel)
        
        # 7. Aplica filtro mediano para suavizar
        final = cv2.medianBlur(cleaned, 3)
    
    # Converte de volta para PIL
    img_final = Image.fromarray(final)
    
    # 8. Aplica sharpening usando PIL
    enhancer = ImageEnhance.Sharpness(img_final)
    img_final = enhancer.enhance(1.5)
    
    print("  Filtros aplicados com sucesso!")
    return img_final

def extrair_texto_pdf_ocr(caminho_pdf, usar_filtros_avancados=False):
    """
    Extrai texto de um arquivo PDF digitalizado usando PyMuPDF + Tesseract OCR
    
    Args:
        caminho_pdf (str): Caminho para o arquivo PDF
        usar_filtros_avancados (bool): Se True, aplica filtros avançados
    
    Returns:
        str: Texto extraído do PDF usando OCR
    """
    texto_completo = ""
    
    try:
        print(f"Abrindo PDF: {caminho_pdf}")
        
        # Abre o PDF com PyMuPDF
        documento = fitz.open(caminho_pdf)
        num_paginas = documento.page_count
        
        print(f"Número de páginas: {num_paginas}")
        
        # Processa cada página
        for i in range(num_paginas):
            print(f"Processando página {i+1}/{num_paginas}...")
            
            # Obtém a página
            pagina = documento[i]
            
            # Converte a página para imagem (matriz de pixels)
            # zoom = 2.0 para melhor qualidade (300 DPI aproximadamente)
            matriz = fitz.Matrix(2.0, 2.0)
            pix = pagina.get_pixmap(matrix=matriz)
            
            # Converte para PIL Image
            img_data = pix.tobytes("ppm")
            img_original = Image.open(io.BytesIO(img_data))
            
            print(f"  Imagem original: {img_original.size}")
            
            # Segmenta a imagem horizontalmente (pega apenas 3ª e 4ª partes)
            segmentos = segmentar_imagem_horizontal(img_original, num_segmentos=4, segmentos_desejados=[2, 3])
            
            # Processa cada segmento separadamente
            texto_segmentos = []
            
            for idx_seg, segmento in enumerate(segmentos):
                print(f"  Processando segmento {idx_seg+3}...")  # +3 porque são o 3º e 4º segmentos
                
                # Aplica OCR diretamente com processamento básico (mais rápido)
                try:
                    # Tenta primeiro com português, se não funcionar usa inglês
                    try:
                        config_tesseract = '--psm 6 -l por'
                        texto_segmento = pytesseract.image_to_string(segmento, config=config_tesseract)
                    except Exception:
                        print("    Português não disponível, usando inglês...")
                        config_tesseract = '--psm 6 -l eng'
                        texto_segmento = pytesseract.image_to_string(segmento, config=config_tesseract)
                    
                    # Se o resultado não for satisfatório ou filtros avançados estiverem ativados, aplica filtros
                    aplicar_filtros = usar_filtros_avancados or len(texto_segmento.strip()) < 50
                    
                    if aplicar_filtros:
                        if not usar_filtros_avancados:
                            print(f"    Pouco texto extraído ({len(texto_segmento.strip())} chars), aplicando filtros...")
                        else:
                            print(f"    Aplicando filtros avançados...")
                            
                        img_processada = preprocessar_imagem(segmento, 'simples')
                        
                        # Salva a imagem processada para debug
                        debug_filename = f"debug_pagina_{i+1}_segmento_{idx_seg+3}_filtrado.png"
                        img_processada.save(debug_filename)
                        
                        try:
                            texto_segmento = pytesseract.image_to_string(img_processada, config=config_tesseract)
                        except Exception:
                            config_tesseract = '--psm 6 -l eng'
                            texto_segmento = pytesseract.image_to_string(img_processada, config=config_tesseract)
                    
                    # Adiciona o resultado deste segmento
                    if texto_segmento.strip():
                        texto_segmentos.append(f"--- SEGMENTO {idx_seg+3} ---\n{texto_segmento.strip()}")
                        print(f"    Texto extraído: {len(texto_segmento.strip())} caracteres")
                    else:
                        print(f"    Nenhum texto reconhecível no segmento {idx_seg+3}")
                        
                except Exception as e:
                    print(f"    Erro ao processar segmento {idx_seg+3}: {str(e)}")
                    continue
            
            # Combina todos os segmentos desta página
            if texto_segmentos:
                texto_pagina = "\n\n".join(texto_segmentos)
                texto_completo += f"\n--- PÁGINA {i+1} ---\n"
                texto_completo += texto_pagina
                texto_completo += "\n"
            else:
                print(f"Aviso: Página {i+1} não contém texto reconhecível nos segmentos 3 e 4")
        
        # Fecha o documento
        documento.close()
    
    except Exception as e:
        print(f"Erro ao processar PDF {caminho_pdf}: {str(e)}")
        return None
    
    return texto_completo

def processar_primeiro_pdf(usar_filtros_avancados=False):
    """
    Processa o primeiro arquivo PDF encontrado na pasta tests usando PyMuPDF + OCR
    
    Args:
        usar_filtros_avancados (bool): Se True, aplica filtros avançados em todas as imagens
    """
    pasta_tests = Path("tests")
    
    if not pasta_tests.exists():
        print("Pasta 'tests' não encontrada!")
        return
    
    # Busca arquivos PDF na pasta tests
    arquivos_pdf = list(pasta_tests.glob("*.pdf"))
    
    if not arquivos_pdf:
        print("Nenhum arquivo PDF encontrado na pasta tests!")
        return
    
    # Pega o primeiro arquivo PDF
    primeiro_pdf = arquivos_pdf[0]
    print(f"Arquivo selecionado: {primeiro_pdf}")
    print(f"Modo de filtros avançados: {'Ativado' if usar_filtros_avancados else 'Desativado (mais rápido)'}")
    
    # Extrai o texto usando PyMuPDF + OCR
    texto_extraido = extrair_texto_pdf_ocr(primeiro_pdf, usar_filtros_avancados)
    
    if texto_extraido and texto_extraido.strip():
        print("\n" + "="*50)
        print("TEXTO EXTRAÍDO COM OCR:")
        print("="*50)
        print(texto_extraido)
        
        # Salva o texto em um arquivo
        nome_saida = f"texto_extraido_ocr_{primeiro_pdf.stem}.txt"
        with open(nome_saida, 'w', encoding='utf-8') as arquivo:
            arquivo.write(texto_extraido)
        
        print(f"\nTexto salvo em: {nome_saida}")
        print(f"Total de caracteres extraídos: {len(texto_extraido)}")
    else:
        print("Não foi possível extrair texto do PDF usando OCR")

def verificar_instalacao():
    """Verifica se Tesseract está instalado"""
    print("Verificando instalação...")
    
    # Verifica Tesseract
    try:
        versao_tesseract = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract instalado - Versão: {versao_tesseract}")
    except Exception as e:
        print(f"✗ Erro com Tesseract: {str(e)}")
        return False
    
    # Verifica PyMuPDF
    try:
        print(f"✓ PyMuPDF instalado - Versão: {fitz.version[0]}")
    except Exception as e:
        print(f"✗ Erro com PyMuPDF: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Extrator de Texto PDF com PyMuPDF + OCR")
    print("="*45)
    
    if verificar_instalacao():
        print("="*45)
        print("Opções de processamento:")
        print("1. Rápido (sem filtros) - Recomendado")
        print("2. Avançado (com filtros) - Mais lento, melhor qualidade")
        
        escolha = input("\nEscolha uma opção (1 ou 2): ").strip()
        
        usar_filtros = escolha == "2"
        
        print("="*45)
        processar_primeiro_pdf(usar_filtros)
    else:
        print("="*45)
        print("Erro: Dependências não instaladas corretamente!")
        print("\nPara instalar:")
        print("pip install PyMuPDF")
        print("choco install tesseract")