#!/bin/bash
# Script de configuración para el sistema MCP de clases
echo "🚀 Configurando sistema MCP para gestión de clases..."

# Verificar que Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Por favor instálalo primero."
    exit 1
fi

# Verificar que uv está instalado (recomendado para MCP servers)
if ! command -v uv &> /dev/null; then
    echo "📦 Instalando uv (gestor de paquetes Python rápido)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
    echo "✅ uv instalado correctamente"
fi

# Crear directorio del proyecto
mkdir -p mcp-class-system
cd mcp-class-system

# Crear entorno virtual de Python
echo "🐍 Configurando entorno Python..."
uv venv venv
source venv/bin/activate

# Crear requirements.txt si no existe
cat > requirements.txt << 'EOF'
anthropic>=0.18.0
gitpython>=3.1.40
python-dotenv>=1.0.0
requests>=2.31.0
markdown>=3.5.1
EOF

# Instalar dependencias de Python
echo "📦 Instalando dependencias Python..."
uv pip install -r requirements.txt

# Instalar mcp-server-git usando uv
echo "🔧 Instalando mcp-server-git..."
uv tool install mcp-server-git

# Crear estructura de directorios
mkdir -p clases
mkdir -p .github/workflows
mkdir -p config

# Configurar Git si no existe
if [ ! -d ".git" ]; then
    echo "🔧 Inicializando repositorio Git..."
    git init
    git branch -M main
    
    echo "📝 Configura tu repositorio remoto:"
    echo "git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git"
fi

# Crear configuración MCP para Claude Desktop
cat > config/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    },
    "filesystem": {
      "command": "uvx", 
      "args": ["mcp-server-filesystem", "--allowed-dir", "."]
    }
  }
}
EOF

# Crear configuración MCP para VS Code
cat > .vscode/mcp.json << 'EOF'
{
  "servers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    },
    "filesystem": {
      "command": "uvx",
      "args": ["mcp-server-filesystem", "--allowed-dir", "."]
    }
  }
}
EOF

# Crear archivo de configuración GitHub Actions
cat > .github/workflows/deploy.yml << 'EOF'
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    
    steps:
    - uses: actions/checkout@v4
        
    - name: Setup Pages
      uses: actions/configure-pages@v4
          
    - name: Upload artifact
      uses: actions/upload-pages-artifact@v3
      with:
        path: '.'
            
    - name: Deploy to GitHub Pages
      id: deployment
      uses: actions/deploy-pages@v4
EOF

# Crear archivo .env de ejemplo
cat > .env.example << 'EOF'
# Configuración del sistema MCP
ANTHROPIC_API_KEY=tu_api_key_aqui

# Configuración Git (opcional)
GIT_USER_NAME=Tu Nombre
GIT_USER_EMAIL=tu@email.com

# Configuración del proyecto
PROJECT_DIR=./clases
REPO_PATH=.
EOF

# Crear gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.pyc
*.pyo
venv/
.env

# Node
node_modules/
npm-debug.log*

# Sistema
.DS_Store
Thumbs.db

# Logs
*.log

# MCP
.mcp/
EOF

# Crear script de prueba MCP
cat > test_mcp.py << 'EOF'
#!/usr/bin/env python3
"""
Script de prueba para verificar la instalación MCP
"""
import os
import subprocess
import sys
from pathlib import Path

def test_uv_installation():
    """Verifica que uv esté instalado"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ uv está instalado:", result.stdout.strip())
            return True
        else:
            print("❌ Error con uv:", result.stderr)
            return False
    except FileNotFoundError:
        print("❌ uv no está instalado")
        return False

def test_mcp_git_server():
    """Verifica que mcp-server-git esté disponible"""
    try:
        result = subprocess.run(['uvx', 'mcp-server-git', '--help'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ mcp-server-git está disponible")
            return True
        else:
            print("❌ Error con mcp-server-git:", result.stderr)
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ mcp-server-git no está disponible")
        return False

def test_git_repo():
    """Verifica que estemos en un repositorio Git"""
    if Path('.git').exists():
        print("✅ Repositorio Git inicializado")
        return True
    else:
        print("❌ No es un repositorio Git")
        return False

def main():
    print("🧪 Probando configuración MCP...\n")
    
    tests = [
        test_uv_installation,
        test_mcp_git_server,
        test_git_repo
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    if all(results):
        print("🎉 ¡Todas las pruebas pasaron! Sistema MCP configurado correctamente.")
        return 0
    else:
        print("⚠️  Algunas pruebas fallaron. Revisa la configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x test_mcp.py

echo "✅ Sistema configurado correctamente!"
echo ""
echo "📋 Pasos siguientes:"
echo "1. Copia tu API key de Anthropic en .env:"
echo "   cp .env.example .env"
echo "   # Edita .env con tu API key"
echo ""
echo "2. Ejecuta las pruebas del sistema:"
echo "   python3 test_mcp.py"
echo ""
echo "3. Configura Claude Desktop (opcional):"
echo "   # Copia config/claude_desktop_config.json a tu directorio de configuración de Claude"
echo ""
echo "4. Para VS Code, asegúrate de tener la extensión MCP instalada"
echo ""
echo "5. Configura tu repositorio GitHub:"
echo "   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git"
echo ""
echo "6. Activa GitHub Pages en tu repositorio:"
echo "   Settings > Pages > Source: GitHub Actions"
echo ""
echo "🔧 Comandos útiles:"
echo "   # Probar mcp-server-git directamente:"
echo "   uvx mcp-server-git"
echo ""
echo "   # Debugging con MCP inspector:"
echo "   npx @modelcontextprotocol/inspector uvx mcp-server-git"
echo ""
echo "🎉 ¡Listo para usar!"