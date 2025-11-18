"""
학습된 에이전트로 게임 플레이
"""
import torch
import argparse
import time
from agent import DQNAgent
from game_interface import GameInterface
import config


def play(model_path, host='127.0.0.1', port=12345, verbose=True):
    """
    학습된 에이전트로 게임 플레이
    
    Args:
        model_path: 모델 파일 경로
        host: 게임 서버 호스트
        port: 게임 서버 포트
        verbose: 상세 출력 여부
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    if verbose:
        print(f"Using device: {device}")
        print(f"Loading model from: {model_path}")
    
    # 에이전트 로드
    agent = DQNAgent(device=device)
    try:
        agent.load(model_path)
        agent.set_eval_mode()
        if verbose:
            print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # 게임 연결
    if verbose:
        print(f"Connecting to {host}:{port}...")
    
    interface = GameInterface(host=host, port=port)
    if not interface.connect():
        print("Connection failed! Make sure the game is running.")
        return
    
    if verbose:
        print("Connected! Starting to play...")
        print("Press Ctrl+C to stop\n")
    
    step_count = 0
    episode_count = 0
    total_reward = 0.0
    
    try:
        while True:
            # 상태 수신
            state = interface.receive_state()
            if state is None:
                if verbose:
                    print("Connection lost or game ended")
                break
            
            # 행동 선택 (탐험 없이, 최선의 행동만)
            action = agent.select_action(state, training=False)
            
            # 행동 이름 매핑
            action_names = ['IDLE', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'PLACE_BOMB']
            
            if verbose and step_count % 10 == 0:  # 10 스텝마다 출력
                print(f"Step {step_count:4d} | Action: {action_names[action]:12s}", end='\r')
            
            # 행동 전송
            if not interface.send_action(action):
                if verbose:
                    print("\nFailed to send action")
                break
            
            step_count += 1
            
            # 간단한 딜레이 (게임 속도 조절)
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    except Exception as e:
        print(f"\nError during play: {e}")
    
    finally:
        interface.disconnect()
        if verbose:
            print(f"\nTotal steps: {step_count}")
            print("Disconnected from game")


def main():
    parser = argparse.ArgumentParser(description='Play CrazyArcade with trained AI agent')
    parser.add_argument('--model', type=str, required=True, 
                       help='Path to trained model file (.pth)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                       help='Game server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=12345,
                       help='Game server port (default: 12345)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress verbose output')
    
    args = parser.parse_args()
    
    play(
        model_path=args.model,
        host=args.host,
        port=args.port,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
