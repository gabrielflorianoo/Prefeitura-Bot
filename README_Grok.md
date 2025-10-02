# 🤖 Extrator de Dados com Grok Vision AI

## 📋 Pré-requisitos

### 1. Instalar dependências
```powershell
pip install -r requirements_deepseek.txt
```

### 2. Obter API Key do OpenRouter
1. Acesse: https://openrouter.ai/
2. Crie uma conta
3. Obtenha sua API key
4. Adicione créditos (você paga apenas pelo uso)

### 3. Configurar API Key
```powershell
# Configure a variável de ambiente (Windows)
setx OPENROUTER_API_KEY "sua_api_key_aqui"

# Reinicie o terminal após configurar
```

## 🚀 Como usar

### Execução simples
```powershell
python extrator_deepseek.py
```

### Verificar se está configurado
```powershell
echo %OPENROUTER_API_KEY%
```

## 🤖 Modelo usado: Grok Vision

O script agora usa especificamente o **Grok Vision** da xAI:

- **Modelo**: `x-ai/grok-vision-beta`
- **Capacidades**: Análise avançada de imagens e documentos
- **Velocidade**: Processamento rápido
- **Precisão**: Otimizado para documentos estruturados

## 📊 O que o script extrai

O script usa Grok Vision AI para extrair automaticamente:

- **Número do Documento**: Número do documento que inicia com 8 (formato 8XXX)
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
├── extrator_deepseek.py         # Script principal (agora usa Grok Vision)
├── requirements_deepseek.txt    # Dependências
├── tests/                       # PDFs para processar
│   ├── arquivo1.pdf
│   ├── arquivo2.pdf
│   └── ...
└── dados_extraidos_grok.csv     # Resultados (gerado automaticamente)
```

## 🎯 Vantagens do Grok Vision

- **Especializado**: Desenvolvido pela xAI especificamente para análise de documentos
- **Rápido**: Processamento otimizado
- **Preciso**: Excelente reconhecimento de texto em imagens
- **Econômico**: Custo competitivo
- **Confiável**: Menos propenso a erros de API

## 💰 Custos aproximados

- **Grok Vision**: ~$0.01-0.03 por imagem
- **Pagamento por uso**: Sem mensalidades
- **Transparente**: Custos claros no painel OpenRouter

## 🔧 Resolução de problemas

### Erro: "API Key não encontrada"
```powershell
# Reconfigure a variável de ambiente
setx OPENROUTER_API_KEY "sua_api_key_aqui"
# Feche e abra novamente o terminal
```

### Erro de conexão
- Verifique sua conexão com a internet
- Confirme se a API key está válida
- Verifique se há créditos na conta OpenRouter

### Modelo não disponível
- Grok Vision pode estar temporariamente indisponível
- Verifique o status em: https://status.openrouter.ai/
- Entre em contato com suporte do OpenRouter se persistir

### Nenhum dado extraído
- Verifique se os PDFs estão na pasta `tests/`
- Confirme se as imagens têm boa qualidade
- O script segmenta automaticamente para focar na área relevante

## 💡 Dicas de uso

1. **Qualidade das imagens**: PDFs com melhor resolução geram melhores resultados
2. **Monitoramento**: Acompanhe os custos no painel do OpenRouter
3. **Backup**: O script salva automaticamente os resultados em CSV
4. **Otimização**: Grok Vision é otimizado para documentos fiscais

## 🎯 Exemplo de saída

```
🚀 EXTRATOR DE DADOS COM GROK VISION AI
============================================================
🎯 Campos a extrair:
   • Número do Documento (formato 8XXX)
   • Código do Produto
   • Quantidade
   • Valor Unitário
   • Valor Total
   • Placa
   • KM
   • Modelo do Veículo
============================================================

📄 Processando: Archivo_escaneado_20251002-1412.pdf
------------------------------------------------------------
📑 Processando página 1/1...
  📐 Imagem original: (1240, 1754)
  🔍 Analisando segmento 3...
  Enviando imagem para Grok Vision via OpenRouter...
  Resposta recebida do Grok, processando...
  ✅ Sucesso com Grok Vision!
    ✅ placa: ABC-1234
    ✅ valor_total: 198.75
    ✅ numero_serie: 1
    ✅ quantidade: 33.874

📋 RESULTADOS PARA: Archivo_escaneado_20251002-1412.pdf
============================================================
✅ Número do Documento: 8109
✅ Placa: ABC-1234
✅ Quantidade: 33.874
✅ Valor Total: 198.75
❌ Código do Produto: Não encontrado
❌ Valor Unitário: Não encontrado
❌ KM: Não encontrado
❌ Modelo do Veículo: Não encontrado

📊 RESUMO: 4/8 campos extraídos
💾 Resultados salvos em dados_extraidos_grok.csv

🎉 PROCESSAMENTO CONCLUÍDO!
📁 1 arquivo(s) processado(s)
💾 Resultados salvos em dados_extraidos_grok.csv
```

## 🚀 Configuração rápida

1. **Obtenha créditos no OpenRouter**
2. **Configure a API key:**
   ```powershell
   setx OPENROUTER_API_KEY "sua_api_key_aqui"
   ```
3. **Execute:**
   ```powershell
   python extrator_deepseek.py
   ```

O Grok Vision processará automaticamente todos os PDFs e salvará os resultados! 🎯