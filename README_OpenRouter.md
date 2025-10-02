# 🤖 Extrator de Dados com OpenRouter AI

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

## 🤖 Modelos disponíveis

O script tentará usar os seguintes modelos na ordem de prioridade:

1. **GPT-4 Omni** (`openai/gpt-4o`) - Recomendado
2. **GPT-4 Vision** (`openai/gpt-4-vision-preview`)
3. **Claude 3.5 Sonnet** (`anthropic/claude-3-5-sonnet`)
4. **Claude 3 Opus** (`anthropic/claude-3-opus`)
5. **Gemini Pro Vision** (`google/gemini-pro-vision`)

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
├── extrator_deepseek.py             # Script principal (agora usa OpenRouter)
├── requirements_deepseek.txt        # Dependências
├── tests/                           # PDFs para processar
│   ├── arquivo1.pdf
│   ├── arquivo2.pdf
│   └── ...
└── dados_extraidos_openrouter.csv   # Resultados (gerado automaticamente)
```

## 🎯 Vantagens do OpenRouter

- **Múltiplos modelos**: Acesso a GPT-4, Claude, Gemini em uma única API
- **Fallback automático**: Se um modelo falhar, tenta o próximo
- **Custo otimizado**: Pague apenas pelo que usar
- **Alta precisão**: Usa os melhores modelos de visão disponíveis
- **Sem dependência**: Não precisa de contas separadas em cada provedor

## 💰 Custos aproximados

- **GPT-4 Vision**: ~$0.01-0.02 por imagem
- **Claude 3 Opus**: ~$0.02-0.04 por imagem
- **Claude 3.5 Sonnet**: ~$0.003-0.015 por imagem (recomendado)

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

### Nenhum modelo funcionou
- Verifique se tem créditos suficientes
- Alguns modelos podem estar temporariamente indisponíveis
- O script tentará automaticamente outros modelos

### Nenhum dado extraído
- Verifique se os PDFs estão na pasta `tests/`
- Confirme se as imagens têm boa qualidade
- O script segmenta automaticamente para focar na área relevante

## 💡 Dicas de uso

1. **Qualidade das imagens**: PDFs com melhor resolução geram melhores resultados
2. **Monitoramento**: Acompanhe os custos no painel do OpenRouter
3. **Backup**: O script salva automaticamente os resultados em CSV
4. **Modelos**: Claude 3.5 Sonnet oferece a melhor relação custo-benefício

## 🎯 Exemplo de saída

```
📄 Processando: Archivo_escaneado_20251002-1412.pdf
------------------------------------------------------------
📑 Processando página 1/1...
  📐 Imagem original: (1240, 1754)
  🔍 Analisando segmento 3...
  Enviando imagem para OpenRouter (openai/gpt-4o)...
  Resposta recebida, processando...
  ✅ Sucesso com modelo: openai/gpt-4o
    ✅ placa: ABC-1234
    ✅ valor_total: 198.75

📋 RESULTADOS PARA: Archivo_escaneado_20251002-1412.pdf
============================================================
✅ Placa: ABC-1234
✅ Valor Total: 198.75
❌ Nº Série: Não encontrado
...

📊 RESUMO: 2/8 campos extraídos
💾 Resultados salvos em dados_extraidos_openrouter.csv
```

## 🚀 Próximos passos

Após configurar a API key, execute:
```powershell
python extrator_deepseek.py
```

O script processará automaticamente todos os PDFs da pasta `tests/` e salvará os resultados!