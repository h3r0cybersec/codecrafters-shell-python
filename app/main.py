import sys
import readline
import subprocess
from dataclasses import dataclass

# ogni comando eseguito ritorna uno status code
type Status = int

@dataclass
class Builtin:
    """ comandi builtin """

    def do_echo(self, *args) -> Status:
        pass

    def do_exit(self, *args) -> Status:
        pass

    def do_type(self, *args) -> Status:
        pass
    

@dataclass
class Shell:
    PROMPT = "$ "
    
    def __post_init__(self) -> None:
        # list comandi builtin supportati dalla shell
        self.builtins = Builtin()
        self.latest_status_code = -1

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
                status = self._run_cmd(cmd.strip().split())
            except (EOFError, KeyboardInterrupt):
                sys.stdout.write('\n')
                continue
        
def main() -> None:
    s = Shell()
    s.show()

if __name__ == "__main__":
    main()
