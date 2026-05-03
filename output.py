import sys
import os
import runpy
import io

class NewNumberedLogger:
    def __init__(self, input_file="player_input.txt", output_file="game_output.txt"):
        # 실행 위치를 현재 파이썬 파일이 있는 폴더로 강제 지정
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_file = os.path.join(base_dir, input_file)
        self.output_file = os.path.join(base_dir, output_file)
        self.counter = 0
        
        # 시작 시 파일 초기화
        open(self.input_file, "w", encoding="utf-8").close()
        open(self.output_file, "w", encoding="utf-8").close()

    def next_num(self):
        self.counter += 1
        return self.counter

    def log_input(self, text):
        num = self.next_num()
        line = f"[{num}] 입력: {text}"
        with open(self.input_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def log_output(self, text):
        if text.strip():
            num = self.next_num()
            line = f"[{num}] {text}"
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")

logger = NewNumberedLogger()

class LoggedStdout(io.TextIOBase):
    def __init__(self, original):
        self.original = original
        self._pending = ""

    def write(self, text):
        self.original.write(text)
        self.original.flush()
        self._pending += text
        while "\n" in self._pending:
            line, self._pending = self._pending.split("\n", 1)
            if line.strip():
                logger.log_output(line)
        return len(text)

    def flush(self):
        self.original.flush()

    def fileno(self):
        return self.original.fileno()

    @property
    def encoding(self):
        return self.original.encoding

class LoggedStdin(io.TextIOBase):
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

def main():
    if len(sys.argv) < 2:
        print("사용법: python run.py main.py")
        sys.exit(1)

    target = sys.argv[1]
    # 절대 경로 기준으로 파일이 있는지 확인
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), target)
    if not os.path.exists(target_path):
        print(f"파일을 찾을 수 없습니다: {target_path}")
        sys.exit(1)

    _original_stdout = sys.stdout
    _original_stdin = sys.stdin
    sys.stdout = LoggedStdout(_original_stdout)
    sys.stdin = LoggedStdin(_original_stdin)

    try:
        runpy.run_path(target_path, run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:
        sys.stdout = _original_stdout
        sys.stdin = _original_stdin
        raise
    finally:
        sys.stdout = _original_stdout
        sys.stdin = _original_stdin
        print(f"\n[작업 완료] 입력 기록 -> {logger.input_file} | 출력 기록 -> {logger.output_file}")

if __name__ == "__main__":
    main()