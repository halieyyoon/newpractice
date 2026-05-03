import json
import os
import glob
import pickle
from datetime import datetime
import sys
import io

# ────────────────────────────────────────
# 로깅 시스템
# python run.py main.py로 실행해도 main.py가 직접
# player_input.txt, game_output.txt를 번호 형식으로 저장합니다.
# ────────────────────────────────────────
class SimpleLogger:
    def __init__(self, input_file="player_input.txt", output_file="game_output.txt"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_file = os.path.join(base_dir, input_file)
        self.output_file = os.path.join(base_dir, output_file)
        self.input_counter = 0
        self.output_counter = 0
        self.reset_files()

    def reset_files(self):
        self.input_counter = 0
        self.output_counter = 0
        open(self.input_file, "w", encoding="utf-8").close()
        open(self.output_file, "w", encoding="utf-8").close()

    def next_input_num(self):
        self.input_counter += 1
        return self.input_counter

    def next_output_num(self):
        self.output_counter += 1
        return self.output_counter

    def log_input(self, text):
        input_line = f"[{self.next_input_num()}] 입력: {text}"
        output_line = f"[{self.next_output_num()}] 입력: {text}"
        with open(self.input_file, "a", encoding="utf-8") as f:
            f.write(input_line + "\n")
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(output_line + "\n")

    def log_output(self, text):
        if text.strip():
            line = f"[{self.next_output_num()}] {text}"
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")


class LoggedStdout(io.TextIOBase):
    def __init__(self, original, active_logger):
        self.original = original
        self.logger = active_logger
        self._pending = ""
        self.capture_enabled = True

    def write(self, text):
        self.original.write(text)
        self.original.flush()

        if self.capture_enabled:
            self._pending += text
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", 1)
                self.logger.log_output(line)

        return len(text)

    def flush(self):
        if self.capture_enabled and self._pending.strip():
            self.logger.log_output(self._pending)
            self._pending = ""
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
        return self.original.readline()

    def fileno(self):
        return self.original.fileno()

    @property
    def encoding(self):
        return self.original.encoding


logger = SimpleLogger()
CONSOLE_STDIN = None
CONSOLE_STDOUT = None


def unwrap_stream(stream, attr="original"):
    while hasattr(stream, attr):
        stream = getattr(stream, attr)
    return stream

MAP = [
    ["종합관", "본관", "경영관", "노천극장", "새천년관", "이윤재관"],
    ["백양관", "백양로5", "대강당", "음악관", "알렌관", "ABMRC"],
    ["중앙도서관", "독수리상", "학생회관", "루스채플", "재활병원", "치과대학"],
    ["체육관", "백양로3", "공터2", "광혜원", "어린이병원", "세브란스"],
    ["공학관", "백양로2", "백주년기념관", "안과병원", "제중관", None],
    ["공학원", "백양로1", "공터1", "암병원", "의과대학", None],
    ["연대앞 버스정류장", "정문", "스타벅스", "세브란스병원 버스정류장", None, None],
]

ROWS = len(MAP)
COLS = len(MAP[0])

DIRECTIONS = {
    "북": (-1, 0),
    "남": (1, 0),
    "서": (0, -1),
    "동": (0, 1),
}

START_POS = [6, 0]
SAVE_EXT = ".sav.json"
EVENTS_FILE = "events.bin"

DIFFICULTY_HP = {
    "보통": 1.0,
    "어려움": 2.0,
}

INPUT_LOG = []


def ask(prompt="입력: "):
    global CONSOLE_STDIN, CONSOLE_STDOUT

    out = CONSOLE_STDOUT if CONSOLE_STDOUT is not None else sys.stdout
    inp = CONSOLE_STDIN if CONSOLE_STDIN is not None else sys.stdin

    out.write(prompt)
    out.flush()

    line = inp.readline()
    if line == "":
        raise EOFError

    value = line.rstrip("\n").strip()
    INPUT_LOG.append(value)
    logger.log_input(value)
    return value


def format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def is_valid_cell(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS and MAP[r][c] is not None


def location_particle(name):
    if name == "정문":
        return "으로"
    return "에"


def load_events():
    default = {
        "events": {
            "노천극장": "아카라카 공연 티켓 암표 거래가 이루어지고 있다.",
            "대강당": "행사 도시락이 상온에 오래 방치되어 식중독 의심 증상이 보고되었다.",
            "중앙도서관": "자리에 짐을 잔뜩 올려서 차지하고, 키오스크에서 배석받은 학생이 와도 비켜주지 않는 빌런이 있다.",
            "공터2": "학생회관에서 버린 음식물쓰레기가 부패하여 학생회관으로 흘러들어가고있다!",
        },
        "answers": {
            "교내 부조리 수사": "노천극장",
            "교내 위생사건 수사": "대강당",
        },
    }

    if not os.path.exists(EVENTS_FILE):
        return default

    try:
        with open(EVENTS_FILE, "rb") as f:
            data = pickle.load(f)

        if "events" not in data:
            data["events"] = {}
        if "answers" not in data:
            data["answers"] = {}

        for k, v in default["events"].items():
            data["events"].setdefault(k, v)
        for k, v in default["answers"].items():
            data["answers"].setdefault(k, v)

        return data

    except Exception as e:
        print(f"사건 파일 로드 실패: {e}")
        print("기본 사건 정보를 사용합니다.")
        return default


class Quest:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.completed = False

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "completed": self.completed,
        }

    @staticmethod
    def from_dict(d):
        q = Quest(d["name"], d["description"])
        q.completed = d["completed"]
        return q


class Player:
    def __init__(self):
        self.hp = 10.0
        self.money = 10000
        self.pos = list(START_POS)
        self.bag = []
        self.hunger = True

    def move(self, direction, difficulty):
        if direction not in DIRECTIONS:
            print("동/서/남/북 중 하나를 입력해.")
            return False

        dr, dc = DIRECTIONS[direction]
        nr, nc = self.pos[0] + dr, self.pos[1] + dc

        if not is_valid_cell(nr, nc):
            print("그 방향은 막혔어.")
            return False

        self.pos = [nr, nc]
        self.hp -= DIFFICULTY_HP[difficulty]
        return True

    def location(self):
        r, c = self.pos
        return MAP[r][c]

    def print_status(self, env):
        r, c = self.pos
        neighbors = {}
        for dname, (dr, dc) in DIRECTIONS.items():
            nr, nc = r + dr, c + dc
            neighbors[dname] = MAP[nr][nc] if is_valid_cell(nr, nc) else "막힘"

        print(f"계좌의 잔액 = {self.money:,}원")
        print(f"HP = {format_number(self.hp)}")
        print(f"현재위치 = {self.location()}")
        print(f"동서남북 = {neighbors['동']}, {neighbors['서']}, {neighbors['남']}, {neighbors['북']}")

    def add_to_bag(self, item_template):
        for item in self.bag:
            if item["name"] == item_template["name"]:
                item["qty"] = item.get("qty", 1) + 1
                return

        new_item = dict(item_template)
        new_item["qty"] = 1
        self.bag.append(new_item)

    def remove_from_bag(self, name, qty=1):
        for item in self.bag:
            if item["name"] == name:
                item["qty"] = item.get("qty", 1) - qty
                if item["qty"] <= 0:
                    self.bag.remove(item)
                return True
        return False

    def show_bag(self):
        if not self.bag:
            print("가방이 비어있어.")
            return False

        item_texts = []
        for item in self.bag:
            qty = item.get("qty", 1)
            display_name = "라떼" if item["name"] == "카페라떼" else item["name"]
            item_texts.append(f"{display_name} x{qty}")

        print(f"가방을 엽니다 [{', '.join(item_texts)}]")
        return True

    def use_item(self, choice):
        if not self.bag:
            print("가방이 비어있어.")
            return

        target = None

        if str(choice).isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(self.bag):
                target = self.bag[idx]
            else:
                print(f"{choice}번 물건은 가방에 없어.")
                return
        else:
            aliases = {
                "라떼": "카페라떼",
                "카페라떼": "카페라떼",
                "두쫀쿠": "두쫀쿠",
            }
            search_name = aliases.get(choice, choice)
            for item in self.bag:
                if item["name"] == search_name:
                    target = item
                    break

        if target is None:
            print(f"{choice}는 가방에 없어.")
            return

        self.hp += target["hp_effect"]
        name = target["name"]
        self.remove_from_bag(name, 1)
        print(f"{name}를 먹었습니다. HP={format_number(self.hp)}")

        if self.hp > 10:
            self.hunger = False

    def to_dict(self):
        return {
            "hp": self.hp,
            "money": self.money,
            "pos": self.pos,
            "bag": self.bag,
            "hunger": self.hunger,
        }

    @staticmethod
    def from_dict(d):
        p = Player()
        p.hp = d["hp"]
        p.money = d["money"]
        p.pos = d["pos"]
        p.bag = d["bag"]
        p.hunger = d["hunger"]
        return p


class Place:
    BUY_CATALOG = {
        "학생회관": [
            {"name": "두쫀쿠", "price": 5000, "hp_effect": 10},
            {"name": "카페라떼", "price": 3000, "hp_effect": 5},
        ],
        "스타벅스": [
            {"name": "두쫀쿠", "price": 4000, "hp_effect": 10},
            {"name": "카페라떼", "price": 2000, "hp_effect": 5},
        ],
        "ABMRC": [
            {"name": "두쫀쿠", "price": 4000, "hp_effect": 10},
            {"name": "카페라떼", "price": 2000, "hp_effect": 5},
        ],
    }

    SELL_GROUP_A = {
        "체육관",
        "공학관",
        "공학원",
        "재활병원",
        "어린이병원",
        "종합관",
        "노천극장",
    }
    SELL_PRICE_A = {"두쫀쿠": 7000, "카페라떼": 4000}

    SELL_GROUP_B = {
        "중앙도서관",
        "백양관",
        "대강당",
        "백주년기념관",
        "안과병원",
        "암병원",
        "새천년관",
        "알렌관",
        "제중관",
        "의과대학",
        "치과대학",
        "세브란스",
        "본관",
        "경영관",
    }
    SELL_PRICE_B = {"두쫀쿠": 6000, "카페라떼": 3000}

    QUEST_PLACES = {"정문", "독수리상", "본관", "세브란스", "이윤재관"}

    def __init__(self, name, events_data):
        self.name = name
        self.event_info = events_data["events"].get(name)
        self.answers = events_data["answers"]

    def sell_prices(self):
        if self.name in self.SELL_GROUP_A:
            return self.SELL_PRICE_A
        if self.name in self.SELL_GROUP_B:
            return self.SELL_PRICE_B
        return None

    def available_interactions(self):
        acts = []
        if self.name in self.BUY_CATALOG:
            acts.append("구매")
        if self.sell_prices():
            acts.append("판매")
        if self.name in self.QUEST_PLACES:
            acts.append("임무")
        return acts

    def arrive_message(self):
        parts = []
        location = self.name

        if location == "정문":
            msg = f"{location}으로 이동했다."
        elif location in ("스타벅스",):
            msg = f"{location}로 이동했다."
        else:
            msg = f"{location}에 도착했다."

        if self.event_info:
            msg += f" {self.event_info}"
            if location == "중앙도서관":
                msg += " 저런!"

        acts = self.available_interactions()
        if acts:
            msg += f" [{', '.join(acts)}]"

        return msg

    def interact_buy(self, player):
        items = self.BUY_CATALOG.get(self.name)
        if not items:
            print("여기선 살 수 있는 게 없어.")
            return

        print(f"1) 두쫀쿠: {items[0]['price']}원, HP가 {items[0]['hp_effect']}만큼 증가한다.")
        print(f"2) {items[1]['name']}: {items[1]['price']}원, HP가 {items[1]['hp_effect']}만큼 증가한다.")
        print("3) 종료")

        while True:
            choice = ask("입력: ")

            if choice == "3" or choice == "종료":
                print("구매를 종료합니다.")
                break

            item = None
            if choice == "1":
                item = items[0]
            elif choice == "2":
                item = items[1]

            if item is None:
                print("잘못된 선택입니다.")
                continue

            if player.money < item["price"]:
                print(f"{item['name']} 구매를 실패했다. 계좌 잔액이 부족하다.")
            else:
                player.money -= item["price"]
                player.add_to_bag(item)
                print(f"{item['name']}를 구매해서 가방에 넣었다. 계좌 잔액 = {player.money}원")

    def interact_sell(self, player):
        prices = self.sell_prices()

        if not prices:
            print("여기선 팔 수 있는 곳이 아니야.")
            return

        while True:
            sellable = [item for item in player.bag if item["name"] in prices]

            if not sellable:
                print("팔 것이 없어서 종료합니다.")
                break

            print("무엇을 판매하시겠습니까?")
            for i, item in enumerate(sellable, 1):
                print(f"{i}) {item['name']} x1")
            print(f"{len(sellable) + 1}) 종료")

            choice = ask("입력: ")

            if choice == str(len(sellable) + 1):
                print("판매를 종료합니다.")
                break

            if choice.isdigit() and 1 <= int(choice) <= len(sellable):
                item = sellable[int(choice) - 1]
                earned = prices[item["name"]]
                player.money += earned
                player.remove_from_bag(item["name"], 1)
                print(f"{item['name']}를 판매해서 {earned}원을 벌었다. 계좌 잔액 = {player.money}원")
            else:
                print("잘못된 선택입니다.")

    def interact_quest(self, player, quests):
        if self.name == "정문":
            return _q_jeonmun(quests)
        if self.name == "독수리상":
            return _q_eagle(quests)
        if self.name == "본관":
            return _q_bonkwan(quests, self.answers)
        if self.name == "세브란스":
            return _q_severance(quests, self.answers)
        if self.name == "이윤재관":
            return _q_yunjae(quests)

        print("여기선 받을 임무가 없어.")
        return None


def _find_quest(quests, name):
    for q in quests:
        if q.name == name:
            return q
    return None


def _q_jeonmun(quests):
    if _find_quest(quests, "독수리상 방문") is None:
        q = Quest(
            "독수리상 방문",
            "학교에서 어떤 일들이 일어나고있는지 소식들이 모이는 독수리상에서 알아보자.",
        )
        quests.append(q)
        print("학교에서 어떤 일들이 일어나고있는지 소식들이 모이는")
        print("독수리상에서 알아보자.")
        print("[임무목록]에 임무가 추가되었습니다.")
    else:
        print("이미 독수리상 임무를 받았습니다.")
    return None


def _q_eagle(quests):
    q0 = _find_quest(quests, "독수리상 방문")

    if q0 and not q0.completed:
        q0.completed = True
        print("다음의 임무가 해결되었다! [학교에서 어떤 일들이")
        print("일어나고있는지 소식들이 모이는 독수리상에서")
        print("알아보자.]")

    quest_data = [
        (
            "교내 부조리 수사",
            "교내 어딘가에서 부조리가 일어나고있다. 이동하고 상호작용을 해서 부조리를 찾아서 본관에 보고하라.",
        ),
        (
            "교내 위생사건 수사",
            "학생들이 단체로 식중독에 걸렸다. 이동하고 상호작용을 해서 위생사건의 원인을 찾아서 세브란스에 보고하라.",
        ),
    ]

    for name, desc in quest_data:
        if _find_quest(quests, name) is None:
            quests.append(Quest(name, desc))
            if name == "교내 부조리 수사":
                print("교내 부조리 수사 - 교내 어딘가에서 부조리가")
                print("일어나고있다. 이동하고 상호작용을 해서 부조리를 찾아서")
                print("본관에 보고하라.")
            else:
                print("교내 위생사건 수사 - 학생들이 단체로 식중독에 걸렸다.")
                print("이동하고 상호작용을 해서 위생사건의 원인을 찾아서")
                print("세브란스에 보고하라.")

    return None


def _q_bonkwan(quests, answers):
    q = _find_quest(quests, "교내 부조리 수사")

    if q is None:
        print("교내 부조리 수사 임무가 없습니다.")
        return None

    if q.completed:
        print("이미 해결된 임무입니다.")
        return None

    correct = answers.get("교내 부조리 수사", "")
    print("교내 어디에 부조리가 있나?")
    ans = ask("입력: ")

    if ans == correct:
        q.completed = True
        print("다음의 임무가 해결되었다! [교내 부조리 수사]")
        print("수업들으러 이윤재관 가야지!")
    else:
        print("틀렸습니다. 더 조사해보세요.")

    return None


def _q_severance(quests, answers):
    q = _find_quest(quests, "교내 위생사건 수사")

    if q is None:
        print("교내 위생사건 수사 임무가 없습니다.")
        return None

    if q.completed:
        print("이미 해결된 임무입니다.")
        return None

    correct = answers.get("교내 위생사건 수사", "")
    print("교내 어디에 식중독 원인이 있나?")
    ans = ask("입력: ")

    if ans == correct:
        q.completed = True
        print("다음의 임무가 해결되었다! [교내 위생사건 수사]")
        print("수업들으러 이윤재관 가야지!")
    else:
        print("틀렸습니다. 더 조사해보세요.")

    return None


def _q_yunjae(quests):
    q0 = _find_quest(quests, "독수리상 방문")
    if q0 is None or not q0.completed:
        print("독수리상에서 임무를 먼저 받아와!")
        return None

    c1 = _find_quest(quests, "교내 부조리 수사")
    c2 = _find_quest(quests, "교내 위생사건 수사")

    done1 = c1 is not None and c1.completed
    done2 = c2 is not None and c2.completed

    if done1 and done2:
        print("부조리와 식중독 수사를 완료했구나! 수업은 이걸로 끝입니다. 또 만나요~")
        return "END"
    if done1:
        print("부조리 수사를 완료했구나! 식중독 원인도 찾아주세요~")
    elif done2:
        print("식중독 수사를 완료했구나! 부조리도 찾아주세요~")
    else:
        print("아직 수사 임무를 완료하지 않았어!")

    return None


def show_quests(quests):
    active = [q for q in quests if not q.completed]

    if not active:
        print("현재 진행 중인 임무가 없습니다.")
        return

    for q in active:
        if q.name == "교내 부조리 수사":
            print("교내 부조리 수사 - 교내 어딘가에서 부조리가")
            print("일어나고있다. 이동하고 상호작용을 해서 부조리를 찾아서")
            print("본관에 보고하라.")
        elif q.name == "교내 위생사건 수사":
            print("교내 위생사건 수사 - 학생들이 단체로 식중독에 걸렸다.")
            print("이동하고 상호작용을 해서 위생사건의 원인을 찾아서")
            print("세브란스에 보고하라.")
        else:
            print(f"{q.name} - {q.description}")


def show_difficulty(env):
    print(f"현재 난이도: {env['difficulty']}")
    print("1. 보통")
    print("2. 어려움")
    print("3. 취소")

    choice = ask("입력: ")

    if choice == "1":
        env["difficulty"] = "보통"
        print("난이도가 보통으로 변경되었습니다.")
    elif choice == "2":
        env["difficulty"] = "어려움"
        print("난이도가 어려움으로 변경되었습니다.")
    elif choice == "3":
        print("난이도 변경을 취소합니다.")
    else:
        print("잘못된 선택입니다.")


def save_game(player, env, quests, input_log):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"save_{timestamp}{SAVE_EXT}"

    save_data = {
        "player": player.to_dict(),
        "env": env,
        "quests": [q.to_dict() for q in quests],
        "input_log": input_log,
        "saved_at": timestamp,
    }

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"저장 완료 -> {filename}")
    except Exception as e:
        print(f"저장 실패: {e}")


