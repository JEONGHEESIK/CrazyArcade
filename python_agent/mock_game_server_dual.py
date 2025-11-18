#!/usr/bin/env python3
"""
Dual Mock 게임 서버 (진짜 AI vs AI)
두 개의 AI 에이전트가 서로 대결
"""
import socket
import json
import numpy as np
import threading
import time
import random


class DualMockGameServer:
    """두 AI가 대결하는 Mock 게임 서버"""
    
    def __init__(self, port1=12345, port2=12346):
        self.port1 = port1
        self.port2 = port2
        self.running = False
        self.socket1 = None
        self.socket2 = None
        self.client1 = None
        self.client2 = None
        
        # 게임 상태
        self.reset_game()
        
        self.game_time = 0.0
        self.step_count = 0
        self.max_steps = 500
    
    def reset_game(self):
        """게임 리셋"""
        self.player1_pos = [200.0, 200.0]
        self.player2_pos = [500.0, 500.0]
        self.player1_alive = True
        self.player2_alive = True
        self.player1_bombs = 1
        self.player1_power = 1
        self.player1_speed = 2.0
        self.player2_bombs = 1
        self.player2_power = 1
        self.player2_speed = 2.0
        
        # 물방울 시스템 (크레이지아케이드 핵심!)
        self.player1_trapped = False  # 물방울에 갇혔는지
        self.player1_trap_timer = 0   # 물방울 타이머 (50 스텝 = 5초)
        self.player2_trapped = False
        self.player2_trap_timer = 0
        self.TRAP_TIMER = 50  # 50 스텝 후 자동 KO
        
        # 맵 상태 (13x15)
        self.map_bombs = np.zeros((13, 15), dtype=int)
        self.map_items = np.zeros((13, 15), dtype=int)
        self.map_waves = np.zeros((13, 15), dtype=int)
        
        # 물풍선 타이머 (각 위치별)
        self.bomb_timers = {}  # {(x, y): remaining_steps}
        self.BOMB_TIMER = 30  # 30 스텝 후 폭발 (3초)
        
        # 아이템 생성
        self._spawn_items()
        
        self.game_time = 0.0
        self.step_count = 0
    
    def _spawn_items(self):
        """랜덤 위치에 아이템 생성"""
        for _ in range(5):
            row = random.randint(0, 12)
            col = random.randint(0, 14)
            self.map_items[row, col] = random.randint(1, 4)
    
    def start(self):
        """서버 시작"""
        # 소켓 1 (Player 1)
        self.socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket1.bind(('127.0.0.1', self.port1))
        self.socket1.listen(1)
        
        # 소켓 2 (Player 2)
        self.socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket2.bind(('127.0.0.1', self.port2))
        self.socket2.listen(1)
        
        self.running = True
        
        print(f"🎮 Dual Mock 게임 서버 시작")
        print(f"Player 1 포트: {self.port1}")
        print(f"Player 2 포트: {self.port2}")
        print("두 AI 에이전트 연결 대기 중...\n")
        
        # Player 1 연결 대기
        print(f"Player 1 연결 대기 (포트 {self.port1})...")
        self.client1, addr1 = self.socket1.accept()
        print(f"✅ Player 1 연결됨: {addr1}")
        
        # Player 2 연결 대기
        print(f"Player 2 연결 대기 (포트 {self.port2})...")
        self.client2, addr2 = self.socket2.accept()
        print(f"✅ Player 2 연결됨: {addr2}")
        
        print("\n🎮 게임 시작!\n")
        
        # 게임 루프
        try:
            self._game_loop()
        except Exception as e:
            print(f"오류: {e}")
        finally:
            self.stop()
    
    def _game_loop(self):
        """게임 메인 루프"""
        episode = 0
        
        while self.running:
            episode += 1
            self.reset_game()
            print(f"Episode {episode} 시작")
            
            while self.running and self.step_count < self.max_steps:
                # 두 플레이어 모두 살아있는지 체크
                if not self.player1_alive or not self.player2_alive:
                    break
                
                # Player 1 상태 전송 및 행동 수신
                state1 = self._get_state(player=1)
                action1 = self._send_and_receive(self.client1, state1)
                if action1 is None:
                    print("Player 1 연결 끊김")
                    return
                
                # Player 2 상태 전송 및 행동 수신
                state2 = self._get_state(player=2)
                action2 = self._send_and_receive(self.client2, state2)
                if action2 is None:
                    print("Player 2 연결 끊김")
                    return
                
                # 게임 업데이트 (두 행동 동시 실행)
                self._update_game(action1, action2)
                
                time.sleep(0.01)
            
            # 게임 종료 처리
            winner = 0
            if not self.player1_alive and not self.player2_alive:
                result = "무승부"
            elif not self.player1_alive:
                result = "Player 2 승리"
                winner = 2
            elif not self.player2_alive:
                result = "Player 1 승리"
                winner = 1
            else:
                result = "시간 초과"
                winner = 0

            # 최종 상태 전송 (game_over 신호 포함)
            final_state1 = self._get_state(player=1)
            final_state2 = self._get_state(player=2)
            final_state1['game_over'] = True
            final_state2['game_over'] = True
            final_state1['winner'] = winner
            final_state2['winner'] = winner
            self._send_state_only(self.client1, final_state1)
            self._send_state_only(self.client2, final_state2)

            print(f"Episode {episode} 종료: {result} (스텝: {self.step_count})\n")
            time.sleep(0.5)
    
    def _send_and_receive(self, client, state):
        """상태 전송 및 행동 수신"""
        try:
            # 상태 전송
            state_json = json.dumps(state) + '\n'
            client.sendall(state_json.encode('utf-8'))
            
            # 행동 수신
            data = client.recv(1024)
            if not data:
                return None
            
            msg = data.decode('utf-8').strip()
            
            # RESET 명령 처리
            if msg == 'RESET':
                return 0  # IDLE
            
            try:
                action = int(msg)
                return action
            except ValueError:
                return 0  # IDLE
        
        except Exception as e:
            print(f"통신 오류: {e}")
            return None
    
    def _send_state_only(self, client, state):
        """행동을 기다리지 않고 상태만 전송"""
        try:
            state_json = json.dumps(state) + '\n'
            client.sendall(state_json.encode('utf-8'))
        except Exception as e:
            print(f"상태 전송 오류: {e}")
    
    def _get_state(self, player):
        """플레이어별 상태 생성"""
        if player == 1:
            my_pos = self.player1_pos
            my_speed = self.player1_speed
            my_bombs = self.player1_bombs
            my_power = self.player1_power
            my_alive = self.player1_alive
            my_trapped = self.player1_trapped
            my_trap_timer = self.player1_trap_timer
            
            enemy_pos = self.player2_pos
            enemy_speed = self.player2_speed
            enemy_bombs = self.player2_bombs
            enemy_power = self.player2_power
            enemy_alive = self.player2_alive
            enemy_trapped = self.player2_trapped
            enemy_trap_timer = self.player2_trap_timer
        else:
            my_pos = self.player2_pos
            my_speed = self.player2_speed
            my_bombs = self.player2_bombs
            my_power = self.player2_power
            my_alive = self.player2_alive
            my_trapped = self.player2_trapped
            my_trap_timer = self.player2_trap_timer
            
            enemy_pos = self.player1_pos
            enemy_speed = self.player1_speed
            enemy_bombs = self.player1_bombs
            enemy_power = self.player1_power
            enemy_alive = self.player1_alive
            enemy_trapped = self.player1_trapped
            enemy_trap_timer = self.player1_trap_timer
        
        state = {
            'player_index': player,
            'my_x': my_pos[0],
            'my_y': my_pos[1],
            'my_speed': my_speed,
            'my_bomb_count': my_bombs,
            'my_power': my_power,
            'my_state': 2,
            'my_alive': my_alive,
            'my_trapped': my_trapped,  # 물방울 상태
            'my_trap_timer': my_trap_timer,  # 남은 시간
            
            'enemy_x': enemy_pos[0],
            'enemy_y': enemy_pos[1],
            'enemy_speed': enemy_speed,
            'enemy_bomb_count': enemy_bombs,
            'enemy_power': enemy_power,
            'enemy_state': 2,
            'enemy_alive': enemy_alive,
            'enemy_trapped': enemy_trapped,  # 적 물방울 상태
            'enemy_trap_timer': enemy_trap_timer,  # 적 남은 시간
            
            'map_bombs': self.map_bombs.flatten().tolist(),
            'map_items': self.map_items.flatten().tolist(),
            'map_waves': self.map_waves.flatten().tolist(),
            
            'game_time': self.game_time,
            'game_over': (not self.player1_alive or not self.player2_alive or self.step_count >= self.max_steps),
            'winner': self._determine_winner()
        }
        return state

    def _determine_winner(self):
        """승자 결정 (0: 무승부/시간초과, 1 또는 2: 승자)"""
        if not self.player1_alive and not self.player2_alive:
            return 0
        if not self.player1_alive:
            return 2
        if not self.player2_alive:
            return 1
        if self.step_count >= self.max_steps:
            return 0
        return 0
    
    def _update_game(self, action1, action2):
        """게임 상태 업데이트 (두 행동 동시)"""
        self.step_count += 1
        self.game_time += 0.1
        
        speed = 5.0
        
        # Player 1 행동 실행 (갇혀있으면 움직일 수 없음!)
        if not self.player1_trapped:
            if action1 == 1:  # UP
                self.player1_pos[1] = max(53, self.player1_pos[1] - speed)
            elif action1 == 2:  # DOWN
                self.player1_pos[1] = min(676, self.player1_pos[1] + speed)
            elif action1 == 3:  # LEFT
                self.player1_pos[0] = max(26, self.player1_pos[0] - speed)
            elif action1 == 4:  # RIGHT
                self.player1_pos[0] = min(780, self.player1_pos[0] + speed)
            elif action1 == 5:  # PLACE_BOMB
                grid_x = int((self.player1_pos[0] - 26) / 52)
                grid_y = int((self.player1_pos[1] - 53) / 52)
                if 0 <= grid_x < 15 and 0 <= grid_y < 13:
                    pos = (grid_y, grid_x)
                    if pos not in self.bomb_timers:  # 이미 물풍선이 없으면
                        self.map_bombs[grid_y, grid_x] = 1
                        self.bomb_timers[pos] = self.BOMB_TIMER
        
        # Player 2 행동 실행 (갇혀있으면 움직일 수 없음!)
        if not self.player2_trapped:
            if action2 == 1:  # UP
                self.player2_pos[1] = max(53, self.player2_pos[1] - speed)
            elif action2 == 2:  # DOWN
                self.player2_pos[1] = min(676, self.player2_pos[1] + speed)
            elif action2 == 3:  # LEFT
                self.player2_pos[0] = max(26, self.player2_pos[0] - speed)
            elif action2 == 4:  # RIGHT
                self.player2_pos[0] = min(780, self.player2_pos[0] + speed)
            elif action2 == 5:  # PLACE_BOMB
                grid_x = int((self.player2_pos[0] - 26) / 52)
                grid_y = int((self.player2_pos[1] - 53) / 52)
                if 0 <= grid_x < 15 and 0 <= grid_y < 13:
                    pos = (grid_y, grid_x)
                    if pos not in self.bomb_timers:  # 이미 물풍선이 없으면
                        self.map_bombs[grid_y, grid_x] = 1
                        self.bomb_timers[pos] = self.BOMB_TIMER
        
        # 아이템 수집 체크 (Player 1)
        self._check_item_collection(1)
        
        # 아이템 수집 체크 (Player 2)
        self._check_item_collection(2)
        
        # 물풍선 타이머 업데이트 및 폭발
        self._update_bombs()
        
        # 물방울 타이머 업데이트
        self._update_trap_timers()
        
        # 물방울 터트리기 체크
        self._check_trap_pop()
    
    def _check_item_collection(self, player):
        """아이템 수집 체크"""
        if player == 1:
            pos = self.player1_pos
        else:
            pos = self.player2_pos
        
        grid_x = int((pos[0] - 26) / 52)
        grid_y = int((pos[1] - 53) / 52)
        
        if 0 <= grid_x < 15 and 0 <= grid_y < 13:
            if self.map_items[grid_y, grid_x] > 0:
                item_type = self.map_items[grid_y, grid_x]
                
                if player == 1:
                    if item_type == 1:  # Ballon
                        self.player1_bombs = min(6, self.player1_bombs + 1)
                    elif item_type == 2:  # Potion
                        self.player1_power = min(7, self.player1_power + 1)
                    elif item_type == 4:  # Skate
                        self.player1_speed = min(5.0, self.player1_speed + 1.0)
                else:
                    if item_type == 1:
                        self.player2_bombs = min(6, self.player2_bombs + 1)
                    elif item_type == 2:
                        self.player2_power = min(7, self.player2_power + 1)
                    elif item_type == 4:
                        self.player2_speed = min(5.0, self.player2_speed + 1.0)
                
                self.map_items[grid_y, grid_x] = 0
    
    def _update_bombs(self):
        """물풍선 타이머 업데이트 및 폭발"""
        # 타이머 감소
        expired_bombs = []
        for pos, timer in list(self.bomb_timers.items()):
            self.bomb_timers[pos] = timer - 1
            if self.bomb_timers[pos] <= 0:
                expired_bombs.append(pos)
        
        # 폭발 처리
        if expired_bombs:
            self.map_waves = np.zeros((13, 15), dtype=int)
            destroyed_items = []  # 파괴된 아이템 위치
            
            for pos in expired_bombs:
                grid_y, grid_x = pos
                # 물줄기 생성 (십자 모양)
                wave_positions = [(grid_y, grid_x)]
                
                # 상하좌우로 파워만큼 퍼짐
                for dy in range(-2, 3):  # 파워 2 가정
                    if 0 <= grid_y + dy < 13:
                        wave_positions.append((grid_y + dy, grid_x))
                for dx in range(-2, 3):
                    if 0 <= grid_x + dx < 15:
                        wave_positions.append((grid_y, grid_x + dx))
                
                # 물줄기 표시 및 아이템 파괴 체크
                for wy, wx in wave_positions:
                    self.map_waves[wy, wx] = 1
                    # 물줄기가 닿은 곳의 아이템 파괴!
                    if self.map_items[wy, wx] > 0:
                        self.map_items[wy, wx] = 0
                        destroyed_items.append((wy, wx))
                
                # 물풍선 제거
                self.map_bombs[grid_y, grid_x] = 0
                del self.bomb_timers[pos]
            
            # 충돌 체크
            self._check_wave_collision(1)
            self._check_wave_collision(2)
        else:
            self.map_waves = np.zeros((13, 15), dtype=int)
    
    def _check_wave_collision(self, player):
        """물줄기 충돌 체크 - 물방울에 갇힘!"""
        if player == 1:
            pos = self.player1_pos
            already_trapped = self.player1_trapped
        else:
            pos = self.player2_pos
            already_trapped = self.player2_trapped
        
        grid_x = int((pos[0] - 26) / 52)
        grid_y = int((pos[1] - 53) / 52)
        
        if 0 <= grid_x < 15 and 0 <= grid_y < 13:
            if self.map_waves[grid_y, grid_x] > 0 and not already_trapped:
                # 물방울에 갇힘! (즉시 사망 X)
                if player == 1:
                    self.player1_trapped = True
                    self.player1_trap_timer = self.TRAP_TIMER
                else:
                    self.player2_trapped = True
                    self.player2_trap_timer = self.TRAP_TIMER
    
    def _update_trap_timers(self):
        """물방울 타이머 업데이트"""
        # Player 1 타이머
        if self.player1_trapped:
            self.player1_trap_timer -= 1
            if self.player1_trap_timer <= 0:
                # 시간 초과 → 자동 KO!
                self.player1_alive = False
                self.player1_trapped = False
        
        # Player 2 타이머
        if self.player2_trapped:
            self.player2_trap_timer -= 1
            if self.player2_trap_timer <= 0:
                # 시간 초과 → 자동 KO!
                self.player2_alive = False
                self.player2_trapped = False
    
    def _check_trap_pop(self):
        """물방울 터트리기 체크"""
        import math
        
        # Player 1이 Player 2 물방울 터트리기
        if self.player2_trapped and not self.player1_trapped:
            dist = math.sqrt(
                (self.player1_pos[0] - self.player2_pos[0])**2 +
                (self.player1_pos[1] - self.player2_pos[1])**2
            )
            if dist < 52:  # 한 칸 거리 (직접 터트림!)
                self.player2_alive = False
                self.player2_trapped = False
        
        # Player 2가 Player 1 물방울 터트리기
        if self.player1_trapped and not self.player2_trapped:
            dist = math.sqrt(
                (self.player2_pos[0] - self.player1_pos[0])**2 +
                (self.player2_pos[1] - self.player1_pos[1])**2
            )
            if dist < 52:  # 한 칸 거리 (직접 터트림!)
                self.player1_alive = False
                self.player1_trapped = False
    
    def stop(self):
        """서버 중지"""
        self.running = False
        if self.client1:
            self.client1.close()
        if self.client2:
            self.client2.close()
        if self.socket1:
            self.socket1.close()
        if self.socket2:
            self.socket2.close()


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dual Mock 게임 서버')
    parser.add_argument('--port1', type=int, default=12345, help='Player 1 포트')
    parser.add_argument('--port2', type=int, default=12346, help='Player 2 포트')
    args = parser.parse_args()
    
    server = DualMockGameServer(port1=args.port1, port2=args.port2)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n서버 중지 중...")
        server.stop()
        print("서버 중지됨")


if __name__ == "__main__":
    main()
