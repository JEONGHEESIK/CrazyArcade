"""
진짜 DQN vs PPO 대결
Player 1 (DQN) vs Player 2 (PPO)
"""
import torch
import subprocess
import time
import sys


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='True DQN vs PPO Battle')
    parser.add_argument('--episodes', type=int, default=1000, help='Number of episodes')
    args = parser.parse_args()
    
    print("=" * 60)
    print("진짜 DQN vs PPO 대결")
    print("=" * 60)
    print()
    print("실행 순서:")
    print("1. Dual Mock 서버 시작 (포트 12345, 12346)")
    print("2. Player 1 (DQN) 시작 (포트 12345)")
    print("3. Player 2 (PPO) 시작 (포트 12346)")
    print()
    print("=" * 60)
    print()
    
    # 1. Dual Mock 서버 시작
    print("1️⃣  Dual Mock 서버 시작 중...")
    server_process = subprocess.Popen(
        ['python', 'mock_game_server_dual.py', '--port1', '12345', '--port2', '12346'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("   서버 시작 대기 (3초)...")
    time.sleep(3)
    
    # 2. Player 1 (DQN) 시작
    print("\n2️⃣  Player 1 (DQN) 시작 중...")
    dqn_process = subprocess.Popen(
        ['python', 'train_single_agent.py', '--agent', 'dqn', '--port', '12345', 
         '--episodes', str(args.episodes), '--name', 'Player1_DQN'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("   Player 1 시작 대기 (2초)...")
    time.sleep(2)
    
    # 3. Player 2 (PPO) 시작
    print("\n3️⃣  Player 2 (PPO) 시작 중...")
    ppo_process = subprocess.Popen(
        ['python', 'train_single_agent.py', '--agent', 'ppo', '--port', '12346',
         '--episodes', str(args.episodes), '--name', 'Player2_PPO'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("\n" + "=" * 60)
    print("🎮 게임 시작!")
    print("=" * 60)
    print()
    print("로그 확인:")
    print("  - 서버: 위 출력")
    print("  - Player 1 (DQN): logs/Player1_DQN/")
    print("  - Player 2 (PPO): logs/Player2_PPO/")
    print()
    print("중단: Ctrl+C")
    print("=" * 60)
    print()
    
    try:
        # 서버 출력 실시간 표시
        while True:
            output = server_process.stdout.readline()
            if output:
                print(output.strip())
            
            # 프로세스 종료 체크
            if server_process.poll() is not None:
                break
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n중단 요청...")
    
    finally:
        print("\n프로세스 종료 중...")
        server_process.terminate()
        dqn_process.terminate()
        ppo_process.terminate()
        
        server_process.wait()
        dqn_process.wait()
        ppo_process.wait()
        
        print("모든 프로세스 종료됨")


if __name__ == "__main__":
    main()
