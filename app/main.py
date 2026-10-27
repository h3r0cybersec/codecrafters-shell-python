import sys
from pathlib import Path
import readline
from subprocess import PIPE, STDOUT, Popen
from typing import Dict, AnyStr, List
from dataclasses import dataclass
from collections import UserDict, namedtuple
from itertools import islice
import contextlib
import shlex
import os

# ogni comando eseguito ritorna uno status code
type Status = int

Redirection = namedtuple("Redirection", "index, file, mode, stdout, stderr")

def is_builtin(cmd: str, b: 'Builtin') -> bool:
        return True if cmd in b._internal.keys() else False
        
def is_external(cmd: str, e: 'Environment') -> AnyStr:
    search_path = e["PATH"].split(os.pathsep)
    for loc in search_path:
        try:
            full_path = Path(loc) / cmd
            if full_path.exists() and os.access(full_path, os.X_OK):
                return full_path
        except: continue
    return ""

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
            if is_builtin(cmd, self):
                out += f"{cmd} is a shell builtin\n"
            elif (full_path := is_external(cmd, self.env)):
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

    def do_history(self, *args) -> Status:
        """Mostra la lista dei comandi precedentemente eseguiti"""
    
        lines_count = readline.get_current_history_length()
    
        current_history = [
            (index, readline.get_history_item(index))
            for index in range(1, lines_count + 1)
        ]
    
        if args:
            count = int(args[0])
            current_history = current_history[-count:]
    
        for index, line in current_history:
            sys.stdout.write(f"    {index} {line}\n")
    
        return 0
        
