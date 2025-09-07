import os
from git import Repo, GitCommandError

class GIT:
    def __init__(self, base_path="."):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)
        self.repo = None
        self.repo_path = None

    def setup_repo(self, github_url: str, repo_name: str):
        """Configura o clona un repositorio."""
        self.repo_path = os.path.join(self.base_path, repo_name)

        if os.path.exists(self.repo_path):
            self.repo = Repo(self.repo_path)
        else:
            self.repo = Repo.clone_from(github_url, self.repo_path)

        # Si el repo está vacío, crear commit inicial
        if not self.repo.head.is_valid() or len(self.repo.heads) == 0:
            dummy_file = os.path.join(self.repo_path, ".gitkeep")
            with open(dummy_file, "w", encoding="utf-8") as f:
                f.write("Initial commit\n")
            self.repo.index.add([dummy_file])
            self.repo.index.commit("Initial commit")

            try:
                origin = self.repo.remote(name="origin")
                try:
                    origin.push(refspec="HEAD:main")
                except GitCommandError:
                    origin.push(refspec="HEAD:master")
            except GitCommandError:
                pass

        return f"Repositorio listo en {self.repo_path}"

    
    def create_file_and_commit(self, filename: str, content: str, commit_message: str, push=True, branch="main"):
        """Crea o agrega contenido a un archivo y hace commit/push."""
        return self._commit_file(filename, content, commit_message, push, branch, overwrite=False)

    def overwrite_file_and_commit(self, filename: str, content: str, commit_message: str, push=True, branch="main"):
        """Sobrescribe un archivo existente y hace commit/push."""
        return self._commit_file(filename, content, commit_message, push, branch, overwrite=True)

    def _commit_file(self, filename, content, commit_message, push, branch, overwrite):
        if self.repo is None:
            return "Repo no inicializado. Usa setup_repo primero."

        file_path = os.path.join(self.repo_path, filename)
        dir_path = os.path.dirname(file_path)

        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        mode = "w" if overwrite else ("a" if os.path.exists(file_path) else "w")
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content + "\n")

        self.repo.index.add([filename])
        self.repo.index.commit(commit_message)

        result_msg = f"Archivo '{filename}' {'sobrescrito' if overwrite else 'actualizado/creado'} y commit '{commit_message}' realizado."

        if push:
            try:
                origin = self.repo.remote(name="origin")
                origin.fetch()
                pushed = origin.push(branch)
                if pushed and pushed[0].flags & 128:
                    result_msg += f" ⚠️ Error en push: {pushed[0].summary}"
                else:
                    result_msg += f" ✅ Commit pusheado a {branch}"
            except GitCommandError as e:
                result_msg += f" ⚠️ Error haciendo push: {e}"

        return result_msg

# Instancia global
git_manager = GIT(base_path="./repos")
