import os
from git import Repo

class GIT:
    def __init__(self, base_path="."):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
        self.repo = None
        self.repo_path = None

    def setup_repo(self, github_url: str, repo_name: str):
        self.repo_path = os.path.join(self.base_path, repo_name)
        if os.path.exists(self.repo_path):
            # Si ya existe, simplemente abrimos
            self.repo = Repo(self.repo_path)
        else:
            self.repo = Repo.clone_from(github_url, self.repo_path)
        return f"Repositorio listo en {self.repo_path}"
    
    
    def create_file_and_commit(self, filename: str, content: str, commit_message: str, push=True, branch="main"):
        if self.repo is None:
            return "Repo no inicializado. Usa setup_repo primero."
        
        file_path = os.path.join(self.repo_path, filename)
        dir_path = os.path.dirname(file_path)

        # Crear directorio si no existe
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # Crear o agregar contenido al archivo
        if os.path.exists(file_path):
            mode = "a"  # agregar
        else:
            mode = "w"  # crear
        
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content + "\n")

        # Git add y commit
        self.repo.index.add([filename])
        self.repo.index.commit(commit_message)

        result_msg = f"Archivo '{filename}' {'actualizado' if mode=='a' else 'creado'} y commit '{commit_message}' realizado."

        if push:
            try:
                origin = self.repo.remote(name="origin")
                # Hacer pull antes de push para evitar conflictos
                origin.pull(rebase=True)
                origin.push(branch)
                result_msg += f" ✅ Commit pusheado a {branch}"
            except Exception as e:
                result_msg += f" ⚠️ Error haciendo push: {e}"

        return result_msg



git_manager = GIT(base_path="./repos")