def load_game():
    save_files = sorted(glob.glob(f"*{SAVE_EXT}"))

    print("불러오기")
    if save_files:
        print("현재 폴더의 저장 파일:")
        for i, file_name in enumerate(save_files, 1):
            print(f"{i}. {file_name}")
    else:
        print("현재 폴더에 저장 파일이 없습니다.")

    print("번호를 입력하면 목록에서 선택합니다.")
    print("경로를 입력하면 상대경로 또는 절대경로로 불러옵니다.")
    print("0. 취소")

    choice = ask("입력: ")

    if choice == "0":
        print("불러오기를 취소합니다.")
        return None

    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(save_files):
            filepath = save_files[idx]
        else:
            print("잘못된 번호입니다.")
            return None
    else:
        filepath = os.path.abspath(choice)
        if not os.path.exists(filepath):
            print(f"파일을 찾을 수 없습니다: {choice}")
            return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        player = Player.from_dict(data["player"])
        env = data["env"]
        quests = [Quest.from_dict(q) for q in data.get("quests", [])]
        input_log = data.get("input_log", [])

        print(f"불러오기 완료! 저장 시각: {data.get('saved_at', '알 수 없음')}")
        print(f"위치: {player.location()} | HP: {format_number(player.hp)} | 잔액: {player.money:,}원")

        return player, env, quests, input_log

    except Exception as e:
        print(f"불러오기 실패: {e}")
        return None


