import argparse
import builtins
import contextlib
import runpy
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("script", help="Target Python script, e.g. main.py")
    parser.add_argument(
        "--input", help="Text file containing input lines")
    parser.add_argument(
        "--output", default="output_log.txt", help="Log file path (default: output_log.txt)",
    )
    parser.add_argument("--encoding", default="utf-8")
    return parser.parse_args()


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def make_logged_input(lines):
    iterator = iter(lines)

    def logged_input(prompt=""):
        try:
            line = next(iterator)
        except StopIteration as exc:
            raise EOFError("No more lines in input file.") from exc
        print(f"{prompt}{line}")
        return line

    return logged_input


def make_live_logged_input(original_input):
    def logged_input(prompt=""):
        line = original_input(prompt)
        print(line)
        return line

    return logged_input


def main():
    args = parse_args()
    script_path = Path(args.script).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    using_input_log = bool(args.input)

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    original_input = builtins.input
    original_argv = sys.argv[:]

    if using_input_log:
        input_path = Path(args.input).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        input_lines = input_path.read_text(encoding=args.encoding).splitlines()
        builtins.input = make_logged_input(input_lines)
    else:
        builtins.input = make_live_logged_input(original_input)

    sys.argv = [str(script_path)]

    try:
        with output_path.open("w", encoding=args.encoding, newline="") as log_file:
            tee_stdout = Tee(sys.stdout, log_file)
            tee_stderr = Tee(sys.stderr, log_file)
            with contextlib.redirect_stdout(tee_stdout), contextlib.redirect_stderr(tee_stderr):
                try:
                    runpy.run_path(str(script_path), run_name="__main__")
                except EOFError:
                    if using_input_log:
                        print("EOF reached: input file does not contain enough lines.")
                    else:
                        raise
    finally:
        builtins.input = original_input
        sys.argv = original_argv


if __name__ == "__main__":
    main()