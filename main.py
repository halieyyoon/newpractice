"""
=============================================================
  연세대 캠퍼스 텍스트 어드벤처 게임
=============================================================
"""
 
import json
import os
import glob
from datetime import datetime
 

MAP = [
    ["종합관",        "본관",    "경영관",         "노천극장",      "새천년관",    "이윤재관"],
    ["백양관",       "백양로5",    "대강당",        "음악관",       "알렌관",     "ABMRC"],
    ["중앙도서관",   "독수리상",   "학생회관",      "루스채플",     "재활병원",   "치과대학"],
    ["체육관",       "백양로3",    "공터2",         "광혜원",       "어린이병원", "세브란스"],
    ["공학관",       "백양로2",    "백주년기념관",  "안과병원",     "제중관",     None],
    ["공학원",       "백양로1",    "공터1",         "암병원",       "의과대학",   None],
    ["연대앞 버스정류장", "정문",  "스타벅스",      "세브란스병원 버스정류장", None, None],
]
 

 
ROWS = len(MAP)      
COLS = len(MAP[0]) 
 
# 방향 → (행 변화, 열 변화) 매핑
DIRECTIONS = {
    "북": (-1, 0),
    "남": ( 1, 0),
    "서": ( 0,-1),
    "동": ( 0, 1),
}
 
# 시작 위치 (row=6, col=0 → "연대앞 버스정류장")
START_POS = [6, 0]
 
# 학생회관 좌표
STORE_POS = [2, 2]
 
# 학생회관 판매 아이템
STORE_ITEMS = [
    {"name": "두쫀쿠",   "price": 5000,  "hp_effect": 25},
    {"name": "카페라떼", "price": 2500,  "hp_effect": 25},
]
 
# 저장 파일 확장자
SAVE_EXT = ".sav.json"
 
 
# ─────────────────────────────────────────────
#  게임 상태 초기화
# ─────────────────────────────────────────────
def init_game():
    """게임 초기 상태를 반환한다."""
    player = {
        "hp":     10,        # 초기 HP (배고픈 상태)
        "money":  50000,     # 만원 단위 
        "pos":    list(START_POS), 
        "bag":    [],       
        "hunger": True,      
    }
    env = {
        "time":       11,    # 현재 시각 (11시)
        "difficulty": "보통", # 난이도
    }
    input_log = []           # 전체 입력 기록 (채점용)
    return player, env, input_log
 
 
# ─────────────────────────────────────────────
#  맵 유틸리티
# ─────────────────────────────────────────────
def current_location(player):
    """현재 위치의 장소 이름을 반환한다."""
    r, c = player["pos"]
    return MAP[r][c]
 
 
def is_valid_cell(r, c):
    """해당 좌표가 맵 범위 안이고 None이 아닌지 확인한다."""
    if 0 <= r < ROWS and 0 <= c < COLS:
        return MAP[r][c] is not None
    return False
 
 
# ─────────────────────────────────────────────
#  이동 시스템
# ─────────────────────────────────────────────
def move(player, direction):
    """
    주어진 방향으로 이동한다.
    - 경계 밖 또는 None 셀: "그 방향은 막혔어." 출력
    - 정상 이동: HP -1, 새 위치 안내
    반환값: 이동 성공 여부 (bool)
    """
    if direction not in DIRECTIONS:
        print("동/서/남/북 중 하나를 입력해.")
        return False
 
    dr, dc = DIRECTIONS[direction]
    nr, nc = player["pos"][0] + dr, player["pos"][1] + dc
 
    if not is_valid_cell(nr, nc):
        print("그 방향은 막혔어.")
        return False
 
    # 이동 성공
    player["pos"] = [nr, nc]
    player["hp"] -= 1
    loc = current_location(player)
    print(f"[{loc}] 에 도착했다. (HP -{1} → HP {player['hp']})")
    return True
 
 
# ─────────────────────────────────────────────
#  상태 출력 시스템
# ─────────────────────────────────────────────
def show_status(player, env):
    """'상태' 명령: 계좌 잔액과 HP를 출력한다."""
    print("─" * 30)
    print(f"현재 위치 : {current_location(player)}")
    print(f"현재 시각 : {env['time']}시")
    print(f"계좌 잔액 : {player['money']:,}원")
    print(f"HP       : {player['hp']}")
    print(f"가방 아이템: {len(player['bag'])}개")
    print("─" * 30)
 
 
# ─────────────────────────────────────────────
#  inventory (가방) sys
# ─────────────────────────────────────────────
def show_bag(player):
    """'가방' 명령: 가방 내 아이템 목록을 출력한다."""
    bag = player["bag"]
    if not bag:
        print("가방이 비어있어.")
        return
 
    print("─" * 30)
    print("가방 속 물건:")
    for i, item in enumerate(bag, 1):
        print(f"  {i}. {item['name']}  (HP +{item['hp_effect']})")
    print("─" * 30)
 
 
