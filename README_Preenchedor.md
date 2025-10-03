# 🤖 Preenchedor Automático de Dados

Automatiza o preenchimento de formulários usando dados extraídos de PDFs.

## 🚀 Instalação

```bash
pip install -r requirements_preenchedor.txt
```

## 📋 Como Usar

### 1️⃣ Preparação
1. Certifique-se que você tem um arquivo CSV com dados extraídos (ex: `dados_extraidos_grok.csv`)
2. Abra o aplicativo que você quer preencher
3. Posicione o cursor no **primeiro campo** da primeira linha

### 2️⃣ Execução
```bash
python preenchedor_automatico.py
```

### 3️⃣ Configuração
- **Modo Automático**: Preenche tudo sozinho com pausas de 3 segundos entre linhas
- **Modo Manual**: Espera você pressionar Enter para cada linha
- **Tempo de Espera**: Configura velocidade entre campos (0.1 a 5.0 segundos)

## 🎮 Controles

| Tecla | Função |
|-------|--------|
| `ESC` | Pausar (modo automático) |
| `SPACE` | Continuar (quando pausado) |
| `Q` | Sair (quando pausado) |
| `Mouse canto superior esquerdo` | Parada de emergência |

## 📊 Campos Preenchidos (em ordem)

1. **Número do Documento** → TAB
2. **Código do Produto** → TAB  
3. **Quantidade** → TAB
4. **Valor Unitário** → TAB
5. **Valor Total** → TAB
6. **Placa** → TAB
7. **KM** → TAB
8. **Modelo do Veículo** → ENTER (próxima linha)

## 🧪 Teste

Para testar antes de usar no app real:

```bash
python teste_preenchimento.py
```

Isso abre um aplicativo simulado onde você pode testar o preenchimento.

## ⚠️ Dicas Importantes

1. **Teste primeiro** com o app simulado
2. **Ajuste a velocidade** se o app for lento
3. **Use modo manual** para apps complexos
4. **Tenha um backup** dos dados importantes
5. **Clique no primeiro campo correto** antes de iniciar

## 🔧 Solução de Problemas

### Problema: Campos sendo preenchidos errados
**Solução**: Ajuste o tempo de espera para um valor maior

### Problema: App não responde ao TAB
**Solução**: Alguns apps usam setas. Modifique o código para usar `pyautogui.press('down')`

### Problema: Parada de emergência não funciona
**Solução**: Mova o mouse rapidamente para o canto superior esquerdo da tela

## 📁 Arquivos

- `preenchedor_automatico.py` - Script principal
- `teste_preenchimento.py` - App de teste
- `requirements_preenchedor.txt` - Dependências
- `dados_extraidos_*.csv` - Arquivos de entrada (gerados pelos extractors)

## 🔄 Fluxo Completo

```
PDF → Extrator → CSV → Preenchedor → App Preenchido
```

1. Use `extrator_gratuito.py` ou `extrator_deepseek.py` para extrair dados dos PDFs
2. Use `preenchedor_automatico.py` para preencher o app automaticamente
3. Verifique os dados preenchidos e faça ajustes se necessário

## 🛡️ Segurança

- **Failsafe ativado**: Mouse no canto superior esquerdo para parar
- **Modo manual disponível**: Controle total sobre cada linha
- **Backup recomendado**: Sempre tenha backup dos dados importantes
- **Teste primeiro**: Use o app simulado antes do app real