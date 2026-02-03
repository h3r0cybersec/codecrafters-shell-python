import sys
import readline

PROMPT = "$ "

class Shell:
    pass

def main():
    while True:
        cmd = input(PROMPT)
        if cmd == "exit":
            break
        #out = handle_pipe(cmd)
        # out.read().decode("utf-8")
        sys.stdout.write(f"{cmd}\n")

if __name__ == "__main__":
    main()