def use_item(player, choice):
    """
    가방에서 아이템을 꺼내 사용한다.
    choice: 아이템 이름(str) 또는 번호(str/int)
    """
    bag = player["bag"]
    if not bag:
        print("가방이 비어있어.")
        return
 
    target = None
    # 번호로 선택
    if str(choice).isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(bag):
            target = bag[idx]
    else:
        # 이름으로 선택
        for item in bag:
            if item["name"] == choice:
                target = item
                break
 
    if target is None:
        print(f"'{choice}' 는 가방에 없어.")
        return
 
    # 아이템 사용
    player["hp"] += target["hp_effect"]
    bag.remove(target)
    print(f"'{target['name']}' 을 먹었다! HP +{target['hp_effect']} → HP {player['hp']}")
 
    # 배고픔 해소
    if player["hp"] > 10:
        player["hunger"] = False
 
 
# ─────────────────────────────────────────────
#  상호작용: 학생회관 상점
# ─────────────────────────────────────────────
def interact_store(player):
    """
    학생회관 도착 시 상점 상호작용.
    아이템을 구매해 가방에 넣는다.
    """
    print("=" * 40)
    print(" 학생회관 편의점에 들어왔다.")
    print("  구매할 물건을 고르세요:")
    for i, item in enumerate(STORE_ITEMS, 1):
        print(f"  {i}. {item['name']}  - {item['price']:,}원  (HP +{item['hp_effect']})")
    print("  0. 나가기")
    print("=" * 40)
 
    while True:
        choice = input("구매 > ").strip()
        if choice == "0":
            print("가게를 나왔다.")
            break
        elif choice.isdigit() and 1 <= int(choice) <= len(STORE_ITEMS):
            item_template = STORE_ITEMS[int(choice) - 1]
            if player["money"] < item_template["price"]:
                print(f"돈이 부족해. (잔액: {player['money']:,}원)")
            else:
                player["money"] -= item_template["price"]
                # 딕셔너리 복사해서 가방에 추가 (원본 보호)
                player["bag"].append(dict(item_template))
                print(f"'{item_template['name']}' 을 샀다! (잔액: {player['money']:,}원)")
        else:
            print("0~", len(STORE_ITEMS), "중에서 선택해.")
 
 
def try_interact(player):
    """현재 위치에 따라 상호작용을 시도한다."""
    loc = current_location(player)
    if player["pos"] == STORE_POS:   # 학생회관
        interact_store(player)
    elif loc == "이윤재관":
        print("이윤재관에 도착했다! 511호 수업이 기다리고 있어.")
    elif loc == "스타벅스":
        print("스타벅스다. 아직 구매 기능은 없어.")
    # 다른 장소는 확장 가능
 
 
