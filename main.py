import json
import os
import glob
import pickle
from datetime import datetime
import sys
import io

# ────────────────────────────────────────
# 로깅 시스템
# ────────────────────────────────────────
class SimpleLogger:
    def __init__(self, input_file="player_input.txt", output_file="game_output.txt"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.input_file = os.path.join(base_dir, input_file)
        self.output_file = os.path.join(base_dir, output_file)
        self.counter = 0
        
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

logger = SimpleLogger()

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
        if text.strip():
            logger.log_input(text)
        return line

    def fileno(self):
        return self.original.fileno()

    @property
    def encoding(self):
        return self.original.encoding


MAP = [
    ["종합관",        "본관",    "경영관",    "노천극장",                   "새천년관",    "이윤재관"],
    ["백양관",        "백양로5", "대강당",      "음악관",                     "알렌관",      "ABMRC"],
    ["중앙도서관",    "독수리상","학생회관",    "루스채플",                   "재활병원",    "치과대학"],
    ["체육관",        "백양로3", "공터2",       "광혜원",                     "어린이병원",  "세브란스"],
    ["공학관",        "백양로2", "백주년기념관","안과병원",                   "제중관",      "None"],
    ["공학원",        "백양로1", "공터1",       "암병원",                     "의과대학",    "None"],
    ["연대앞 버스정류장","정문", "스타벅스",    "세브란스병원 버스정류장", "None",        "None"],
]

ROWS = len(MAP)
COLS = len(MAP[0])

DIRECTIONS = {
    "북": (-1,  0),
    "남": ( 1,  0),
    "서": ( 0, -1),
    "동": ( 0,  1),
}

START_POS   = [6, 0]
SAVE_EXT    = ".sav.json"
EVENTS_FILE = "events.bin"

DIFFICULTY_HP = {
    "보통":   1.0,
    "어려움": 2.0,
}

def is_valid_cell(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS and MAP[r][c] is not None

def load_events():
    default = {
        "events": {
            "노천극장":   "아카라카 공연 티켓 암표 거래가 이루어지고 있다.",
            "대강당":     "행사 도시락이 상온에 오래 방치되어 식중독 의심 증상이 보고되었다.",
            "중앙도서관": "자리에 짐을 잔뜩 올려서 차지하고, 키오스크에서 배석받은 학생이 와도 비켜주지 않는 빌런이 있다.",
            "공터2":      "학생회관에서 버린 음식물쓰레기가 부패하여 학생회관으로 흘러들어가고 있다!",
        },
        "answers": {
            "교내 부조리 수사":  "노천극장",
            "교내 위생사건 수사": "대강당",
        }
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
        print(f"[경고] 사건 파일 로드 실패: {e} -> 기본값 사용")
        return default


class Quest:
    def __init__(self, name, description):
        self.name        = name
        self.description = description
        self.completed   = False

    def to_dict(self):
        return {"name": self.name, "description": self.description, "completed": self.completed}

    @staticmethod
    def from_dict(d):
        q = Quest(d["name"], d["description"])
        q.completed = d["completed"]
        return q


class Player:
    def __init__(self):
        self.hp     = 10.0
        self.money  = 10000
        self.pos    = list(START_POS)
        self.bag    = []
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
        hp_loss = DIFFICULTY_HP[difficulty]
        self.hp -= hp_loss
        print(f"{self.location()}로 이동했다.")
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
        print(f"HP = {self.hp}")
        print(f"현재위치 = {self.location()}")
        print(f"동서남북 = {neighbors['동']}, {neighbors['서']}, {neighbors['남']}, {neighbors['북']}")

    def add_to_bag(self, item_template):
        for it in self.bag:
            if it["name"] == item_template["name"]:
                it["qty"] = it.get("qty", 1) + 1
                return
        new_item = dict(item_template)
        new_item["qty"] = 1
        self.bag.append(new_item)

    def remove_from_bag(self, name, qty=1):
        for it in self.bag:
            if it["name"] == name:
                it["qty"] = it.get("qty", 1) - qty
                if it["qty"] <= 0:
                    self.bag.remove(it)
                return True
        return False

    def show_bag(self):
        if not self.bag:
            print("가방이 비어있어.")
            return False
        print("가방 속 물건:")
        for i, item in enumerate(self.bag, 1):
            qty = item.get("qty", 1)
            print(f" {i}) {item['name']}: {item['hp_effect']}만큼 증가한다.")
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
                print(f"'{choice}' 는 잘못된 번호야.")
                return
        else:
            for item in self.bag:
                if item["name"] == choice:
                    target = item
                    break
        if target is None:
            print(f"'{choice}' 는 가방에 없어.")
            return
        self.hp += target["hp_effect"]
        name = target["name"]
        self.remove_from_bag(name, 1)
        print(f"{name}를 먹었습니다. HP={self.hp}")
        if self.hp > 10:
            self.hunger = False

    def to_dict(self):
        return {
            "hp":     self.hp,
            "money":  self.money,
            "pos":    self.pos,
            "bag":    self.bag,
            "hunger": self.hunger,
        }

    @staticmethod
    def from_dict(d):
        p = Player()
        p.hp     = d["hp"]
        p.money  = d["money"]
        p.pos    = d["pos"]
        p.bag    = d["bag"]
        p.hunger = d["hunger"]
        return p


class Place:
    BUY_CATALOG = {
        "학생회관": [
            {"name": "두쫀쿠",   "price": 5000, "hp_effect": 10},
            {"name": "카페라떼", "price": 3000, "hp_effect": 5},
        ],
        "스타벅스": [
            {"name": "두쫀쿠",   "price": 4000, "hp_effect": 10},
            {"name": "카페라떼", "price": 2000, "hp_effect": 5},
        ],
        "ABMRC": [
            {"name": "두쫀쿠",   "price": 4000, "hp_effect": 10},
            {"name": "카페라떼", "price": 2000, "hp_effect": 5},
        ],
    }
    SELL_GROUP_A = {"체육관", "공학관", "공학원", "재활병원", "어린이병원", "종합관", "노천극장"}
    SELL_PRICE_A = {"두쫀쿠": 7000, "카페라떼": 4000}
    SELL_GROUP_B = {
        "중앙도서관","백양관","대강당","백주년기념관",
        "안과병원","암병원","새천년관","알렌관","제중관",
        "의과대학","치과대학","세브란스","본관","경영관",
    }
    SELL_PRICE_B = {"두쫀쿠": 6000, "카페라떼": 3000}
    QUEST_PLACES = {"정문", "독수리상", "본관", "세브란스", "이윤재관"}

    def __init__(self, name, events_data):
        self.name       = name
        self.event_info = events_data["events"].get(name)
        self.answers    = events_data["answers"]

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

    def print_event(self):
        if self.event_info:
            print(f"[{self.event_info}]")

    def interact_buy(self, player):
        items = self.BUY_CATALOG.get(self.name)
        if not items:
            print("여기선 살 수 있는 게 없어.")
            return
            
        buy_msg = f"1) 두쫀쿠: {items[0]['price']}원, HP가 {items[0]['hp_effect']}만큼 증가한다.\n" \
                  f"2) {items[1]['name']}: {items[1]['price']}원, HP가 {items[1]['hp_effect']}만큼 증가한다.\n" \
                  f"3) 종료"
        print(buy_msg)
        
        while True:
            choice = input("입력: ").strip()
            if choice == "3" or choice == "종료":
                print("구매를 종료합니다.")
                break
            
            item = None
            if choice == "1":
                item = items[0]
            elif choice == "2":
                item = items[1]
                
            if item is None:
                print("1~3번 중에서 선택해.")
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
            sellable = [it for it in player.bag if it["name"] in prices]
            if not sellable:
                print("팔 것이 없어서 종료합니다.")
                break
                
            sell_msg = "무엇을 판매하시겠습니까?\n"
            for i, item in enumerate(sellable, 1):
                sell_msg += f" {i}) {item['name']} x1\n"
            sell_msg += f" {len(sellable)+1}) 종료"
            print(sell_msg)
            
            choice = input("입력: ").strip()
            if choice == str(len(sellable) + 1):
                print("판매를 종료합니다.")
                break
            elif choice.isdigit() and 1 <= int(choice) <= len(sellable):
                item = sellable[int(choice) - 1]
                earned = prices[item["name"]]
                player.money += earned
                player.remove_from_bag(item["name"], 1)
                print(f"{item['name']}를 판매해서 {earned}원을 벌었다. 계좌 잔액 = {player.money}원")
            else:
                print(f"1~{len(sellable)+1} 중에서 선택해.")

    def interact_quest(self, player, quests):
        if self.name == "정문":
            return _q_jeonmun(quests)
        elif self.name == "독수리상":
            return _q_eagle(quests)
        elif self.name == "본관":
            return _q_bonkwan(quests, self.answers)
        elif self.name == "세브란스":
            return _q_severance(quests, self.answers)
        elif self.name == "이윤재관":
            return _q_yunjae(quests)
        else:
            print("여기선 받을 임무가 없어.")
        return None


def _find_quest(quests, name):
    for q in quests:
        if q.name == name:
            return q
    return None


def _q_jeonmun(quests):
    if _find_quest(quests, "독수리상 방문") is None:
        q = Quest("독수리상 방문",
                  "학교에서 어떤 일들이 일어나고있는지 소식들이 모이는 독수리상에서 알아보자.")
        quests.append(q)
        print(q.description)
        print("[임무목록]에 임무가 추가되었습니다.")
    else:
        print("이미 독수리상 임무를 받았어.")
    return None


def _q_eagle(quests):
    q0 = _find_quest(quests, "독수리상 방문")
    if q0 and not q0.completed:
        q0.completed = True
        print(f"다음의 임무가 해결되었다! [{q0.description}]")
    for name, desc in [
        ("교내 부조리 수사",
         "교내 어딘가에서 부조리가 일어나고있다. 이동하고 상호작용을 해서 부조리를 찾아서 본관에 보고하라."),
        ("교내 위생사건 수사",
         "학생들이 단체로 식중독에 걸렸다. 이동하고 상호작용을 해서 위생사건의 원인을 찾아서 세브란스에 보고하라."),
    ]:
        if _find_quest(quests, name) is None:
            q = Quest(name, desc)
            quests.append(q)
            print(f"{name} - {desc}")
    return None


def _q_bonkwan(quests, answers):
    q = _find_quest(quests, "교내 부조리 수사")
    if q is None:
        print("교내 부조리 수사 임무가 없어.")
        return None
    if q.completed:
        print("이미 해결된 임무야.")
        return None
    correct = answers.get("교내 부조리 수사", "")
    print("교내 어디에 부조리가 있나?")
    ans = input("답 > ").strip()
    if ans == correct:
        q.completed = True
        print("다음의 임무가 해결되었다! [교내 부조리 수사]")
        print("수업들으러 이윤재관 가야지!")
    else:
        print("틀렸어. 더 조사해봐.")
    return None


def _q_severance(quests, answers):
    q = _find_quest(quests, "교내 위생사건 수사")
    if q is None:
        print("교내 위생사건 수사 임무가 없어.")
        return None
    if q.completed:
        print("이미 해결된 임무야.")
        return None
    correct = answers.get("교내 위생사건 수사", "")
    print("교내 어디에 식중독 원인이 있나?")
    ans = input("답 > ").strip()
    if ans == correct:
        q.completed = True
        print("다음의 임무가 해결되었다! [교내 위생사건 수사]")
        print("수업들으러 이윤재관 가야지!")
    else:
        print("틀렸어. 더 조사해봐.")
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
    elif done1:
        print("부조리 수사를 완료했구나! 식중독 원인도 찾아주세요~")
    elif done2:
        print("식중독 수사를 완료했구나! 부조리도 찾아주세요~")
    else:
        print("아직 수사 임무를 완료하지 않았어!")
    return None


def show_quests(quests):
    active = [q for q in quests if not q.completed]
    if not active:
        print("현재 진행 중인 임무가 없어.")
        return
    print("─" * 40)
    print("임무 목록:")
    for q in active:
        print(f"  > {q.name}")
        print(f"    {q.description}")
    print("─" * 40)


def show_difficulty(env):
    print(f"현재 난이도: {env['difficulty']}  (HP 감소: {DIFFICULTY_HP[env['difficulty']]}/칸)")
    print("변경: '쉬움' / '보통' / '어려움'  |  취소: Enter")
    choice = input("난이도 > ").strip()
    if choice in DIFFICULTY_HP:
        env["difficulty"] = choice
        print(f"난이도가 '{choice}'으로 변경됐어. (HP 감소: {DIFFICULTY_HP[choice]}/칸)")
    elif choice == "":
        print("변경 취소.")
    else:
        print("잘못된 난이도야. (쉬움/보통/어려움 중 하나)")


def save_game(player, env, quests, input_log):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"save_{timestamp}{SAVE_EXT}"
    save_data = {
        "player":    player.to_dict(),
        "env":       env,
        "quests":    [q.to_dict() for q in quests],
        "input_log": input_log,
        "saved_at":  timestamp,
    }
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"저장 완료 -> '{filename}'")
    except Exception as e:
        print(f"저장 실패: {e}")


def load_game():
    save_files = sorted(glob.glob(f"*{SAVE_EXT}"))
    print("─" * 40)
    print("불러오기")
    if save_files:
        print("  현재 폴더의 저장 파일:")
        for i, f in enumerate(save_files, 1):
            print(f"  {i}. {f}")
    else:
        print("  (현재 폴더에 저장 파일 없음)")
    print("  번호 입력: 목록에서 선택")
    print("  경로 입력: 상대/절대 경로 직접 입력")
    print("  0: 취소")
    print("─" * 40)
    choice = input("선택 > ").strip()
    if choice == "0":
        print("불러오기 취소.")
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(save_files):
            filepath = save_files[idx]
        else:
            print("잘못된 번호야.")
            return None
    else:
        filepath = os.path.abspath(choice)
        if not os.path.exists(filepath):
            print(f"파일을 찾을 수 없어: '{choice}'")
            return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        player    = Player.from_dict(data["player"])
        env       = data["env"]
        quests    = [Quest.from_dict(q) for q in data.get("quests", [])]
        input_log = data.get("input_log", [])
        print(f"불러오기 완료! (저장 시각: {data.get('saved_at', '알 수 없음')})")
        print(f"   위치: {player.location()}  |  HP: {player.hp}  |  잔액: {player.money:,}원")
        return player, env, quests, input_log
    except Exception as e:
        print(f"불러오기 실패: {e}")
        return None


def print_help():
    print("────────────────────────────────────────")
    print("명령어 목록:")
    print("  북 / 남 / 동 / 서  -> 이동")
    print("  상태               -> HP, 잔액, 위치, 인접칸 확인")
    print("  가방               -> 가방 아이템 확인/사용")
    print("  사용 [이름/번호]   -> 아이템 사용")
    print("  구매               -> 현재 장소 구매")
    print("  판매               -> 현재 장소 판매")
    print("  임무               -> 현재 장소 임무 상호작용")
    print("  임무목록           -> 보유 임무 목록 출력")
    print("  상호작용           -> 가능한 상호작용 목록")
    print("  저장               -> 게임 저장")
    print("  불러오기           -> 저장된 게임 불러오기")
    print("  난이도             -> 확인/변경")
    print("  도움말             -> 이 화면")
    print("  종료               -> 게임 종료")
    print("────────────────────────────────────────")


def process_command(cmd, player, env, quests, places, input_log):
    tokens = cmd.split()
    if not tokens:
        return None
    action = tokens[0]
    place  = places.get(player.location())

    if action in DIRECTIONS:
        moved = player.move(action, env["difficulty"])
        if moved:
            new_place = places.get(player.location())
            if new_place:
                new_place.print_event()
                acts = new_place.available_interactions()
                if acts:
                    print(f"[{', '.join(acts)}]")

    elif action == "상태":
        player.print_status(env)

    elif action == "가방":
        has = player.show_bag()
        if has:
            use_input = input("사용할 아이템 번호/이름 (Enter=건너뜀): ").strip()
            if use_input:
                player.use_item(use_input)

    elif action == "사용":
        if len(tokens) < 2:
            print("사용 [아이템 이름 또는 번호] 형태로 입력해.")
        else:
            player.use_item(" ".join(tokens[1:]))

    elif action == "구매":
        if place:
            place.interact_buy(player)
        else:
            print("알 수 없는 장소야.")

    elif action == "판매":
        if place:
            place.interact_sell(player)
        else:
            print("알 수 없는 장소야.")

    elif action == "임무":
        if place:
            result = place.interact_quest(player, quests)
            if result == "END":
                return "quit"
        else:
            print("알 수 없는 장소야.")

    elif action == "임무목록":
        show_quests(quests)

    elif action == "상호작용":
        if place:
            acts = place.available_interactions()
            if not acts:
                print("여기선 특별한 상호작용이 없어.")
            else:
                print(f"가능한 상호작용: {', '.join(acts)}")
                print("원하는 상호작용을 입력해 (구매/판매/임무).")
        else:
            print("알 수 없는 장소야.")

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
        print("게임을 종료합니다. 안녕!")
        return "quit"

    else:
        print(f"'{cmd}' 는 알 수 없는 명령이야. '도움말' 을 입력해봐.")

    return None


def main():
    _original_stdout = sys.stdout
    _original_stdin = sys.stdin
    sys.stdout = LoggedStdout(_original_stdout)
    sys.stdin = LoggedStdin(_original_stdin)

    try:
        print("==================================================")
        print("  연세대 캠퍼스 어드벤처")
        print("   송도 생활을 마치고 신촌에 처음 도착했다.")
        print("   현재 시각은 11시. 1시 수업은 이윤재관 511호.")
        print("   배가 고프다...")
        print("==================================================")
        print("시작 위치: 연대앞 버스정류장")
        print_help()

        difficulty_set = False

        events_data = load_events()
        places = {
            name: Place(name, events_data)
            for row in MAP for name in row if name is not None
        }

        player    = Player()
        env       = {"time": 11, "difficulty": "보통"}
        quests    = []
        input_log = []

        while True:
            loc = player.location()
            try:
                cmd = input(f"\n[{loc}] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n게임을 종료합니다.")
                break

            if not cmd:
                continue

            if not difficulty_set:
                print("\n난이도를 선택하세요")
                while True:
                    choice = input("1. 보통\n2. 어려움\n입력 (1 또는 2) > ").strip()
                    if choice == "1":
                        env["difficulty"] = "보통"
                        difficulty_set = True
                        break
                    elif choice == "2":
                        env["difficulty"] = "어려움"
                        difficulty_set = True
                        break
                    else:
                        print("올바른 번호(1 또는 2)를 입력해주세요.")
                print(f"\n난이도가 '{env['difficulty']}'로 설정되었습니다. 게임을 시작합니다.")
                continue

            input_log.append(cmd)
            result = process_command(cmd, player, env, quests, places, input_log)

            if result == "quit":
                break
            elif isinstance(result, tuple) and result[0] == "load":
                _, (player, env, quests, loaded_log) = result
                input_log = loaded_log
                places = {
                    name: Place(name, events_data)
                    for row in MAP for name in row if name is not None
                }
                print(f"게임 재개! 현재 위치: {player.location()}")

            if player.hp <= 0:
                print("HP가 0 이하야! 너무 배고파서 쓰러질 것 같아. 무언가를 먹어야 해!")
    finally:
        sys.stdout = _original_stdout
        sys.stdin = _original_stdin
        print(f"\n[작업 완료] 입력 기록 완료")


if __name__ == "__main__":
    main()