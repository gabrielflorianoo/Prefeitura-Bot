# Instruções de Instalação - Windows

## 1. Instalar as dependências Python
```
pip install -r requirements.txt
```

## 2. Instalar Tesseract OCR

### Opção A: Chocolatey (recomendado)
```
choco install tesseract
```

### Opção B: Download manual
1. Baixe o Tesseract do GitHub: https://github.com/UB-Mannheim/tesseract/wiki
2. Instale o arquivo .exe
3. Adicione o caminho ao PATH do sistema (geralmente: C:\Program Files\Tesseract-OCR)

### Opção C: Via Windows Package Manager
```
winget install UB-Mannheim.TesseractOCR
```

## 3. Instalar poppler (para pdf2image)

### Opção A: Chocolatey
```
choco install poppler
```

### Opção B: Download manual
1. Baixe poppler do: https://blog.alivate.com.au/poppler-windows/
2. Extraia para C:\poppler
3. Adicione C:\poppler\Library\bin ao PATH

## 4. Verificar instalação
```
tesseract --version
```

## 5. Executar o script
```
python main.py
```

## Solução de problemas

Se encontrar erro "tesseract is not installed", adicione ao código:
```python
# No Windows, pode ser necessário especificar o caminho do tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```