#!/usr/bin/env python3
"""
Sistema MCP para gestión de clases con Claude AI
Integra Filesystem MCP Server y Git MCP Server
"""

import json
import os
import asyncio
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional
import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
    """Bot principal que integra Claude con servidores MCP"""
    
    def __init__(self, anthropic_api_key: str, classes_dir: str = "clases"):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.schedule_manager = ClassScheduleManager()
        self.classes_dir = Path(classes_dir)
        self.classes_dir.mkdir(exist_ok=True)
        
        # Configuración de servidores MCP
        self.filesystem_server = None
        self.git_server = None
    
    async def setup_mcp_servers(self):
        """Configura los servidores MCP"""
        try:
            # Configurar Filesystem MCP Server
            fs_server_params = StdioServerParameters(
                command="npx",
                args=["@modelcontextprotocol/server-filesystem", str(self.classes_dir)]
            )
            
            # Configurar Git MCP Server  
            git_server_params = StdioServerParameters(
                command="npx",
                args=["@modelcontextprotocol/server-git", "."]
            )
            
            # Inicializar servidores
            self.filesystem_server = stdio_client(fs_server_params)
            self.git_server = stdio_client(git_server_params)
            
            print("✅ Servidores MCP configurados correctamente")
            
        except Exception as e:
            print(f"❌ Error configurando servidores MCP: {e}")
    
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

---
*Generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
            
            # Usar MCP Filesystem Server para escribir archivo
            if self.filesystem_server:
                async with self.filesystem_server as session:
                    await session.call_tool("write_file", {
                        "path": str(filepath),
                        "content": content
                    })
            else:
                # Fallback: escribir directamente
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            print(f"✅ Notas creadas: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando notas: {e}")
            return False
    
    async def commit_and_push_to_github(self, subject: str, message: str = None) -> bool:
        """Hace commit y push de los archivos al repositorio"""
        try:
            if not message:
                today = date.today().strftime('%d/%m/%Y')
                message = f"Agregar notas de {subject} - {today}"
            
            if self.git_server:
                async with self.git_server as session:
                    # Agregar archivos
                    await session.call_tool("git_add", {"paths": [str(self.classes_dir)]})
                    
                    # Hacer commit
                    await session.call_tool("git_commit", {"message": message})
                    
                    # Push a GitHub
                    await session.call_tool("git_push", {"remote": "origin", "branch": "main"})
            else:
                # Fallback: usar comandos git directos
                os.system(f"git add {self.classes_dir}")
                os.system(f'git commit -m "{message}"')
                os.system("git push origin main")
            
            print(f"✅ Cambios publicados en GitHub: {message}")
            return True
            
        except Exception as e:
            print(f"❌ Error publicando en GitHub: {e}")
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
            await self.commit_and_push_to_github("Sitio web", "Actualizar GitHub Pages")
            
            print("✅ Sitio desplegado en GitHub Pages")
            return True
            
        except Exception as e:
            print(f"❌ Error desplegando en GitHub Pages: {e}")
            return False
    
    def generate_index_html(self) -> str:
        """Genera el HTML para GitHub Pages"""
        classes_files = list(self.classes_dir.glob("*.md"))
        
        html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mis Clases - Notas</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .class-item { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .date { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>📚 Mis Notas de Clase</h1>
    <p>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
"""
        
        for file_path in sorted(classes_files, reverse=True):
            subject = file_path.stem.replace('_', ' ').title()
            html += f"""
    <div class="class-item">
        <h3><a href="clases/{file_path.name}">{subject}</a></h3>
        <p class="date">Archivo: {file_path.name}</p>
    </div>"""
        
        html += """
</body>
</html>"""
        return html
    
    async def chat_with_claude(self, user_message: str) -> str:
        """Interactúa con Claude AI"""
        try:
            # Obtener contexto de clases del día
            today_info = await self.get_today_classes_info()
            
            system_prompt = f"""Eres un asistente educativo que ayuda a gestionar clases y notas.

Información del día:
{today_info}

Puedes ayudar con:
1. Consultar qué clases tienes hoy
2. Crear notas de clases
3. Publicar notas en GitHub
4. Desplegar en GitHub Pages

Responde de manera útil y concisa."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error comunicándome con Claude: {e}"
    
    async def run_interactive_session(self):
        """Ejecuta sesión interactiva del bot"""
        await self.setup_mcp_servers()
        
        print("🤖 Bot de Clases con Claude AI y MCP iniciado")
        print("Comandos disponibles:")
        print("  - 'clases' o 'horario': Ver clases de hoy")
        print("  - 'notas [materia]': Crear notas para una materia")
        print("  - 'publicar': Publicar cambios en GitHub")
        print("  - 'deploy': Desplegar en GitHub Pages")
        print("  - 'salir': Terminar")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n💬 Tú: ").strip()
                
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    print("👋 ¡Hasta luego!")
                    break
                
                elif user_input.lower() in ['clases', 'horario']:
                    info = await self.get_today_classes_info()
                    print(f"\n🤖 Bot: {info}")
                
                elif user_input.lower().startswith('notas'):
                    parts = user_input.split(' ', 1)
                    if len(parts) > 1:
                        subject = parts[1]
                        notes_content = input(f"📝 Ingresa las notas para {subject}: ")
                        success = await self.create_class_notes(subject, notes_content)
                        if success:
                            print(f"✅ Notas de {subject} guardadas correctamente")
                        else:
                            print(f"❌ Error guardando notas de {subject}")
                    else:
                        print("❓ Especifica la materia: 'notas Matemáticas'")
                
                elif user_input.lower() == 'publicar':
                    success = await self.commit_and_push_to_github("Actualización general")
                    if success:
                        print("✅ Cambios publicados en GitHub")
                    else:
                        print("❌ Error publicando en GitHub")
                
                elif user_input.lower() == 'deploy':
                    success = await self.deploy_to_github_pages()
                    if success:
                        print("✅ Sitio desplegado en GitHub Pages")
                    else:
                        print("❌ Error desplegando el sitio")
                
                else:
                    # Consultar a Claude
                    response = await self.chat_with_claude(user_input)
                    print(f"\n🤖 Claude: {response}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

# Función principal
async def main():
    # Configurar con tu API key de Anthropic
    API_KEY = os.getenv("ANTHROPIC_API_KEY")
    if not API_KEY:
        print("❌ Error: Define la variable ANTHROPIC_API_KEY")
        return
    
    bot = MCPClassBot(API_KEY)
    await bot.run_interactive_session()

if __name__ == "__main__":
    asyncio.run(main())