def print_help():
    print("명령어 목록")
    print("북 / 남 / 동 / 서 : 이동")
    print("상태 : HP, 잔액, 위치, 인접칸 확인")
    print("가방 : 가방 아이템 확인 및 사용")
    print("사용 이름 또는 번호 : 아이템 사용")
    print("구매 : 현재 장소에서 구매")
    print("판매 : 현재 장소에서 판매")
    print("임무 : 현재 장소 임무 상호작용")
    print("임무목록 : 보유 임무 목록 출력")
    print("상호작용 : 가능한 상호작용 목록")
    print("저장 : 게임 저장")
    print("불러오기 : 저장된 게임 불러오기")
    print("난이도 : 난이도 확인 및 변경")
    print("도움말 : 명령어 목록 출력")
    print("종료 : 게임 종료")


def process_command(cmd, player, env, quests, places, input_log):
    tokens = cmd.split()

    if not tokens:
        return None

    action = tokens[0]
    place = places.get(player.location())

    if action in DIRECTIONS:
        moved = player.move(action, env["difficulty"])
        if moved:
            new_place = places.get(player.location())
            if new_place:
                print(new_place.arrive_message())

    elif action == "상태":
        player.print_status(env)

    elif action == "가방":
        has_item = player.show_bag()
        if has_item:
            item_choice = ask("입력: ")
            if item_choice:
                player.use_item(item_choice)

    elif action == "사용":
        if len(tokens) < 2:
            print("사용할 아이템 이름 또는 번호를 입력하세요.")
        else:
            player.use_item(" ".join(tokens[1:]))

    elif action in ("두쫀쿠", "카페라떼", "라떼"):
        player.use_item(action)

    elif action == "구매":
        if place:
            place.interact_buy(player)
        else:
            print("알 수 없는 장소입니다.")

    elif action == "판매":
        if place:
            place.interact_sell(player)
        else:
            print("알 수 없는 장소입니다.")

    elif action == "임무":
        if place:
            result = place.interact_quest(player, quests)
            if result == "END":
                return "quit"
        else:
            print("알 수 없는 장소입니다.")

    elif action == "임무목록":
        show_quests(quests)

    elif action == "상호작용":
        if place:
            acts = place.available_interactions()
            if acts:
                print(f"가능한 상호작용: {', '.join(acts)}")
            else:
                print("여기선 특별한 상호작용이 없습니다.")
        else:
            print("알 수 없는 장소입니다.")

    elif action == "저장":
        save_game(player, env, quests, input_log)

    elif action == "불러오기":
        result = load_game()
        if result is not None:
            return ("load", result)

    elif action == "난이도":
        show_difficulty(env)

    elif action == "도움말":
        print_help()

    elif action == "종료":
        print("게임을 종료합니다.")
        return "quit"

    else:
        print("알 수 없는 명령입니다.")

    return None