# ─────────────────────────────────────────────
#  저장 기능
# ─────────────────────────────────────────────
def save_game(player, env, input_log):
    """
    '저장' 명령:
    - 주인공 상태, 위치, 현재 시각, 난이도, 전체 입력 기록을 JSON 파일에 저장
    - 파일명: save_YYYYMMDD_HHMMSS.sav.json
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"save_{timestamp}{SAVE_EXT}"
 
    save_data = {
        "player":    player,
        "env":       env,
        "input_log": input_log,
        "saved_at":  timestamp,
    }
 
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"저장 완료 → '{filename}'")
    except Exception as e:
        print(f"저장 실패: {e}")
 
 
# ─────────────────────────────────────────────
#  불러오기 기능
# ─────────────────────────────────────────────
def load_game():
    """
    '불러오기' 명령:
    - 현재 폴더의 저장 파일을 번호와 함께 보여줌
    - 번호 선택 또는 경로 직접 입력 (상대/절대 경로 모두 지원)
    - 성공 시 (player, env, input_log) 반환, 실패 시 None 반환
    """
    # 현재 폴더의 저장 파일 목록
    save_files = sorted(glob.glob(f"*{SAVE_EXT}"))
 
    print("─" * 40)
    print("불러오기")
    if save_files:
        print("  현재 폴더의 저장 파일:")
        for i, f in enumerate(save_files, 1):
            print(f"  {i}. {f}")
    else:
        print("  (현재 폴더에 저장 파일 없음)")
    print("  → 번호 입력: 위 목록에서 선택")
    print("  → 경로 입력: 직접 경로 입력 (상대/절대 경로)")
    print("  → 0: 취소")
    print("─" * 40)
 
    choice = input("선택 > ").strip()
 
    if choice == "0":
        print("불러오기 취소.")
        return None
 
    # 번호 선택
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(save_files):
            filepath = save_files[idx]
        else:
            print("잘못된 번호야.")
            return None
    else:
        # 경로 직접 입력 (상대경로 & 절대경로 모두 지원)
        filepath = os.path.abspath(choice)  # 절대경로로 변환 (상대경로도 처리됨)
        if not os.path.exists(filepath):
            print(f"파일을 찾을 수 없어: '{choice}'")
            return None
 
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        player    = data["player"]
        env       = data["env"]
        input_log = data["input_log"]
        print(f"불러오기 완료! (저장 시각: {data.get('saved_at', '알 수 없음')})")
        print(f"   위치: {current_location(player)}  |  HP: {player['hp']}  |  잔액: {player['money']:,}원")
        return player, env, input_log
    except Exception as e:
        print(f"불러오기 실패: {e}")
        return None
 
 
# ─────────────────────────────────────────────
#  입력 처리 & 메인 루프
# ─────────────────────────────────────────────
def print_help():
    """도움말 출력."""
    print("─" * 40)
    print("명령어 목록:")
    print("  북 / 남 / 동 / 서  → 이동")
    print("  상태              → HP, 잔액 확인")
    print("  가방              → 가방 아이템 확인")
    print("  사용 [이름/번호]  → 아이템 사용")
    print("  상호작용          → 현재 장소 이용")
    print("  저장              → 게임 저장")
    print("  불러오기          → 저장된 게임 불러오기")
    print("  도움말            → 이 화면")
    print("  종료              → 게임 종료")
    print("─" * 40)
 
 
def process_command(cmd, player, env, input_log):
    """
    입력 명령을 파싱하고 처리한다.
    반환값: "quit" (종료), "load" (불러오기 성공 시 새 상태), None (계속)
    """
    tokens = cmd.split()
    if not tokens:
        return None
 
    action = tokens[0]
 
    # ── 이동 ──
    if action in DIRECTIONS:
        moved = move(player, action)
        if moved:
            try_interact(player)
 
    # ── 상태 확인 ──
    elif action == "상태":
        show_status(player, env)
 
    # ── 가방 ──
    elif action == "가방":
        show_bag(player)
        if player["bag"]:
            use_input = input("사용할 아이템 번호/이름 (Enter=건너뜀): ").strip()
            if use_input:
                use_item(player, use_input)
 
    # ── 사용 (단독 명령) ──
    elif action == "사용":
        if len(tokens) < 2:
            print("사용 [아이템 이름 또는 번호] 형태로 입력해.")
        else:
            use_item(player, " ".join(tokens[1:]))
 
    # ── 상호작용 ──
    elif action == "상호작용":
        try_interact(player)
 
    # ── 저장 ──
    elif action == "저장":
        save_game(player, env, input_log)
 
    # ── 불러오기 ──
    elif action == "불러오기":
        result = load_game()
        if result is not None:
            return ("load", result)
 
    # ── 도움말 ──
    elif action == "도움말":
        print_help()
 
    # ── 종료 ──
    elif action == "종료":
        print("게임을 종료합니다. 안녕!")
        return "quit"
 
    else:
        print(f"'{cmd}' 는 알 수 없는 명령이야. '도움말' 을 입력해봐.")
 
    return None
 
 
def main():
    """메인 게임 루프."""
    print("=" * 50)
    print("  연세대 캠퍼스 어드벤처")
    print("   송도 생활을 마치고 신촌에 처음 도착했다.")
    print("   현재 시각은 11시. 1시 수업은 이윤재관 511호.")
    print("   배가 고프다...")
    print("=" * 50)
    print(f"시작 위치: 연대앞 버스정류장")
    print_help()
 
    # 게임 상태 초기화
    player, env, input_log = init_game()
 
    # 메인 루프
    while True:
        loc = current_location(player)
        try:
            cmd = input(f"\n[{loc}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n게임을 종료합니다.")
            break
 
        if not cmd:
            continue
 
        # 입력 기록 (채점용)
        input_log.append(cmd)
 
        # 명령 처리
        result = process_command(cmd, player, env, input_log)
 
        if result == "quit":
            break
        elif isinstance(result, tuple) and result[0] == "load":
            # 불러오기 성공 → 상태 교체
            _, (player, env, input_log) = result
            print(f"게임 재개! 현재 위치: {current_location(player)}")
 
        # HP 0 이하 경고
        if player["hp"] <= 0:
            print("HP가 0이 됐다! 너무 배고파서 쓰러질 것 같아. 무언가를 먹어야 해!")
 
 
if __name__ == "__main__":
    main()