import sys
from pathlib import Path
import readline
import subprocess
from dataclasses import dataclass
import os
import importlib

from utils import Status

@dataclass
class Shell:
    PROMPT = "$ "
    BUILTIN_CMD_DIR = Path(__file__).parent / "cmd"
    
    def __post_init__(self) -> None:
        # list comandi builtin supportati dalla shell
        self.builtins = {}
        self.latest_status_code = -1
        self._load_builtin_commands()

    def _load_builtin_commands(self):
        """ carica i comandi integrati """
        for filename in os.listdir(self.BUILTIN_CMD_DIR):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                file_path = os.path.join(self.BUILTIN_CMD_DIR, filename)
                try:
                    # 1. Crea una specifica del modulo dal percorso del file
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    # 2. Crea un nuovo modulo basato sulla specifica
                    module = importlib.util.module_from_spec(spec)
                    # 3. Esegue il modulo per caricarne il contenuto
                    spec.loader.exec_module(module)
                    if hasattr(module, module_name.capitalize()):
                        command = getattr(module, module_name.capitalize())
                        self.builtins[module_name] = command.execute
                    else:
                        sys.stdout.write(f"skipping '{filename}' because not contains executable code\n")
                except Exception as e:
                    sys.stderr.write(f"error occures on load command builtin '{filename}': {e}\n")

    def _run_cmd(self, cmd: str) -> Status:
        sys.stderr.write(f"{cmd[0]}: command not found\n")
        return 1

    def show(self):
        """ Mostra la shell """
        while True:
            try:
                cmd = input(self.PROMPT)
                if cmd == "exit":
                    break
                #out = handle_pipe(cmd)
                # out.read().decode("utf-8")
                status = self._run_cmd(cmd.strip().split())
            except (EOFError, KeyboardInterrupt):
                sys.stdout.write('\n')
                continue
        
def main() -> None:
    s = Shell()
    s.show()

if __name__ == "__main__":
    main()