def select_difficulty(env):
    print("난이도 설명")
    print("보통: 한 칸 이동할 때마다 HP가 1만큼 감소합니다.")
    print("어려움: 한 칸 이동할 때마다 HP가 2만큼 감소합니다.")
    print("난이도를 선택하세요.")
    print("1. 보통")
    print("2. 어려움")

    while True:
        choice = ask("입력: ")

        if choice == "1" or choice == "보통":
            env["difficulty"] = "보통"
            print("난이도가 보통으로 설정되었습니다.")
            break
        if choice == "2" or choice == "어려움":
            env["difficulty"] = "어려움"
            print("난이도가 어려움으로 설정되었습니다.")
            break

        print("올바른 번호를 입력해주세요.")


def main():
    global INPUT_LOG, CONSOLE_STDIN, CONSOLE_STDOUT

    original_stdout = sys.stdout
    original_stdin = sys.stdin

    CONSOLE_STDOUT = unwrap_stream(original_stdout)
    CONSOLE_STDIN = unwrap_stream(original_stdin)

    logger.reset_files()
    sys.stdout = LoggedStdout(CONSOLE_STDOUT, logger)
    sys.stdin = LoggedStdin(CONSOLE_STDIN)

    try:
        _run_game()
    finally:
        sys.stdout.flush()
        sys.stdout = original_stdout
        sys.stdin = original_stdin


def _run_game():
    global INPUT_LOG

    events_data = load_events()
    places = {
        name: Place(name, events_data)
        for row in MAP
        for name in row
        if name is not None
    }

    player = Player()
    env = {"time": 11, "difficulty": "보통"}
    quests = []
    INPUT_LOG = []

    select_difficulty(env)

    print("송도 생활을 마치고 신촌에 처음 도착했다. 연대앞")
    print("버스정류장이다.")

    while True:
        try:
            cmd = ask("입력: ")
        except (EOFError, KeyboardInterrupt):
            print("게임을 종료합니다.")
            break

        if not cmd:
            continue

        result = process_command(cmd, player, env, quests, places, INPUT_LOG)

        if result == "quit":
            break

        if isinstance(result, tuple) and result[0] == "load":
            _, (player, env, quests, loaded_log) = result
            INPUT_LOG = loaded_log

        if player.hp <= 0:
            print("HP가 0 이하야! 너무 배고파서 쓰러질 것 같아. 무언가를 먹어야 해!")


if __name__ == "__main__":
    main()
