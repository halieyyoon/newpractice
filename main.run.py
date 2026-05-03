"""
=============================================================
  run.py — 입출력 번호 기록 래퍼
=============================================================
사용법:
    python run.py main.py

모든 입력과 출력을 번호붙여서 기록한다.
    player_input.txt  ← 입력 기록
    game_output.txt   ← 출력 기록 (입력 프롬프트 포함)
=============================================================
"""

import sys
import os
import io
import runpy


class NumberedLogger:
    """입력/출력을 번호붙여서 파일에 저장하는 래퍼."""

    def __init__(self, input_file="player_input.txt", output_file="game_output.txt"):
        self.input_file = input_file
        self.output_file = output_file
        self.counter = 0
        self.input_lines = []
        self.output_lines = []
        self._input_buffer = []
        self._output_buffer = ""

        # 파일 초기화
        open(self.input_file, "w", encoding="utf-8").close()
        open(self.output_file, "w", encoding="utf-8").close()

    def next_num(self):
        self.counter += 1
        return self.counter

    def log_output(self, text):
        num = self.next_num()
        line = f"[{num}] {text}"
        self.output_lines.append(line)
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_input(self, text):
        num = self.next_num()
        line = f"[{num}] 입력: {text}"
        self.input_lines.append(line)
        with open(self.input_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # 출력 파일에도 입력 기록
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


logger = NumberedLogger()
_original_stdout = sys.stdout
_original_stdin = sys.stdin


class LoggedStdout(io.TextIOBase):
    """print() 출력을 가로채서 번호붙여 기록."""

    def __init__(self, original):
        self.original = original
        self._pending = ""

    def write(self, text):
        self.original.write(text)
        self.original.flush()
        self._pending += text
        # 줄 단위로 기록
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            if line.strip():  # 빈 줄 제외
                logger.log_output(line)
        return len(text)

    def flush(self):
        self.original.flush()

    def fileno(self):
        return self.original.fileno()

    @property
    def encoding(self):
        return self.original.encoding

    @property
    def errors(self):
        return getattr(self.original, 'errors', 'strict')


class LoggedStdin(io.TextIOBase):
    """input() 입력을 가로채서 번호붙여 기록."""

    def __init__(self, original):
        self.original = original

    def readline(self):
        line = self.original.readline()
        text = line.rstrip("\n")
        if text:
            logger.log_input(text)
        return line

    def fileno(self):
        return self.original.fileno()

    @property
    def encoding(self):
        return self.original.encoding

    @property
    def errors(self):
        return getattr(self.original, 'errors', 'strict')


def main():
    if len(sys.argv) < 2:
        print("사용법: python run.py main.py")
        sys.exit(1)

    target = sys.argv[1]
    if not os.path.exists(target):
        print(f"파일을 찾을 수 없어: {target}")
        sys.exit(1)

    # stdin/stdout 교체
    sys.stdout = LoggedStdout(_original_stdout)
    sys.stdin = LoggedStdin(_original_stdin)

    try:
        # main.py 실행
        runpy.run_path(target, run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:
        sys.stdout = _original_stdout
        print(f"오류: {e}")
        raise
    finally:
        sys.stdout = _original_stdout
        sys.stdin = _original_stdin
        print(f"\n입력 기록 → {logger.input_file}")
        print(f"출력 기록 → {logger.output_file}")


if __name__ == "__main__":
    main()