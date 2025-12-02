"""
C++ 게임과 통신하는 인터페이스
"""
import socket
import json
import numpy as np
import math
import config


class GameInterface:
    """게임 통신 인터페이스"""
    
    def __init__(self, host=None, port=None):
        """
        Args:
            host: 게임 서버 호스트
            port: 게임 서버 포트
        """
        self.host = host or config.GAME_HOST
        self.port = port or config.GAME_PORT
        self.socket = None
        self.connected = False
    
    def connect(self, timeout=30):
        """
        게임 서버에 연결 (Python이 클라이언트)
        
        Args:
            timeout: 연결 타임아웃 (초)
        
        Returns:
            연결 성공 여부
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            print(f"Connecting to C++ game server at {self.host}:{self.port}...")
            
            self.socket.connect((self.host, self.port))
            # 연결 후 타임아웃 제거 (무한 대기)
            self.socket.settimeout(None)
            self.connected = True
            print(f"Connected to game server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """연결 종료"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self.connected = False
            print("Disconnected from game server")
    
    def receive_state(self):
        """
        게임 상태 수신
        
        Returns:
            상태 벡터 (numpy array) 또는 None
        """
        if not self.connected:
            return None
        
        try:
            # JSON 데이터 수신 (개행문자로 구분)
            data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    return None
                data += chunk
                if b'\n' in data:
                    break
            
            # JSON 파싱
            json_str = data.decode('utf-8').strip()
            state_dict = json.loads(json_str)
            
            # 디버그: game_over 값 확인
            if state_dict.get('game_over', False):
                print(f"[DEBUG] Received game_over=true from C++ in state JSON")
            
            # 상태 벡터로 변환
            state_vector = self._dict_to_vector(state_dict)
            
            return state_vector
        
        except Exception as e:
            print(f"Error receiving state: {e}")
            return None
    
    def send_action(self, action):
        """
        행동 전송
        
        Args:
            action: 행동 번호 (0-5)
        
        Returns:
            전송 성공 여부
        """
        if not self.connected:
            return False
        
        try:
            # 행동을 문자열로 전송
            action_str = f"{action}\n"
            self.socket.sendall(action_str.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending action: {e}")
            return False
    
    def receive_reward(self):
        """
        보상 데이터 수신 (C++에서 전송하는 reward JSON)
        
        Returns:
            (reward, done, info) 튜플 또는 None
        """
        if not self.connected:
            return None
        
        try:
            # JSON 데이터 수신 (개행문자로 구분)
            data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    return None
                data += chunk
                if b'\n' in data:
                    break
            
            # JSON 파싱
            json_str = data.decode('utf-8').strip()
            reward_dict = json.loads(json_str)
            
            reward = reward_dict.get('reward', 0.0)
            done = reward_dict.get('done', False)
            info = reward_dict.get('info', '')
            
            return (reward, done, info)
        
        except Exception as e:
            print(f"Error receiving reward: {e}")
            return None
    
    def reset(self):
        """
        게임 리셋 요청 (C++가 자동으로 재시작하므로 다음 상태만 받음)
        
        Returns:
            초기 상태 벡터
        """
        if not self.connected:
            return None
        
        try:
            # C++가 자동 재시작하므로 RESET 명령 불필요
            # 다음 상태를 받으면 그것이 새 에피소드의 초기 상태
            return self.receive_state()
        except Exception as e:
            print(f"Error resetting game: {e}")
            return None
    
    def _dict_to_vector(self, state_dict):
        """
        상태 딕셔너리를 벡터로 변환
        
        Args:
            state_dict: 게임 상태 딕셔너리
        
        Returns:
            상태 벡터 (numpy array, shape=(600,))
        """
        # game_over 플래그 저장 (done 판정용)
        self.game_over = state_dict.get('game_over', False)
        
        # 디버그: game_over 값 출력
        if self.game_over:
            print(f"[DEBUG] game_over=True received from C++")
        
        vector = []
        
        # 플레이어 정보 (18개 - 물방울 상태 추가!)
        vector.extend([
            state_dict.get('my_x', 0.0) / 800.0,  # 정규화 (0-1)
            state_dict.get('my_y', 0.0) / 700.0,
            state_dict.get('my_speed', 0.0) / 5.0,
            state_dict.get('my_bomb_count', 0) / 6.0,
            state_dict.get('my_power', 0) / 7.0,
            state_dict.get('my_state', 0) / 10.0,
            1.0 if state_dict.get('my_alive', False) else 0.0,
            1.0 if state_dict.get('my_trapped', False) else 0.0,  # 물방울 상태
            state_dict.get('my_trap_timer', 0) / 50.0,  # 남은 시간 (0-50)
            
            state_dict.get('enemy_x', 0.0) / 800.0,
            state_dict.get('enemy_y', 0.0) / 700.0,
            state_dict.get('enemy_speed', 0.0) / 5.0,
            state_dict.get('enemy_bomb_count', 0) / 6.0,
            state_dict.get('enemy_power', 0) / 7.0,
            state_dict.get('enemy_state', 0) / 10.0,
            1.0 if state_dict.get('enemy_alive', False) else 0.0,
            1.0 if state_dict.get('enemy_trapped', False) else 0.0,  # 적 물방울 상태
            state_dict.get('enemy_trap_timer', 0) / 50.0,  # 적 남은 시간
        ])
        
        # 맵 정보 (195 * 3 = 585개)
        map_bombs = state_dict.get('map_bombs', [0] * 195)
        map_items = state_dict.get('map_items', [0] * 195)
        map_waves = state_dict.get('map_waves', [0] * 195)
        
        vector.extend(map_bombs)
        vector.extend(map_items)
        vector.extend(map_waves)
        
        # 게임 시간 (1개)
        vector.append(state_dict.get('game_time', 0.0) / 300.0)  # 정규화 (0-300초)
        
        # 게임 종료 정보 (3개)
        vector.append(1.0 if state_dict.get('game_over', False) else 0.0)
        vector.append(float(state_dict.get('winner', 0)))
        vector.append(float(state_dict.get('player_index', 0)))
        
        return np.array(vector, dtype=np.float32)
    
    def __enter__(self):
        """Context manager 진입"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.disconnect()


class GameEnvironment:
    """게임 환경 래퍼 (OpenAI Gym 스타일)"""
    
    def __init__(self, host='127.0.0.1', port=12345):
        self.interface = GameInterface(host, port)
        self.state_size = config.STATE_SIZE
        self.action_size = config.ACTION_SIZE
        self.current_state = None
        self.previous_state = None
        self.game_over = False  # game_over 플래그 초기화
    
    def connect(self):
        """게임 서버 연결"""
        return self.interface.connect()
    
    def disconnect(self):
        """연결 종료"""
        self.interface.disconnect()
    
    def reset(self):
        """
        환경 리셋
        
        Returns:
            초기 상태
        """
        self.current_state = self.interface.reset()
        self.previous_state = None
        return self.current_state
    
    def step(self, action):
        """
        행동 실행 및 즉각적인 행동 보정 (Action Shaping)
        """
        # (이전 상태 저장 - 거리 계산용)
        prev_x = self.current_state[0]
        prev_y = self.current_state[1]

        # 1. 행동 전송 및 상태 수신 (기존 코드)
        if not self.interface.send_action(action):
            return None, 0.0, True, {"error": "Failed to send action"}
        
        self.previous_state = self.current_state
        self.current_state = self.interface.receive_state()
        
        if self.current_state is None:
            return None, 0.0, True, {"error": "Failed to receive state"}
        
        # 2. 보상 계산
        reward, done, info = self._calculate_reward()
        
        # ============================================================
        # 🔥 [영적 처방] 벽 치기 및 멍때리기 참교육 🔥
        # ============================================================
        
        # 현재 좌표 확인
        curr_x = self.current_state[0]
        curr_y = self.current_state[1]
        
        # 행동 정의: 1:UP, 2:DOWN, 3:LEFT, 4:RIGHT
        is_move_action = (action in [1, 2, 3, 4])
        
        # 이동 명령을 내렸는데 실제로 움직이지 않은 경우 (벽에 박음)
        # 좌표는 정규화(0~1) 되어 있으므로 아주 작은 차이로 비교
        dist = np.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
        
        if is_move_action and dist < 0.001: 
            # "벽에 머리 박지 마!" -> 강력한 벌금
            reward -= 5.0 
            info['wall_collision'] = True
            
        # 폭탄 설치 패널티 (기존 유지)
        if action == 5:
            penalty = getattr(config, 'REWARD_PLACE_BOMB', -2.0)
            reward += penalty
            
        # 멍때리기 패널티 (기존 유지)
        elif action == 0:
            reward += config.REWARD_IDLE_PENALTY
            
        # ============================================================
        
        return self.current_state, reward, done, info
    
    def _calculate_reward(self):
        """
        보상 계산 (수정됨: 승패 판정 로직 개선 및 Premature Done 방지)
        
        Returns:
            (reward, done, info)
        """
        reward = config.REWARD_TIME_PENALTY  # 기본 시간 패널티
        done = self.game_over  # C++에서 받은 game_over 플래그 사용
        info = {}
        
        if self.previous_state is None:
            return reward, done, info
        
        # 위치 및 상태 추출
        my_x_prev, my_y_prev = self.previous_state[0] * 800, self.previous_state[1] * 700
        my_x_curr, my_y_curr = self.current_state[0] * 800, self.current_state[1] * 700
        enemy_x_prev, enemy_y_prev = self.previous_state[9] * 800, self.previous_state[10] * 700
        enemy_x_curr, enemy_y_curr = self.current_state[9] * 800, self.current_state[10] * 700
        
        # 생존 체크
        my_alive_prev = self.previous_state[6] > 0.5
        my_alive_curr = self.current_state[6] > 0.5
        enemy_alive_prev = self.previous_state[15] > 0.5
        enemy_alive_curr = self.current_state[15] > 0.5
        
        # 물방울 상태 체크 (크레이지아케이드 핵심!)
        my_trapped_prev = self.previous_state[7] > 0.5
        my_trapped_curr = self.current_state[7] > 0.5
        my_trap_timer_curr = int(self.current_state[8] * 50)
        
        enemy_trapped_prev = self.previous_state[16] > 0.5
        enemy_trapped_curr = self.current_state[16] > 0.5
        enemy_trap_timer_curr = int(self.current_state[17] * 50)
        
        # 기본 생존 보상
        reward += config.REWARD_SURVIVE_STEP

        # 적극적인 이동 보상
        move_dist = np.sqrt((my_x_curr - my_x_prev)**2 + (my_y_curr - my_y_prev)**2)
        if move_dist > 30:  # 타일 절반 이상 이동
            reward += config.REWARD_ACTIVE_MOVEMENT

        # ============================================================
        # [수정됨] 게임 종료 및 승패 체크 (ID 불일치 해결 로직)
        # ============================================================
        game_over = self.current_state[-3] > 0.5  # 끝에서 3번째
        winner = int(self.current_state[-2])      # 끝에서 2번째
        player_index = int(self.current_state[-1]) # 끝에서 1번째
        
        if game_over:
            done = True
            print(f"[DEBUG] Game Over Logic Triggered. Winner={winner}, MyID={player_index}")
            
            # 1. ID가 일치하는 경우 (정상)
            if winner == player_index:
                reward += config.REWARD_WIN_GAME
                info['result'] = 'win'
            # 2. 0번 vs 1번 인덱스 불일치 보정
            elif player_index == 0 and winner == 1:
                reward += config.REWARD_WIN_GAME
                info['result'] = 'win'
            elif player_index == 1 and winner == 2:
                reward += config.REWARD_WIN_GAME
                info['result'] = 'win'
            # 3. 무승부 (0번을 무승부로 처리)
            elif winner == 0:
                reward += 0
                info['result'] = 'draw'
            # 4. 패배
            else:
                reward += config.REWARD_DIE
                info['result'] = 'died'
            return reward, done, info
        
        # 물방울 시스템 보상 (크레이지아케이드 핵심!)
        
        # 1. 상대를 물방울에 가뒀는지 체크
        if not enemy_trapped_prev and enemy_trapped_curr:
            reward += config.REWARD_TRAP_ENEMY  # +50
            info['trap_enemy'] = True
        
        # 2. 상대 물방울을 터트렸는지 체크
        if enemy_trapped_prev and enemy_alive_prev and not enemy_alive_curr:
            # 거리 계산
            dist = math.sqrt((my_x_curr - enemy_x_curr)**2 + (my_y_curr - enemy_y_curr)**2)
            if dist < 52:  # 직접 터트림!
                time_bonus = (enemy_trap_timer_curr / 50.0) * config.REWARD_FAST_POP_BONUS
                reward += config.REWARD_POP_ENEMY + time_bonus  # +200 ~ +250
                info['pop_enemy'] = True
                info['pop_type'] = 'direct'
            else:  # 자동 터짐
                reward += config.REWARD_AUTO_KO  # +50
                info['pop_enemy'] = True
                info['pop_type'] = 'auto'
        
        # 3. 내가 물방울에 갇혔는지 체크
        if not my_trapped_prev and my_trapped_curr:
            reward += config.REWARD_GET_TRAPPED  # -100
            info['get_trapped'] = True
        
        # 4. 내가 터졌는지 체크
        if my_trapped_prev and my_alive_prev and not my_alive_curr:
            # 거리 계산
            dist = math.sqrt((my_x_curr - enemy_x_curr)**2 + (my_y_curr - enemy_y_curr)**2)
            if dist < 52:  # 상대가 직접 터트림
                reward += config.REWARD_GET_POPPED  # -200
                info['get_popped'] = True
                info['death_type'] = 'direct'
            else:  # 자동 터짐
                reward += config.REWARD_AUTO_DEATH  # -150
                info['get_popped'] = True
                info['death_type'] = 'auto'
        
        # 5. 갇힌 적에게 접근 중인지 체크 (적극성 유도!)
        if enemy_trapped_curr and not my_trapped_curr:
            dist_prev = math.sqrt((my_x_prev - enemy_x_prev)**2 + (my_y_prev - enemy_y_prev)**2)
            dist_curr = math.sqrt((my_x_curr - enemy_x_curr)**2 + (my_y_curr - enemy_y_curr)**2)
            if dist_curr < dist_prev:  # 가까워짐
                reward += config.REWARD_APPROACH_TRAPPED  # +2
                info['approaching_trapped'] = True
        
        # [수정됨] alive 상태로 인한 강제 done 제거 (보상만 주고 서버 done 기다림)
        if my_alive_prev and not my_alive_curr:
            if not my_trapped_prev:  # 물방울 없이 바로 죽음
                reward += config.REWARD_DIE
            # done = True  <-- 제거됨 (Premature Done 방지)
            info['result'] = 'died'
            info['death_event'] = True
        
        if enemy_alive_prev and not enemy_alive_curr:
            if not enemy_trapped_prev:  # 물방울 없이 바로 죽음
                reward += config.REWARD_WIN_GAME
            # done = True  <-- 제거됨 (Premature Done 방지)
            info['result'] = 'win'
            info['kill_event'] = True
        
        # 아이템 획득 체크 (초반 매우 중요!)
        my_bombs_prev = int(self.previous_state[3] * 6)
        my_bombs_curr = int(self.current_state[3] * 6)
        my_power_prev = int(self.previous_state[4] * 7)
        my_power_curr = int(self.current_state[4] * 7)
        my_speed_prev = self.previous_state[2] * 5
        my_speed_curr = self.current_state[2] * 5
        
        # 게임 시간 (초반 30스텝 내 보너스)
        game_time = self.current_state[-4] * 300.0  # 정규화 해제
        
        if my_bombs_curr > my_bombs_prev:
            item_reward = config.REWARD_COLLECT_BALLON
            if game_time < 3.0:  # 초반 3초 내
                item_reward += config.REWARD_EARLY_ITEM_BONUS
            reward += item_reward
            info['item'] = 'ballon'
            info['early_bonus'] = game_time < 3.0
            
        if my_power_curr > my_power_prev:
            item_reward = config.REWARD_COLLECT_POTION
            if game_time < 3.0:  # 초반 3초 내
                item_reward += config.REWARD_EARLY_ITEM_BONUS
            reward += item_reward
            info['item'] = 'potion'
            info['early_bonus'] = game_time < 3.0
            
        if my_speed_curr > my_speed_prev:
            item_reward = config.REWARD_COLLECT_SKATE
            if game_time < 3.0:  # 초반 3초 내
                item_reward += config.REWARD_EARLY_ITEM_BONUS
            reward += item_reward
            info['item'] = 'skate'
            info['early_bonus'] = game_time < 3.0
        
        # === 전략적 보상 ===
        
        # 1. 아이템 접근 보상 (초반 매우 중요!)
        if game_time < 5.0:  # 초반 5초 동안
            # 맵에서 가장 가까운 아이템 찾기
            map_items = self.current_state[18:18+195]  # 아이템 맵
            closest_item_dist = float('inf')
            
            for i, item_val in enumerate(map_items):
                if item_val > 0:  # 아이템이 있으면
                    item_y = (i // 15) * 52 + 53
                    item_x = (i % 15) * 52 + 26
                    dist = np.sqrt((my_x_curr - item_x)**2 + (my_y_curr - item_y)**2)
                    if dist < closest_item_dist:
                        closest_item_dist = dist
            
            # 아이템에 가까워지면 보상
            if closest_item_dist < 200:  # 아이템이 근처에 있으면
                reward += config.REWARD_MOVE_TO_ITEM
                info['approaching_item'] = True
        
        # 2. 적과의 거리 계산
        dist_prev = np.sqrt((my_x_prev - enemy_x_prev)**2 + (my_y_prev - enemy_y_prev)**2)
        dist_curr = np.sqrt((my_x_curr - enemy_x_curr)**2 + (my_y_curr - enemy_y_curr)**2)

        # 최적 거리 유지 보상 / 패널티
        if dist_curr < 110:  # 너무 가까움 (위험 구간)
            reward += config.REWARD_TOO_CLOSE_PENALTY
            info['distance'] = 'too_close'
        elif 180 <= dist_curr <= 320:  # 적정 거리를 유지
            reward += config.REWARD_OPTIMAL_DISTANCE
            info['distance'] = 'optimal_range'

        # 적에게 접근하면 보상 (공격적 플레이 유도)
        if dist_curr < dist_prev and dist_curr < 200:  # 200 픽셀 이내로 접근
            reward += config.REWARD_MOVE_TO_ENEMY
            info['action'] = 'approach_enemy'
        
        # 너무 멀리 도망하면 패널티 (소극적 플레이 방지)
        if dist_curr > 400 and dist_curr > dist_prev:
            reward += config.REWARD_MOVE_AWAY_COWARD
            info['action'] = 'coward'
        
        # 2. 위험 지역 감지 (물풍선 및 물줄기 근처)
        in_danger_prev = self._is_in_danger_zone(self.previous_state, my_x_prev, my_y_prev)
        in_danger_curr = self._is_in_danger_zone(self.current_state, my_x_curr, my_y_curr)
        
        if in_danger_curr:
            reward += config.REWARD_IN_DANGER_ZONE
            info['danger'] = True
        
        # 위험 지역에서 탈출하면 보상
        if in_danger_prev and not in_danger_curr:
            reward += config.REWARD_ESCAPE_DANGER
            info['action'] = 'escape_danger'
        
        # 3. 물풍선 설치 전략성 평가
        # 적 근처에 물풍선을 설치하면 보상
        if self._placed_bomb_near_enemy(my_x_curr, my_y_curr, enemy_x_curr, enemy_y_curr):
            reward += config.REWARD_PLACE_BOMB_NEAR_ENEMY
            info['action'] = 'bomb_near_enemy'
        
        return reward, done, info
    
    def _is_in_danger_zone(self, state, my_x, my_y):
        """
        위험 지역에 있는지 판단 (물풍선 및 물줄기 근처)
        
        Args:
            state: 현재 상태
            my_x, my_y: 플레이어 위치
        
        Returns:
            위험 지역 여부
        """
        # [수정됨] 맵 정보 추출 인덱스 수정 (14 -> 18)
        # 플레이어 관련 정보가 18개이므로 맵은 18번부터 시작해야 함
        map_bombs = state[18:18+195]  # 물풍선 위치
        map_waves = state[18+195*2:18+195*3]  # 물줄기 위치
        
        # 플레이어 그리드 위치 계산 (52x52 타일)
        grid_x = int((my_x - 26) / 52)
        grid_y = int((my_y - 53) / 52)
        
        if grid_x < 0 or grid_x >= 15 or grid_y < 0 or grid_y >= 13:
            return False
        
        # 현재 위치 및 주변 체크
        danger_range = 2  # 2칸 범위
        for dy in range(-danger_range, danger_range + 1):
            for dx in range(-danger_range, danger_range + 1):
                check_y = grid_y + dy
                check_x = grid_x + dx
                
                if 0 <= check_y < 13 and 0 <= check_x < 15:
                    idx = check_y * 15 + check_x
                    # 물풍선이나 물줄기가 있으면 위험
                    if map_bombs[idx] > 0.5 or map_waves[idx] > 0.5:
                        return True
        
        return False
    
    def _placed_bomb_near_enemy(self, my_x, my_y, enemy_x, enemy_y):
        """
        적 근처에 물풍선을 설치했는지 판단
        
        Returns:
            적 근처 물풍선 설치 여부
        """
        # 간단하게 거리로 판단 (150 픽셀 이내)
        dist = np.sqrt((my_x - enemy_x)**2 + (my_y - enemy_y)**2)
        return dist < 150
    
    def __enter__(self):
        """Context manager"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager"""
        self.disconnect()