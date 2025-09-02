#!/usr/bin/env python3
"""
Sistema MCP para gestión de clases con Claude AI
Versión corregida con servidores MCP funcionales
"""

import json
import os
import asyncio
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import anthropic

class ClassScheduleManager:
    """Gestor del horario de clases"""
    
    def __init__(self, schedule_file: str = "horario_clases.json"):
        self.schedule_file = schedule_file
        self.schedule = self.load_schedule()
    
    def load_schedule(self) -> Dict:
        """Carga el horario desde archivo JSON"""
        if os.path.exists(self.schedule_file):
            with open(self.schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Crear horario de ejemplo
            default_schedule = {
                "lunes": ["Matemáticas", "Historia", "Ciencias"],
                "martes": ["Literatura", "Química", "Educación Física"],
                "miércoles": ["Inglés", "Biología", "Arte"],
                "jueves": ["Física", "Geografía", "Música"],
                "viernes": ["Filosofía", "Informática", "Psicología"],
                "sábado": [],
                "domingo": []
            }
            self.save_schedule(default_schedule)
            return default_schedule
    
    def save_schedule(self, schedule: Dict):
        """Guarda el horario en archivo JSON"""
        with open(self.schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
        self.schedule = schedule
    
    def get_today_classes(self) -> List[str]:
        """Obtiene las clases del día actual"""
        today = date.today().strftime("%A").lower()
        day_mapping = {
            "monday": "lunes",
            "tuesday": "martes", 
            "wednesday": "miércoles",
            "thursday": "jueves",
            "friday": "viernes",
            "saturday": "sábado",
            "sunday": "domingo"
        }
        spanish_day = day_mapping.get(today, today)
        return self.schedule.get(spanish_day, [])

class MCPClassBot:
    """Bot principal que integra Claude con funcionalidades de Git y archivos"""
    
    def __init__(self, anthropic_api_key: str, classes_dir: str = "clases"):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.schedule_manager = ClassScheduleManager()
        self.classes_dir = Path(classes_dir)
        self.classes_dir.mkdir(exist_ok=True)
        self.repo_path = Path(".")
    
    def check_git_repo(self) -> bool:
        """Verifica si estamos en un repositorio Git"""
        return (self.repo_path / ".git").exists()
    
    def init_git_repo(self):
        """Inicializa un repositorio Git si no existe"""
        if not self.check_git_repo():
            try:
                subprocess.run(["git", "init"], cwd=self.repo_path, check=True)
                subprocess.run(["git", "branch", "-M", "main"], cwd=self.repo_path, check=True)
                print("✅ Repositorio Git inicializado")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error inicializando Git: {e}")
    
    async def get_today_classes_info(self) -> str:
        """Consulta las clases del día actual"""
        today_classes = self.schedule_manager.get_today_classes()
        today_str = date.today().strftime("%d/%m/%Y")
        
        if not today_classes:
            return f"📅 No tienes clases programadas para hoy {today_str}"
        
        classes_text = "\n".join([f"• {clase}" for clase in today_classes])
        return f"📚 Clases para hoy {today_str}:\n{classes_text}"
    
    async def create_class_notes(self, subject: str, notes: str) -> bool:
        """Crea archivo de notas para una clase específica"""
        try:
            today = date.today()
            filename = f"{subject.replace(' ', '_').lower()}_{today.strftime('%Y%m%d')}.md"
            filepath = self.classes_dir / filename
            
            # Crear contenido del archivo
            content = f"""# {subject} - {today.strftime('%d/%m/%Y')}

## Notas de la clase

{notes}

## Resumen
- Fecha: {today.strftime('%d/%m/%Y')}
- Materia: {subject}
- Palabras clave: {', '.join(notes.split()[:5])}

---
*Generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
            
            # Escribir archivo
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Notas creadas: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando notas: {e}")
            return False
    
    def git_add(self, files: List[str] = None) -> bool:
        """Agrega archivos al staging area de Git"""
        try:
            if files is None:
                files = ["."]
            
            for file in files:
                subprocess.run(["git", "add", file], cwd=self.repo_path, check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error en git add: {e}")
            return False
    
    def git_commit(self, message: str) -> bool:
        """Hace commit de los cambios"""
        try:
            subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in str(e):
                print("ℹ️ No hay cambios para commitear")
                return True
            print(f"❌ Error en git commit: {e}")
            return False
    
    def git_push(self, remote: str = "origin", branch: str = "main") -> bool:
        """Hace push al repositorio remoto"""
        try:
            subprocess.run(["git", "push", remote, branch], cwd=self.repo_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error en git push: {e}")
            return False
    
    def git_status(self) -> str:
        """Obtiene el status del repositorio"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error obteniendo status: {e}"
    
    async def commit_and_push_to_github(self, subject: str = "", message: str = None) -> bool:
        """Hace commit y push de los archivos al repositorio"""
        try:
            # Verificar que tenemos un repo Git
            if not self.check_git_repo():
                self.init_git_repo()
            
            # Crear mensaje de commit
            if not message:
                today = date.today().strftime('%d/%m/%Y')
                if subject:
                    message = f"Agregar notas de {subject} - {today}"
                else:
                    message = f"Actualización general - {today}"
            
            # Agregar archivos, commitear y hacer push
            if self.git_add() and self.git_commit(message):
                # Intentar push solo si hay remote configurado
                try:
                    subprocess.run(
                        ["git", "remote", "get-url", "origin"], 
                        cwd=self.repo_path, 
                        capture_output=True, 
                        check=True
                    )
                    if self.git_push():
                        print(f"✅ Cambios publicados en GitHub: {message}")
                        return True
                    else:
                        print("⚠️ Commit local realizado, pero no se pudo hacer push")
                        return False
                except subprocess.CalledProcessError:
                    print("⚠️ No hay repositorio remoto configurado")
                    print("💡 Configura el repositorio remoto con:")
                    print("   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git")
                    return False
            else:
                return False
            
        except Exception as e:
            print(f"❌ Error publicando cambios: {e}")
            return False
    
    async def deploy_to_github_pages(self) -> bool:
        """Despliega el sitio en GitHub Pages"""
        try:
            # Generar index.html para GitHub Pages
            index_content = self.generate_index_html()
            index_path = Path("index.html")
            
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            # Commit y push del index
            success = await self.commit_and_push_to_github(
                "", "Actualizar GitHub Pages con notas de clases"
            )
            
            if success:
                print("✅ Sitio desplegado en GitHub Pages")
                print("🌐 Tu sitio estará disponible en: https://TU_USUARIO.github.io/TU_REPO")
                return True
            else:
                return False
            
        except Exception as e:
            print(f"❌ Error desplegando en GitHub Pages: {e}")
            return False
    
    def generate_index_html(self) -> str:
        """Genera el HTML para GitHub Pages"""
        classes_files = sorted(list(self.classes_dir.glob("*.md")), reverse=True)
        
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📚 Mis Notas de Clase</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px; 
            margin: 0 auto; 
            padding: 20px; 
            background: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        .class-item {{ 
            background: white;
            border: none;
            margin: 15px 0; 
            padding: 20px; 
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .class-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}
        .class-item h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .class-item a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .class-item a:hover {{
            text-decoration: underline;
        }}
        .date {{ 
            color: #666; 
            font-size: 0.9em;
            background: #f8f9fa;
            padding: 5px 10px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .stat {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            min-width: 120px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        .no-classes {{
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 10px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        @media (max-width: 600px) {{
            body {{ padding: 10px; }}
            .header {{ padding: 20px 15px; }}
            .stats {{ flex-direction: column; align-items: center; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 Mis Notas de Clase</h1>
        <p>Sistema de gestión educativa con Claude AI</p>
        <p><small>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small></p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <span class="stat-number">{len(classes_files)}</span>
            <span>Archivos de notas</span>
        </div>
        <div class="stat">
            <span class="stat-number">{len(set(f.name.split('_')[0] for f in classes_files))}</span>
            <span>Materias</span>
        </div>
    </div>
"""
        
        if classes_files:
            html += "<h2>📝 Notas por fecha</h2>"
            for file_path in classes_files:
                # Extraer información del nombre del archivo
                parts = file_path.stem.split('_')
                if len(parts) >= 2:
                    subject_parts = parts[:-1]  # Todo excepto la fecha
                    date_part = parts[-1]  # La fecha
                    subject = ' '.join(word.capitalize() for word in subject_parts)
                    
                    # Formatear fecha
                    try:
                        file_date = datetime.strptime(date_part, '%Y%m%d')
                        formatted_date = file_date.strftime('%d/%m/%Y')
                    except:
                        formatted_date = date_part
                else:
                    subject = file_path.stem.replace('_', ' ').title()
                    formatted_date = "Sin fecha"
                
                html += f"""
    <div class="class-item">
        <h3><a href="clases/{file_path.name}">{subject}</a></h3>
        <span class="date">📅 {formatted_date}</span>
    </div>"""
        else:
            html += """
    <div class="no-classes">
        <h3>🎯 ¡Listo para empezar!</h3>
        <p>Aún no tienes notas de clase. ¡Crea tu primera nota usando el bot!</p>
        <p><em>Usa el comando "notas [materia]" para comenzar</em></p>
    </div>"""
        
        html += """
    
    <div style="text-align: center; margin-top: 40px; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <p><strong>🤖 Generado automáticamente por el Sistema MCP de Clases</strong></p>
        <p><em>Integración Claude AI + MCP + GitHub Pages</em></p>
    </div>
</body>
</html>"""
        
        return html
    
    async def chat_with_claude(self, user_message: str) -> str:
        """Interactúa con Claude AI"""
        try:
            # Obtener contexto de clases del día
            today_info = await self.get_today_classes_info()
            
            # Obtener status de Git
            git_status = self.git_status()
            git_info = f"Git status: {'Cambios pendientes' if git_status.strip() else 'Todo actualizado'}"
            
            system_prompt = f"""Eres un asistente educativo especializado en gestión de clases y notas académicas.

INFORMACIÓN DEL CONTEXTO:
{today_info}

Estado del repositorio:
{git_info}

CAPACIDADES DISPONIBLES:
1. 📅 Consultar horarios de clase
2. 📝 Crear y organizar notas de clase
3. 🔄 Versionado automático con Git
4. 🌐 Publicación en GitHub Pages
5. 📊 Generar reportes y estadísticas

COMANDOS ESPECIALES:
- "clases" o "horario" → Mostrar clases de hoy
- "notas [materia]" → Crear notas para una materia
- "publicar" → Subir cambios a GitHub
- "deploy" → Desplegar sitio web

Responde de forma clara, útil y educativa. Si el usuario pregunta sobre temas académicos, 
proporciona información relevante y sugiere cómo organizar esa información en notas."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"❌ Error comunicándome con Claude: {e}\n💡 Verifica que tu API key esté configurada correctamente."
    
    async def run_interactive_session(self):
        """Ejecuta sesión interactiva del bot"""
        print("🤖 Bot de Clases con Claude AI y MCP iniciado")
        print("=" * 60)
        print("📚 COMANDOS DISPONIBLES:")
        print("  • 'clases' o 'horario' → Ver clases de hoy")
        print("  • 'notas [materia]' → Crear notas para una materia")
        print("  • 'publicar' → Publicar cambios en GitHub")
        print("  • 'deploy' → Desplegar en GitHub Pages")
        print("  • 'status' → Ver estado del repositorio")
        print("  • 'salir' → Terminar programa")
        print("  • O pregunta cualquier cosa a Claude AI")
        print("=" * 60)
        
        # Mostrar información inicial
        info = await self.get_today_classes_info()
        print(f"\n{info}")
        
        while True:
            try:
                user_input = input("\n💬 Tú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit', 'q']:
                    print("👋 ¡Hasta luego! Que tengas un buen día de clases.")
                    break
                
                elif user_input.lower() in ['clases', 'horario']:
                    info = await self.get_today_classes_info()
                    print(f"\n🤖 {info}")
                
                elif user_input.lower().startswith('notas'):
                    parts = user_input.split(' ', 1)
                    if len(parts) > 1:
                        subject = parts[1]
                        print(f"\n📝 Creando notas para: {subject}")
                        print("💡 Escribe tus notas (presiona Enter dos veces para finalizar):")
                        
                        notes_lines = []
                        while True:
                            line = input()
                            if line == "":
                                if notes_lines and notes_lines[-1] == "":
                                    break
                            notes_lines.append(line)
                        
                        notes_content = "\n".join(notes_lines).strip()
                        
                        if notes_content:
                            success = await self.create_class_notes(subject, notes_content)
                            if success:
                                print(f"✅ Notas de {subject} guardadas correctamente")
                                
                                # Preguntar si quiere publicar automáticamente
                                publish = input("¿Quieres publicar estas notas en GitHub? (s/N): ").lower()
                                if publish in ['s', 'si', 'sí', 'y', 'yes']:
                                    await self.commit_and_push_to_github(subject)
                            else:
                                print(f"❌ Error guardando notas de {subject}")
                        else:
                            print("❌ No se ingresaron notas")
                    else:
                        print("❓ Especifica la materia: 'notas Matemáticas'")
                
                elif user_input.lower() == 'publicar':
                    print("📤 Publicando cambios en GitHub...")
                    success = await self.commit_and_push_to_github()
                    if success:
                        print("✅ Cambios publicados en GitHub")
                    else:
                        print("❌ Error publicando en GitHub")
                
                elif user_input.lower() == 'deploy':
                    print("🚀 Desplegando sitio en GitHub Pages...")
                    success = await self.deploy_to_github_pages()
                    if success:
                        print("✅ Sitio desplegado en GitHub Pages")
                    else:
                        print("❌ Error desplegando el sitio")
                
                elif user_input.lower() == 'status':
                    status = self.git_status()
                    if status.strip():
                        print(f"\n📊 Estado del repositorio:")
                        print(status)
                    else:
                        print("✅ Repositorio actualizado - no hay cambios pendientes")
                
                else:
                    # Consultar a Claude
                    print("🤖 Claude está pensando...")
                    response = await self.chat_with_claude(user_input)
                    print(f"\n🤖 Claude: {response}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except EOFError:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error inesperado: {e}")
                print("💡 Intenta de nuevo o usa 'salir' para terminar")

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    missing = []
    
    try:
        import anthropic
    except ImportError:
        missing.append("anthropic")
    
    # Verificar Git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append("git")
    
    if missing:
        print("❌ Dependencias faltantes:")
        for dep in missing:
            print(f"  • {dep}")
        print("\n💡 Instala las dependencias con:")
        print("  pip install anthropic")
        if "git" in missing:
            print("  # También necesitas instalar Git en tu sistema")
        return False
    
    return True

def setup_environment():
    """Configura el entorno necesario"""
    # Crear archivo .env si no existe
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creando archivo .env desde .env.example...")
        import shutil
        shutil.copy(env_example, env_file)
        print("⚠️  Recuerda configurar tu ANTHROPIC_API_KEY en el archivo .env")
    
    # Cargar variables de entorno
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Función principal
async def main():
    """Función principal del programa"""
    print("🚀 Iniciando Sistema MCP para Gestión de Clases...")
    print("=" * 60)
    
    # Verificar dependencias
    if not check_dependencies():
        return
    
    # Configurar entorno
    setup_environment()
    
    # Obtener API key
    API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not API_KEY:
        print("❌ Error: No se encontró ANTHROPIC_API_KEY")
        print("\n💡 Configuración necesaria:")
        print("1. Crea un archivo .env en este directorio")
        print("2. Agrega la línea: ANTHROPIC_API_KEY=tu_api_key_aqui")
        print("3. Obtén tu API key en: https://console.anthropic.com/")
        return
    
    # Verificar que la API key no sea el placeholder
    if API_KEY.startswith("tu_api_key") or API_KEY == "your_api_key_here":
        print("❌ Error: Debes reemplazar el placeholder con tu API key real")
        print("💡 Edita el archivo .env y agrega tu API key de Anthropic")
        return
    
    print("✅ Configuración verificada correctamente")
    print("🤖 Iniciando bot...")
    
    try:
        bot = MCPClassBot(API_KEY)
        await bot.run_interactive_session()
    except KeyboardInterrupt:
        print("\n👋 Programa terminado por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        print("💡 Verifica tu configuración y vuelve a intentar")

if __name__ == "__main__":
    asyncio.run(main())