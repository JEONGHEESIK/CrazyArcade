"""
강화학습 설정 파일
"""

# 게임 환경 설정
GAME_HOST = "127.0.0.1"
GAME_PORT = 12345

# 맵 크기
BOARD_ROWS = 13
BOARD_COLS = 15
BOARD_SIZE = BOARD_ROWS * BOARD_COLS  # 195

# 상태 공간 크기
# 플레이어 정보: 위치(2) + 속도(1) + 물풍선개수(1) + 파워(1) + 상태(1) + 생존(1) + 물방울(1) + 타이머(1) = 9
# 자신 + 상대 = 18
# 맵 정보: 물풍선(195) + 아이템(195) + 물줄기(195) = 585
# 게임 정보: 시간(1) + game_over(1) + winner(1) + player_index(1) = 4
# 총합: 18 + 585 + 4 = 607
STATE_SIZE = 607

# 행동 공간 크기
ACTION_SIZE = 6  # IDLE, UP, DOWN, LEFT, RIGHT, PLACE_BOMB

# DQN 하이퍼파라미터
LEARNING_RATE = 0.0001  # 학습률 완만화 (안정적 학습)
GAMMA = 0.95  # 할인율 감소 (단기 보상 중시)
EPSILON_START = 1.0  # 초기 탐험률
EPSILON_MIN = 0.05  # 최소 탐험률 증가 (더 많은 탐험)
EPSILON_DECAY = 0.997  # 탐험률 감소율 완만화 (더 많은 탐험)

# 메모리 및 배치
MEMORY_SIZE = 50000  # 메모리 크기 감소 (메모리 효율)
BATCH_SIZE = 128  # 배치 크기 증가 (안정적 학습)
TARGET_UPDATE_FREQUENCY = 5  # 타겟 네트워크 업데이트 주기 감소 (빠른 수렴)

# 학습 설정
MAX_EPISODES = 5000  # 에피소드 수 감소
MAX_STEPS_PER_EPISODE = 500  # 스텝 수 감소 (빠른 게임)
SAVE_FREQUENCY = 50  # 모델 저장 주기 감소

# 네트워크 구조
HIDDEN_SIZE_1 = 256
HIDDEN_SIZE_2 = 256
HIDDEN_SIZE_3 = 128

# 보상 설정 (초반 아이템 수집 매우 중요!)
REWARD_COLLECT_ITEM = 20.0  # 기본 아이템 (5 → 20)
REWARD_COLLECT_BALLON = 30.0  # 물풍선 개수 증가 (8 → 30) ⭐
REWARD_COLLECT_POTION = 35.0  # 파워 증가 (8 → 35) ⭐⭐
REWARD_COLLECT_SKATE = 25.0  # 속도 증가 (5 → 25) ⭐

# 전투 관련 보상 (대폭 증가)
REWARD_PLACE_BOMB_NEAR_ENEMY = 15.0  # 적 근처에 물풍선 설치
REWARD_HIT_ENEMY = 100.0  # 적 공격 성공
REWARD_WIN_GAME = 500.0  # 승리 (너무 크면 학습 불안정)

# 물방울 시스템 보상 (크레이지아케이드 핵심!)
REWARD_TRAP_ENEMY = 50.0  # 상대를 물방울에 가둠
REWARD_POP_ENEMY = 200.0  # 상대 물방울을 직접 터트림 (적극적 플레이!)
REWARD_AUTO_KO = 50.0  # 자동 KO (소극적 플레이, 낮은 보상)
REWARD_APPROACH_TRAPPED = 3.0  # 갇힌 적에게 접근 (매 스텝)
REWARD_FAST_POP_BONUS = 50.0  # 빠른 처치 보너스 (최대)

# 위험 회피 보상
REWARD_IN_DANGER_ZONE = -3.0  # 위험 지역에 있을 때 (매 스텝)
REWARD_ESCAPE_DANGER = 10.0  # 위험 지역 탈출
REWARD_GET_TRAPPED = -100.0  # 물방울에 갇힘 (큰 패널티!)
REWARD_GET_POPPED = -200.0  # 상대가 직접 터트림 (더 큰 패널티!)
REWARD_AUTO_DEATH = -150.0  # 자동 KO 당함
REWARD_DIE = -500.0  # 사망

# 전략적 보상
REWARD_MOVE_TO_ENEMY = 2.0  # 적에게 접근
REWARD_MOVE_TO_ITEM = 2.0  # 아이템에 접근 (초반 유도!)
REWARD_MOVE_AWAY_COWARD = -1.0  # 너무 멀리 도망 (소극적 플레이 방지)
REWARD_IDLE_PENALTY = -2.0  # 대기 행동 패널티
REWARD_TIME_PENALTY = -0.02  # 시간 패널티 완화
REWARD_SURVIVE_STEP = 0.02  # 생존 보상 (매 스텝)
REWARD_ACTIVE_MOVEMENT = 0.3  # 일정 거리 이상 이동 시 보상
REWARD_OPTIMAL_DISTANCE = 0.5  # 적과 적정 거리 유지 보상
REWARD_TOO_CLOSE_PENALTY = -1.5  # 적과 너무 근접 시 패널티
REWARD_EARLY_ITEM_BONUS = 15.0  # 초반 30스텝 내 아이템 획득 보너스

# 로그 및 저장 경로
LOG_DIR = "./logs"
MODEL_DIR = "./models"
TENSORBOARD_DIR = "./runs"
