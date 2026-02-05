import sys
from pathlib import Path
import readline
from subprocess import PIPE, Popen
from typing import Dict, AnyStr, List
from dataclasses import dataclass
from collections import UserDict
import shlex
import os

# ogni comando eseguito ritorna uno status code
type Status = int

class Environment(UserDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # eredita le variabili di sistema
        for key, value in os.environ.items():
            if key not in self.data:  # Non sovrascrivere se passato in __init__
                self.data[key] = value
        # sovrascrive con quelle personalizzate
        self.data["PS1"] = "$ "

@dataclass
class Builtin:
    """ comandi builtin """

    env: Environment

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
    
    def is_external(self, cmd: str) -> AnyStr:
        search_path = self.env["PATH"].split(":")
        for loc in search_path:
            try:
                for file in Path(loc).iterdir():
                    if cmd == file.name:
                        full_path = Path(loc) / file
                        if os.access(full_path, os.X_OK):
                            return str(full_path)
            except: continue
        return ''

    def do_echo(self, *args) -> Status:
        """ Emette a video quello che è stato passato """
        sys.stdout.write(f"{' '.join(args)}\n")
        return 0

    def do_exit(self, *args) -> Status:
        """ Termina la shell """
        try:
            if len(args) > 0:
                raise SystemExit(int(args[0]))
            raise SystemExit(0)
        except ValueError:
            raise SystemExit(1)

    def do_type(self, *args) -> Status:
        """ Mostra se un comando è builtin oppure no """
        out = ""
        for cmd in args:
            if self.is_builtin(cmd):
                out += f"{cmd} is a shell builtin\n"
            elif (full_path := self.is_external(cmd)):
                out += f"{cmd} is {full_path}\n"
            else:
                out += f"{cmd}: not found\n"
        sys.stdout.write(out)

    def do_pwd(self, *args) -> Status:
        """ Mostra la cartella corrente """
        sys.stdout.write(f"{os.getcwd()}\n")
        return 0

    def do_env(self, *args) -> Status:
        """ Stampa le variabili d'ambiente predefinite """
        out = ""
        for key, value in self.env.items():
            out += f"{key}={value}\n"
        sys.stdout.write(out)
        return 0

    def do_cd(self, *args) -> Status:
        """ Permette di spostarsi nel filesystem """
        if len(args) > 1:
            sys.stderr.write(f"cd: too many arguments\n")
            return 1
        location = os.path.expanduser(args[0]) if args[0].startswith("~") else args[0]
        try:
            os.chdir(location)
            self.env["OLDPWD"] = self.env["PWD"] 
            self.env["PWD"] = location
        except FileNotFoundError:
            sys.stderr.write(f"cd: {location}: No such file or directory\n")
            return 1

@dataclass
class Command:
    """ formatta un comando  """
    raw  : List[AnyStr]
    path : AnyStr = ""

    @property
    def name(self):
        return self.raw[0]

    @property
    def args(self):
        return self.raw[1:]
        
@dataclass
class Shell:
    def __post_init__(self) -> None:
        # variabili d'ambiente per la shell corrente
        self.environment = Environment()
        # list comandi builtin supportati dalla shell
        self.builtins = Builtin(self.environment)
        # ultimo codice di errore
        self.status = -1

    def _run_cmd(self, cmd: Command) -> Status:
        """ esegue un comando nel sistema """
        # 1. Verifica se è un comando builtin
        if self.builtins.is_builtin(cmd.name):
            return self.builtins.cmd[cmd.name](*cmd.args)
        # 2. Verifica se è un comando esterno
        elif (exe_path := self.builtins.is_external(cmd.name)):
            cmd.path = exe_path 
            return self._execute(cmd)
        # 3. Se non ne è nei primi due casi allora è un comando che non esiste
        else:
            sys.stderr.write(f"{cmd.name}: command not found\n")
            return 1

    def _execute(self, cmd: Command) -> Status:
        try:
            proc     = Popen([cmd.name, *cmd.args], env=self.environment, stdout=PIPE, text=True)
            out, err = proc.communicate()
            if err:
                sys.stderr.write(err)
            else:
                sys.stdout.write(out)
            return proc.returncode
        except PermissionError:
            #FIXME: Utilizzare lo stesso modo che usa bash quanto un comando fallisce
            #       per mancanza di privilegi
            return 1

    def repl(self) -> None:
        """ Mostra la shell """
        while True:
            try:
                raw = input(self.environment["PS1"]).strip()
                if not raw:
                    continue
                cmd = Command(shlex.split(raw))
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
        sys.exit(exit_code)
            
if __name__ == "__main__":
    main()
