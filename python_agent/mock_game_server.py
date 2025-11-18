#!/usr/bin/env python3
"""
Mock 게임 서버 (C++ 게임 없이 테스트용)
실제 게임 로직을 시뮬레이션합니다.
"""
import socket
import json
import numpy as np
import threading
import time
import random


class MockGameServer:
    """Mock 게임 서버"""
    
    def __init__(self, port=12345):
        self.port = port
        self.running = False
        self.socket = None
        
        # 게임 상태
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
        
        # 맵 상태 (13x15)
        self.map_bombs = np.zeros((13, 15), dtype=int)
        self.map_items = np.zeros((13, 15), dtype=int)
        self.map_waves = np.zeros((13, 15), dtype=int)
        
        # 아이템 생성
        self._spawn_items()
        
        self.game_time = 0.0
        self.step_count = 0
        self.max_steps = 500
    
    def _spawn_items(self):
        """랜덤 위치에 아이템 생성"""
        for _ in range(5):
            row = random.randint(0, 12)
            col = random.randint(0, 14)
            self.map_items[row, col] = random.randint(1, 4)
    
    def start(self):
        """서버 시작"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('127.0.0.1', self.port))
        self.socket.listen(1)
        self.running = True
        
        print(f"🎮 Mock 게임 서버 시작 (포트 {self.port})")
        print("Python 에이전트 연결 대기 중...")
        
        while self.running:
            try:
                client, addr = self.socket.accept()
                print(f"✅ 연결됨: {addr}")
                self._handle_client(client)
            except Exception as e:
                if self.running:
                    print(f"오류: {e}")
                break
    
    def _handle_client(self, client):
        """클라이언트 처리"""
        try:
            while self.running and self.step_count < self.max_steps:
                # 게임 상태 전송
                state = self._get_state()
                state_json = json.dumps(state) + '\n'
                client.sendall(state_json.encode('utf-8'))
                
                # 행동 수신
                data = client.recv(1024)
                if not data:
                    break
                
                msg = data.decode('utf-8').strip()
                
                # RESET 명령 처리
                if msg == 'RESET':
                    print("게임 리셋 요청")
                    self._reset_game()
                    continue
                
                # 행동 처리
                try:
                    action = int(msg)
                except ValueError:
                    print(f"잘못된 행동: {msg}")
                    continue
                
                # 게임 업데이트
                self._update_game(action)
                
                # 게임 종료 체크
                if not self.player1_alive or not self.player2_alive:
                    print(f"게임 종료! (스텝: {self.step_count})")
                    time.sleep(1)
                    self._reset_game()
                
                time.sleep(0.01)  # 게임 속도 조절
        
        except Exception as e:
            print(f"클라이언트 처리 오류: {e}")
        finally:
            client.close()
            print("연결 종료")
    
    def _get_state(self):
        """현재 게임 상태 반환"""
        state = {
            'player_index': 1,
            'my_x': self.player1_pos[0],
            'my_y': self.player1_pos[1],
            'my_speed': self.player1_speed,
            'my_bomb_count': self.player1_bombs,
            'my_power': self.player1_power,
            'my_state': 2,  # Wait
            'my_alive': self.player1_alive,
            
            'enemy_x': self.player2_pos[0],
            'enemy_y': self.player2_pos[1],
            'enemy_speed': self.player2_speed,
            'enemy_bomb_count': self.player2_bombs,
            'enemy_power': self.player2_power,
            'enemy_state': 2,
            'enemy_alive': self.player2_alive,
            
            'map_bombs': self.map_bombs.flatten().tolist(),
            'map_items': self.map_items.flatten().tolist(),
            'map_waves': self.map_waves.flatten().tolist(),
            
            'game_time': self.game_time,
            'game_over': not (self.player1_alive and self.player2_alive),
            'winner': 0 if (self.player1_alive and self.player2_alive) else (1 if self.player1_alive else 2)
        }
        return state
    
    def _update_game(self, action):
        """게임 상태 업데이트"""
        self.step_count += 1
        self.game_time += 0.1
        
        # 행동 실행
        speed = 5.0
        if action == 1:  # UP
            self.player1_pos[1] = max(53, self.player1_pos[1] - speed)
        elif action == 2:  # DOWN
            self.player1_pos[1] = min(676, self.player1_pos[1] + speed)
        elif action == 3:  # LEFT
            self.player1_pos[0] = max(26, self.player1_pos[0] - speed)
        elif action == 4:  # RIGHT
            self.player1_pos[0] = min(780, self.player1_pos[0] + speed)
        elif action == 5:  # PLACE_BOMB
            # 물풍선 설치 (간단한 시뮬레이션)
            grid_x = int((self.player1_pos[0] - 26) / 52)
            grid_y = int((self.player1_pos[1] - 53) / 52)
            if 0 <= grid_x < 15 and 0 <= grid_y < 13:
                self.map_bombs[grid_y, grid_x] = 1
        
        # 아이템 수집 체크
        grid_x = int((self.player1_pos[0] - 26) / 52)
        grid_y = int((self.player1_pos[1] - 53) / 52)
        if 0 <= grid_x < 15 and 0 <= grid_y < 13:
            if self.map_items[grid_y, grid_x] > 0:
                item_type = self.map_items[grid_y, grid_x]
                if item_type == 1:  # Ballon
                    self.player1_bombs = min(6, self.player1_bombs + 1)
                elif item_type == 2:  # Potion
                    self.player1_power = min(7, self.player1_power + 1)
                elif item_type == 4:  # Skate
                    self.player1_speed = min(5.0, self.player1_speed + 1.0)
                self.map_items[grid_y, grid_x] = 0
        
        # 적 AI (랜덤 이동)
        enemy_action = random.randint(0, 5)
        if enemy_action == 1:
            self.player2_pos[1] = max(53, self.player2_pos[1] - speed)
        elif enemy_action == 2:
            self.player2_pos[1] = min(676, self.player2_pos[1] + speed)
        elif enemy_action == 3:
            self.player2_pos[0] = max(26, self.player2_pos[0] - speed)
        elif enemy_action == 4:
            self.player2_pos[0] = min(780, self.player2_pos[0] + speed)
        
        # 충돌 체크 (간단한 시뮬레이션)
        dist = np.sqrt((self.player1_pos[0] - self.player2_pos[0])**2 + 
                      (self.player1_pos[1] - self.player2_pos[1])**2)
        
        # 물풍선 폭발 시뮬레이션 (10% 확률)
        if random.random() < 0.1:
            self.map_waves = self.map_bombs.copy()
            self.map_bombs = np.zeros((13, 15), dtype=int)
            
            # 물줄기에 맞았는지 체크
            p1_grid_x = int((self.player1_pos[0] - 26) / 52)
            p1_grid_y = int((self.player1_pos[1] - 53) / 52)
            if 0 <= p1_grid_x < 15 and 0 <= p1_grid_y < 13:
                if self.map_waves[p1_grid_y, p1_grid_x] > 0:
                    self.player1_alive = False
            
            p2_grid_x = int((self.player2_pos[0] - 26) / 52)
            p2_grid_y = int((self.player2_pos[1] - 53) / 52)
            if 0 <= p2_grid_x < 15 and 0 <= p2_grid_y < 13:
                if self.map_waves[p2_grid_y, p2_grid_x] > 0:
                    self.player2_alive = False
        else:
            self.map_waves = np.zeros((13, 15), dtype=int)
    
    def _reset_game(self):
        """게임 리셋"""
        self.player1_pos = [200.0, 200.0]
        self.player2_pos = [500.0, 500.0]
        self.player1_alive = True
        self.player2_alive = True
        self.map_bombs = np.zeros((13, 15), dtype=int)
        self.map_items = np.zeros((13, 15), dtype=int)
        self.map_waves = np.zeros((13, 15), dtype=int)
        self._spawn_items()
        self.game_time = 0.0
        self.step_count = 0
    
    def stop(self):
        """서버 중지"""
        self.running = False
        if self.socket:
            self.socket.close()


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock 게임 서버')
    parser.add_argument('--port', type=int, default=12345, help='포트 번호')
    args = parser.parse_args()
    
    server = MockGameServer(port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n서버 중지 중...")
        server.stop()
        print("서버 중지됨")


if __name__ == "__main__":
    main()
