#!/bin/bash

# Script de configuración para el sistema MCP de clases
echo "🚀 Configurando sistema MCP para gestión de clases..."

# Verificar que Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js no está instalado. Por favor instálalo primero."
    echo "   Puedes instalarlo desde: https://nodejs.org/"
    exit 1
fi

# Verificar que Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 no está instalado. Por favor instálalo primero."
    exit 1
fi

# Verificar que uv está instalado (recomendado para MCP)
if ! command -v uv &> /dev/null; then
    echo "📦 Instalando uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    source $HOME/.cargo/env
fi

# Crear directorio del proyecto
echo "📁 Creando estructura del proyecto..."
mkdir -p mcp-class-system
cd mcp-class-system

# Instalar servidores MCP
echo "📦 Instalando servidores MCP..."

# Servidor Filesystem (oficial)
npm install -g @modelcontextprotocol/server-filesystem

# Servidor Git (no oficial - usando pip)
echo "🔧 Instalando mcp-server-git..."
pip install mcp-server-git

# Crear entorno virtual de Python
echo "🐍 Configurando entorno Python..."
python3 -m venv venv
source venv/bin/activate

# Crear requirements.txt
cat > requirements.txt << 'EOF'
anthropic>=0.34.0
mcp>=1.0.0
mcp-server-git>=0.1.0
pathlib
asyncio-extras
EOF

# Instalar dependencias de Python
pip install -r requirements.txt

# Crear estructura de directorios
mkdir -p clases
mkdir -p .github/workflows

# Configurar Git si no existe
if [ ! -d ".git" ]; then
    echo "🔧 Inicializando repositorio Git..."
    git init
    git branch -M main
    
    echo "📝 Configura tu repositorio remoto ejecutando:"
    echo "git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git"
fi

# Crear archivo de configuración MCP para Claude Desktop
echo "⚙️ Creando configuración para Claude Desktop..."
mkdir -p ~/.config/claude/

cat > claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "./clases"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"]
    }
  }
}
EOF

echo "📋 Para configurar Claude Desktop, copia el contenido de claude_desktop_config.json"
echo "   al archivo de configuración de Claude en tu sistema."

# Crear archivo de configuración GitHub Actions
cat > .github/workflows/deploy.yml << 'EOF'
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v4
      
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
ANTHROPIC_API_KEY=tu_api_key_de_anthropic_aqui

# Configuración Git (opcional)
GIT_USER_NAME=Tu Nombre
GIT_USER_EMAIL=tu@email.com
EOF

# Crear gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
venv/
env/
ENV/

# Configuración sensible
.env

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Sistema
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Temporal
.tmp/
temp/
EOF

# Crear README.md
cat > README.md << 'EOF'
# 📚 Sistema MCP para Gestión de Clases

Sistema integrado que combina Claude AI con servidores MCP (Model Context Protocol) para gestionar horarios, notas de clase y publicación automática en GitHub Pages.

## 🚀 Características

- ✅ Gestión automática de horarios de clase
- 📝 Creación y organización de notas
- 🔄 Integración con Git para versionado
- 🌐 Publicación automática en GitHub Pages
- 🤖 Interfaz conversacional con Claude AI

## 📦 Instalación

1. Clona este repositorio
2. Ejecuta el script de configuración:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

## ⚙️ Configuración

1. **API Key de Anthropic:**
   ```bash
   cp .env.example .env
   # Edita .env y agrega tu API key
   ```

2. **Repositorio GitHub:**
   ```bash
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   ```

3. **GitHub Pages:**
   - Ve a Settings > Pages en tu repositorio
   - Selecciona "GitHub Actions" como source

## 🎯 Uso

```bash
# Activar entorno virtual
source venv/bin/activate

# Configurar API key
export ANTHROPIC_API_KEY=tu_api_key

# Ejecutar el sistema
python mcp_class_bot.py
```

## 📋 Comandos Disponibles

- `clases` - Ver clases del día
- `notas [materia]` - Crear notas para una materia
- `publicar` - Subir cambios a GitHub
- `deploy` - Desplegar en GitHub Pages

## 🛠️ Tecnologías

- Python 3.8+
- MCP (Model Context Protocol)
- Claude AI API
- GitHub Actions
- Git

## 📄 Licencia

MIT License
EOF

# Crear un horario de ejemplo
cat > horario_clases.json << 'EOF'
{
  "lunes": ["Matemáticas", "Historia", "Ciencias"],
  "martes": ["Literatura", "Química", "Educación Física"],
  "miércoles": ["Inglés", "Biología", "Arte"],
  "jueves": ["Física", "Geografía", "Música"],
  "viernes": ["Filosofía", "Informática", "Psicología"],
  "sábado": [],
  "domingo": []
}
EOF

echo ""
echo "✅ ¡Sistema configurado correctamente!"
echo ""
echo "📋 Pasos siguientes:"
echo ""
echo "1. 🔑 Configura tu API key de Anthropic:"
echo "   cp .env.example .env"
echo "   # Edita .env con tu API key real"
echo ""
echo "2. 🔗 Configura tu repositorio GitHub:"
echo "   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git"
echo ""
echo "3. 🌐 Activa GitHub Pages:"
echo "   - Ve a tu repositorio en GitHub"
echo "   - Settings > Pages > Source: GitHub Actions"
echo ""
echo "4. ⚙️ Configura Claude Desktop (opcional):"
echo "   - Copia el contenido de claude_desktop_config.json"
echo "   - Pégalo en tu configuración de Claude Desktop"
echo ""
echo "5. 🚀 Ejecuta el sistema:"
echo "   source venv/bin/activate"
echo "   export ANTHROPIC_API_KEY=tu_api_key"
echo "   python mcp_class_bot.py"
echo ""
echo "📖 Consulta README.md para más detalles"
echo ""
echo "🎉 ¡Listo para usar!"