@dataclass
class Shell:
    MAX_HISTORY_LINES = 1000
    def __post_init__(self) -> None:
        # variabili d'ambiente per la shell corrente
        self.environment = Environment()
        # list comandi builtin supportati dalla shell
        self.builtins = Builtin(self.environment)
        # ultimo codice di stato ritornato
        self.status = -1
        # gestisce lo stato interno per l'autocompletamento dei comandi
        self.is_lcp = False
        self.double_tab = False
        # configura la history se non esiste su disco
        try:
            #readline.read_history_file()
            readline.set_history_length(self.MAX_HISTORY_LINES)
        except FileNotFoundError:
            pass
        # configurazione readline per autocompletamento comandi
        readline.set_completer(self._auto_complete)
        readline.parse_and_bind("tab: complete")

    def _get_all_executables(self, text: str) -> List[str]:
        execs = {k for k in self.builtins._internal.keys() if k.startswith(text)}
        path_dirs = self.environment.get("PATH", "").split(os.pathsep)
        for directory in path_dirs:
            d_path = Path(directory)
            if not d_path.is_dir():
                continue
            # Filtraggio diretto con glob è più veloce di iterdir + startswith
            for executable in d_path.glob(f"{text}*"):
                if os.access(executable, os.X_OK):
                    execs.add(executable.name)
        return sorted(list(execs))

    def _lcp(text: str, matches: list) -> str:
        pass
        
        
    def _auto_complete(self, text: str, state: int) -> str | None:
        """ Gestisce l'autocompletamente dei comandi  """
        matches = []
        
        if state == 0:
            # Filtriamo subito per 'text' durante la scansione per essere più veloci
            matches = [
                cmd for cmd in self._get_all_executables(text) if cmd.startswith(text)
            ]
            max_len = len(text)
            matches = list(filter(lambda m: m.startswith(text), matches))
            first = matches[0][max_len:]
            last  = matches[-1][max_len:]
            if first != last:
                i = 0
                lcp = ""
                while i < len(first) and i < len(last) and first[i] == last[i]:
                    lcp = matches[-1][:max_len + i + 1]
                    i += 1
                # Se il LCP è più lungo di quello che l'utente ha scritto,
                # lo restituiamo come primo risultato.
                if len(lcp) > len(text):
                    matches = [f"{lcp}"]
                    self.is_lcp = True
            else:
                matches[-1] = f"{matches[-1]}"

        # Restituiamo i match uno alla volta come richiesto da readline
        if state < len(matches):
            # Aggiungi uno spazio se è un match univoco
            if self.is_lcp and len(matches) == 1:
                self.is_lcp = False
                return matches[state]
            elif len(matches) == 1:
                return f"{matches[state]} "
            else:
                if self.double_tab:
                    self.double_tab = False
                    sys.stdout.write(f"\n{'  '.join(matches)}\n{self.environment['PS1']}{text}")
                    return None
                else:
                    self.double_tab = True
                    None
        return None
        

    def _run_cmd(self, cmd_line: str) -> Status:
        """ esegue un comando nel sistema """
        
        # 1. Controlla se c'è una redirezione nella stringa originale
        redirection = self._redirect(cmd_line)
        
        # 2. Pulisci il comando dagli operatori di redirezione
        if redirection:
            # Rimuoviamo la parte della redirezione per avere il comando pulito
            actual_cmd = cmd_line[:redirection.index].strip()
        else:
            actual_cmd = cmd_line.strip()

        # 3. Parsing degli argomenti
        args = shlex.split(actual_cmd)
        cmd_name, cmd_args = args[0], args[1:]
        
        # 4. Esecuzione con gestione di redirezione per (builtin/external)
        if is_builtin(cmd_name, self.builtins):
            if redirection:
                with open(redirection.file, redirection.mode) as fd:
                    with contextlib.redirect_stdout(fd) if redirection.stdout else contextlib.redirect_stderr(fd):
                        # NOTE: punta stdout su un altro fd
                        return self.builtins.cmd[cmd_name](*cmd_args)
            return self.builtins.cmd[cmd_name](*cmd_args)
        elif is_external(cmd_name, self.environment):
            if redirection:
                return self._execute_and_redirect_on_file(
                    redirection,
                    *args
                )
            return self._execute(redirection, *args)
        else:
            sys.stderr.write(f"{cmd_name}: command not found\n")
            return 1

    def _execute_and_redirect_on_file(self, r: Redirection, *args) -> Status:
        """ Esegue un comando ed effettua il redirect su file """
        with open(r.file, r.mode) as fd:
            proc = Popen(
                     args, 
                     env=self.environment, 
                     stdout=fd if r.stdout else None,
                     stderr=fd if r.stderr else None
                   )
            proc.wait()
            return proc.returncode

    def _execute(self, r: Redirection, *args) -> Status:
        """ Esegue un comando """
        proc = Popen(
            args, 
            env=self.environment,
            stdout=PIPE, 
            stderr=PIPE,
            text=True,
            universal_newlines=True
        )
        try:
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

    def _redirect(self, buffer: str) -> Redirection | None:
        """ 
            Gestisce il redirect
            > 1> 2> >> 2>>
        """
        if (index := buffer.find('>')):
            if index == -1:
                return None

            cur   = buffer[index]
            left  = buffer[index - 1] if buffer[index - 1] == '1' or buffer[index - 1] == '2' else ''
            right = buffer[index + 1] if buffer[index + 1] == '>' else ''
            op = f"{left+cur+right}".strip()
            is_double_op = op.count('>') > 1

            # recupera il file su cui effettuare la redirect
            file   = buffer[index+len(op):].strip()
            mode   = ""
            stdout = False
            stderr = False
            
            match op:
                case '>' | '1>' | '>>' | '1>>':
                    stdout = True
                    mode   = "w" if not is_double_op else "a"
                case '2>' | '2>>':
                    stderr = True
                    mode   = "w" if not is_double_op else "a"
                case _:
                    # TODO: gestire correttamente una redirezione non valida
                    pass
            
            return Redirection(
                    index - 1 if len(op) == 2 else index - 2 if len(op) == 3 else index, 
                    file, 
                    mode,
                    stdout,
                    stderr
            )
    
    def _pipe(self):
        """ Gestisce l'esecuzione di una catena di comandi """
        pass  

    def repl(self) -> None:
        """ Mostra la shell """
        while True:
            try:
                line = input(self.environment["PS1"]).strip()
                if not line:
                    continue
                #readline.add_history(line)
                self.status = self._run_cmd(line)
            except (EOFError, KeyboardInterrupt):
                sys.stdout.write('\n')
                continue
            except SystemExit:
                raise
            #finally:
            #    readline.write_history_file()
        
def main() -> None:
    try:
        s = Shell()
        s.repl()
    except SystemExit as exit_code:
        sys.exit(exit_code)
        
            
if __name__ == "__main__":
    main()
