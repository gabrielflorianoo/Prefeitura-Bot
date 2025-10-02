import subprocess
import sys
import os
from pathlib import Path

def instalar_pyinstaller():
    """Instala PyInstaller se não estiver instalado"""
    try:
        import PyInstaller
        print("✅ PyInstaller já está instalado")
        return True
    except ImportError:
        print("📦 Instalando PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller instalado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar PyInstaller: {e}")
            return False

def encontrar_pyinstaller():
    """Encontra o caminho do PyInstaller"""
    # Primeiro tenta via módulo Python
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"], 
            capture_output=True, text=True, check=True
        )
        print(f"✅ PyInstaller encontrado via módulo Python")
        return [sys.executable, "-m", "PyInstaller"]
    except:
        pass
    
    # Tenta encontrar no PATH
    try:
        result = subprocess.run(
            ["pyinstaller", "--version"], 
            capture_output=True, text=True, check=True
        )
        print(f"✅ PyInstaller encontrado no PATH")
        return ["pyinstaller"]
    except:
        pass
    
    # Tenta encontrar no diretório do Python
    python_dir = Path(sys.executable).parent
    scripts_dir = python_dir / "Scripts"
    pyinstaller_exe = scripts_dir / "pyinstaller.exe"
    
    if pyinstaller_exe.exists():
        print(f"✅ PyInstaller encontrado em: {pyinstaller_exe}")
        return [str(pyinstaller_exe)]
    
    print("❌ PyInstaller não encontrado!")
    return None

def verificar_arquivos():
    """Verifica se os arquivos necessários existem"""
    arquivos_principais = [
        "extrator_deepseek.py",
        "extrator_gratuito.py", 
        "main.py"
    ]
    
    arquivo_encontrado = None
    for arquivo in arquivos_principais:
        if os.path.exists(arquivo):
            arquivo_encontrado = arquivo
            print(f"✅ Arquivo principal: {arquivo}")
            break
    
    if not arquivo_encontrado:
        print("❌ Nenhum arquivo Python principal encontrado!")
        print(f"📋 Procurados: {', '.join(arquivos_principais)}")
        return None
    
    # Verifica pasta tests
    if os.path.exists("tests"):
        print("✅ Pasta 'tests' encontrada")
    else:
        print("⚠️ Pasta 'tests' não encontrada - será criada vazia")
        os.makedirs("tests", exist_ok=True)
    
    return arquivo_encontrado

def criar_executavel():
    """Cria o executável"""
    print("🔨 Criando executável...")
    
    # Encontra PyInstaller
    pyinstaller_cmd = encontrar_pyinstaller()
    if not pyinstaller_cmd:
        print("❌ Não foi possível encontrar o PyInstaller")
        return False
    
    # Verifica arquivos
    arquivo_principal = verificar_arquivos()
    if not arquivo_principal:
        return False
    
    # Monta comando
    comando = pyinstaller_cmd + [
        "--onefile",  # Um único arquivo .exe
        "--console",  # Mantém console (mudei de --windowed)
        "--name=ExtratorPDF",  # Nome do executável
        "--add-data=tests;tests",  # Inclui pasta tests
        "--hidden-import=cv2",
        "--hidden-import=numpy", 
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=easyocr",
        "--hidden-import=requests",
        "--hidden-import=fitz",
        "--hidden-import=PyMuPDF",
        "--distpath=dist",
        "--workpath=build",
        arquivo_principal
    ]
    
    print(f"🔧 Executando: {' '.join(comando)}")
    
    try:
        # Executa o comando
        result = subprocess.run(comando, check=True, capture_output=True, text=True)
        
        print("✅ Executável criado com sucesso!")
        
        # Verifica se foi criado
        exe_path = "dist/ExtratorPDF.exe"
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📁 Localização: {exe_path}")
            print(f"📊 Tamanho: {size:.1f} MB")
        else:
            print("⚠️ Executável não encontrado no local esperado")
        
        print("\n🎯 Para usar em outro computador:")
        print("1. Copie o arquivo 'ExtratorPDF.exe' da pasta 'dist'")
        print("2. Copie a pasta 'tests' com os PDFs para junto do .exe")
        print("3. Execute o .exe no computador de destino")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao criar executável:")
        print(f"Código de saída: {e.returncode}")
        if e.stdout:
            print(f"Saída padrão:\n{e.stdout}")
        if e.stderr:
            print(f"Saída de erro:\n{e.stderr}")
        return False

def main():
    print("🚀 Construtor de Executável - Extrator PDF")
    print("="*50)
    
    print(f"📂 Diretório atual: {os.getcwd()}")
    print(f"🐍 Python: {sys.executable}")
    
    # Instala PyInstaller se necessário
    if not instalar_pyinstaller():
        return
    
    # Cria o executável
    sucesso = criar_executavel()
    
    print("\n" + "="*50)
    if sucesso:
        print("✨ Processo concluído com sucesso!")
        
        # Opção de limpeza
        limpar = input("\n🧹 Remover arquivos temporários (build/)? (s/n): ").lower()
        if limpar in ['s', 'sim', 'y', 'yes']:
            try:
                import shutil
                if os.path.exists("build"):
                    shutil.rmtree("build")
                    print("✅ Pasta 'build' removida")
            except Exception as e:
                print(f"⚠️ Erro ao remover 'build': {e}")
    else:
        print("❌ Falha na criação do executável!")
        print("\n💡 Possíveis soluções:")
        print("1. Reinstale PyInstaller: pip uninstall pyinstaller && pip install pyinstaller")
        print("2. Verifique se tem um arquivo Python principal no diretório")
        print("3. Execute como administrador se necessário")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operação cancelada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nPressione Enter para sair...")