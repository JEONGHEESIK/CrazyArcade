"""
Self-Play 학습 스크립트
Player 1 (DQN) vs Player 2 (PPO) 동시 학습
"""
import subprocess
import sys
import time
import os

def start_agent(script_name, port, model_path=None):
    """
    에이전트 프로세스 시작
    
    Args:
        script_name: 학습 스크립트 이름
        port: 게임 서버 포트
        model_path: 기존 모델 경로
    
    Returns:
        프로세스 객체
    """
    cmd = [sys.executable, script_name, "--port", str(port)]
    
    if model_path:
        cmd.extend(["--model", model_path])
    
    print(f"Starting {script_name} on port {port}...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    return process

def monitor_processes(processes):
    """
    프로세스 모니터링 및 출력
    
    Args:
        processes: 프로세스 딕셔너리 {name: process}
    """
    while True:
        for name, process in processes.items():
            # 프로세스 출력 읽기
            line = process.stdout.readline()
            if line:
                print(f"[{name}] {line.strip()}")
            
            # 프로세스 종료 확인
            if process.poll() is not None:
                print(f"[{name}] Process terminated with code {process.returncode}")
                return False
        
        time.sleep(0.01)

def main(episodes=1000, dqn_model=None, ppo_model=None):
    """
    Self-Play 학습 메인 함수
    
    Args:
        episodes: 학습 에피소드 수
        dqn_model: DQN 기존 모델 경로
        ppo_model: PPO 기존 모델 경로
    """
    print("=== Self-Play Training Started ===")
    print(f"Episodes: {episodes}")
    print(f"Player 1 (DQN) Port: 12345")
    print(f"Player 2 (PPO) Port: 12346")
    print()
    
    # 에이전트 프로세스 시작
    dqn_process = start_agent("train_dqn.py", 12345, dqn_model)
    time.sleep(2)  # DQN이 먼저 연결되도록 대기
    
    ppo_process = start_agent("train_ppo.py", 12346, ppo_model)
    time.sleep(2)  # PPO 연결 대기
    
    processes = {
        "DQN": dqn_process,
        "PPO": ppo_process
    }
    
    print("\nBoth agents started. Waiting for game to begin...")
    print("Press Ctrl+C to stop training.\n")
    
    try:
        # 프로세스 모니터링
        monitor_processes(processes)
    
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
    
    finally:
        # 프로세스 종료
        print("\nTerminating agent processes...")
        for name, process in processes.items():
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                print(f"[{name}] Terminated")
        
        print("\n=== Self-Play Training Ended ===")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Self-Play Training")
    parser.add_argument("--episodes", type=int, default=5000, help="Number of episodes")
    parser.add_argument("--dqn-model", type=str, default=None, help="Path to existing DQN model")
    parser.add_argument("--ppo-model", type=str, default=None, help="Path to existing PPO model")
    
    args = parser.parse_args()
    
    main(episodes=args.episodes, dqn_model=args.dqn_model, ppo_model=args.ppo_model)
