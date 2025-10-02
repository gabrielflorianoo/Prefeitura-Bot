# 🤖 Extrator de Dados com DeepSeek AI

## 📋 Pré-requisitos

### 1. Instalar dependências
```powershell
pip install -r requirements_deepseek.txt
```

### 2. Obter API Key do DeepSeek
1. Acesse: https://platform.deepseek.com/
2. Crie uma conta
3. Obtenha sua API key

### 3. Configurar API Key
```powershell
# Configure a variável de ambiente (Windows)
setx DEEPSEEK_API_KEY "sua_api_key_aqui"

# Reinicie o terminal após configurar
```

## 🚀 Como usar

### Execução simples
```powershell
python extrator_deepseek.py
```

### Verificar se está configurado
```powershell
echo %DEEPSEEK_API_KEY%
```

## 📊 O que o script extrai

O script usa IA para extrair automaticamente:

- **Nº Série**: Número da série do documento
- **Código do Produto**: Código do combustível/produto
- **Quantidade**: Quantidade em litros
- **Valor Unitário**: Preço por litro (R$)
- **Valor Total**: Valor total da compra (R$)
- **Placa**: Placa do veículo
- **KM**: Quilometragem
- **Modelo do Veículo**: Marca/modelo do carro

## 📁 Estrutura de arquivos

```
Prefeitura Bot/
├── extrator_deepseek.py          # Script principal
├── requirements_deepseek.txt     # Dependências
├── tests/                        # PDFs para processar
│   ├── arquivo1.pdf
│   ├── arquivo2.pdf
│   └── ...
└── dados_extraidos_deepseek.csv  # Resultados (gerado automaticamente)
```

## 🎯 Vantagens do DeepSeek

- **Alta precisão**: IA treinada para entender documentos
- **Reconhecimento contextual**: Entende o layout e estrutura
- **Flexibilidade**: Adapta-se a diferentes formatos de documento
- **Sem necessidade de OCR tradicional**: Analisa diretamente a imagem

## 🔧 Resolução de problemas

### Erro: "API Key não encontrada"
```powershell
# Reconfigure a variável de ambiente
setx DEEPSEEK_API_KEY "sua_api_key_aqui"
# Feche e abra novamente o terminal
```

### Erro de conexão
- Verifique sua conexão com a internet
- Confirme se a API key está válida
- Verifique se há créditos na conta DeepSeek

### Nenhum dado extraído
- Verifique se os PDFs estão na pasta `tests/`
- Confirme se as imagens têm boa qualidade
- O script segmenta automaticamente para focar na área relevante

## 💡 Dicas de uso

1. **Qualidade das imagens**: PDFs com melhor resolução geram melhores resultados
2. **Organização**: Mantenha os PDFs organizados na pasta `tests/`
3. **Verificação**: Sempre verifique os resultados no arquivo CSV gerado
4. **Custo**: Monitore o uso da API DeepSeek (cada imagem consome tokens)

## 🎯 Exemplo de saída

```
📄 Processando: Archivo_escaneado_20251002-1412.pdf
------------------------------------------------------------
📑 Processando página 1/1...
  📐 Imagem original: (1240, 1754)
  🔍 Analisando segmento 3...
  Enviando imagem para DeepSeek...
  Resposta recebida, processando...
    ✅ placa: ABC-1234
    ✅ valor_total: 198.75

📋 RESULTADOS PARA: Archivo_escaneado_20251002-1412.pdf
============================================================
✅ Placa: ABC-1234
✅ Valor Total: 198.75
❌ Nº Série: Não encontrado
❌ Código do Produto: Não encontrado
...

📊 RESUMO: 2/8 campos extraídos
```