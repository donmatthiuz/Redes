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

    def create_file_and_commit(self, filename: str, content: str, commit_message: str):
        if self.repo is None:
            return "Repo no inicializado. Usa setup_repo primero."
        
        file_path = os.path.join(self.repo_path, filename)
        with open(file_path, "w") as f:
            f.write(content)
        
        self.repo.index.add([filename])
        self.repo.index.commit(commit_message)
        return f"Archivo '{filename}' creado y commit '{commit_message}' realizado."


git_manager = GIT(base_path="./repos")
