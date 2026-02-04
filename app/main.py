import sys
import readline
import subprocess
from typing import Dict, AnyStr, List
from dataclasses import dataclass
import os

# ogni comando eseguito ritorna uno status code
type Status = int

@dataclass
class Command:
    """ descrive un comando """
    name: AnyStr
    args: List[AnyStr]

@dataclass
class Builtin:
    """ comandi builtin """

    def __post_init__(self) -> None:
        self._internal = {}
        for attr in dir(self):
            if attr.startswith("do_"):
                self._internal[attr[3:]] = getattr(self, attr)
    @property
    def cmd(self):
        return self._internal
        
    def is_builtin(self, cmd: str) -> bool:
        return True if cmd in self._internal.keys() else False

    def do_echo(self, *args) -> Status:
        sys.stdout.write(f"{' '.join(args)}\n")
        return 0

    def do_type(self, *args) -> Status:
        out = ""
        for cmd in args:
            if self.is_builtin(cmd):
                out += f"{cmd} is a shell builtin\n"
            else:
                out += f"{cmd}: command not found\n"
        sys.stdout.write(out)

    def do_pwd(self, *args) -> Status:
        sys.stdout.write(os.getcwd())
        return 0


@dataclass
class Shell:
    PROMPT = "$ "
    
    def __post_init__(self) -> None:
        # list comandi builtin supportati dalla shell
        self.builtins = Builtin()
        self.status = -1            # ultimo codice di errore

    def _run_cmd(self, cmd: Command) -> Status:
        """ esegue un comando nel sistema """
        if cmd.name == "exit":
            raise SystemExit(cmd.args[0] if cmd.args else 0)
            
        # 1. Verifica se è un comando builtin
        if self.builtins.is_builtin(cmd.name):
            return self.builtins.cmd[cmd.name](*cmd.args)
        # 2. Verifica se è un comando esterno

        # 3. Se non ne è nei primi due casi allora è un comando che non esiste
        else:
            sys.stderr.write(f"{cmd.name}: command not found\n")
            return 1

    def repl(self) -> None:
        """ Mostra la shell """
        while True:
            try:
                raw = input(self.PROMPT).strip().split()
                cmd = Command(raw[0], raw[1:])
                self.status = self._run_cmd(cmd)
            except (EOFError, KeyboardInterrupt):
                continue
            except SystemExit:
                raise
        
def main() -> None:
    try:
        s = Shell()
        s.repl()
    except SystemExit as exit_code:
        try:
            sys.exit(exit_code)
        except ValueError:
            sys.exit(1)
            
if __name__ == "__main__":
    main()
