import argparse
from app.CommandDispatch import CommandDispatch

def main():
    command = CommandDispatch()
    parser = argparse.ArgumentParser()
    commands = command.available_commands()
    parser.add_argument("command", type=str, choices=commands, help=f"Operation to perform: {', '.join(commands)}")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Additional arguments")
    args = parser.parse_args()
    print(command.dispatch(args.command, args.args), end="")


if __name__ == "__main__":
    main()
