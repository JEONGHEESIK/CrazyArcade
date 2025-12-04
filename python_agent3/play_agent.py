"""
학습된 에이전트로 게임 플레이
"""
import argparse
import torch
import numpy as np
from dqn_agent import DQNAgent
from ppo_agent import PPOAgent
from game_interface import GameEnvironment
import config


def play_game(agent_type='dqn', model_path=None, num_episodes=10, render=True, port=None):
    """
    학습된 모델로 게임 플레이
    
    Args:
        agent_type: 'dqn' 또는 'ppo'
        model_path: 모델 파일 경로
        num_episodes: 플레이할 에피소드 수
        render: 게임 화면 표시 여부
        port: 게임 서버 포트 (12345=Player1, 12346=Player2)
    """
    # 디바이스 설정
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 에이전트 초기화
    if agent_type.lower() == 'dqn':
        agent = DQNAgent(device=device)
        if model_path is None:
            model_path = f"{config.MODEL_DIR}/dqn_episode_1000.pth"
    elif agent_type.lower() == 'ppo':
        agent = PPOAgent(device=device)
        if model_path is None:
            model_path = f"{config.MODEL_DIR}/ppo_episode_1000.pth"
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    # 모델 로드
    print(f"Loading model from {model_path}...")
    try:
        agent.load(model_path)
        agent.set_eval_mode()  # 평가 모드로 설정
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # 게임 환경 연결
    if port is None:
        port = config.GAME_PORT  # 기본값: 12345 (Player 1)
    
    player_name = "Player 1" if port == 12345 else "Player 2" if port == 12346 else f"Port {port}"
    env = GameEnvironment(port=port)
    if not env.connect():
        print("Failed to connect to game server!")
        print("Please make sure the CrazyArcade game is running.")
        return
    
    print("\n" + "="*60)
    print("Starting game play with trained agent!")
    print(f"Player: {player_name} (Port {port})")
    print(f"Agent type: {agent_type.upper()}")
    print(f"Model: {model_path}")
    print(f"Episodes: {num_episodes}")
    print("="*60 + "\n")
    
    # 통계 변수
    total_wins = 0
    total_losses = 0
    total_draws = 0
    total_rewards = []
    total_steps = []
    
    try:
        for episode in range(1, num_episodes + 1):
            # 에피소드 초기화
            state = env.reset()
            if state is None:
                print("Failed to reset environment!")
                break
            
            episode_reward = 0
            episode_steps = 0
            done = False
            
            print(f"\n[Episode {episode}/{num_episodes}] Starting...")
            
            # 에피소드 실행
            while not done and episode_steps < config.MAX_STEPS_PER_EPISODE:
                # 행동 선택 (평가 모드 - 탐험 없음)
                action = agent.select_action(state, training=False)
                
                # 행동 실행
                next_state, reward, done, info = env.step(action)
                
                if next_state is None:
                    print("Connection lost!")
                    done = True
                    break
                
                episode_reward += reward
                episode_steps += 1
                state = next_state
                
                # 중요한 이벤트 출력
                if 'trap_enemy' in info and info['trap_enemy']:
                    print(f"  [Step {episode_steps}] ⭐ Trapped enemy!")
                if 'pop_enemy' in info and info['pop_enemy']:
                    pop_type = info.get('pop_type', 'unknown')
                    print(f"  [Step {episode_steps}] 💥 Popped enemy ({pop_type})!")
                if 'get_trapped' in info and info['get_trapped']:
                    print(f"  [Step {episode_steps}] ⚠️ Got trapped!")
                if 'item' in info:
                    item_type = info['item']
                    early = " (EARLY BONUS!)" if info.get('early_bonus', False) else ""
                    print(f"  [Step {episode_steps}] 🎁 Collected {item_type}{early}")
            
            # 에피소드 결과 처리
            result = info.get('result', 'unknown')
            if result == 'win':
                total_wins += 1
                result_emoji = "🏆"
            elif result == 'died':
                total_losses += 1
                result_emoji = "💀"
            else:
                total_draws += 1
                result_emoji = "🤝"
            
            total_rewards.append(episode_reward)
            total_steps.append(episode_steps)
            
            # 에피소드 요약
            print(f"\n[Episode {episode}] {result_emoji} Result: {result.upper()}")
            print(f"  Steps: {episode_steps}")
            print(f"  Total Reward: {episode_reward:.2f}")
            print(f"  Average Reward: {episode_reward/episode_steps:.2f}")
            
            # 현재까지 통계
            print(f"\n[Overall Stats]")
            print(f"  Win Rate: {total_wins}/{episode} ({100*total_wins/episode:.1f}%)")
            print(f"  Loss Rate: {total_losses}/{episode} ({100*total_losses/episode:.1f}%)")
            print(f"  Draw Rate: {total_draws}/{episode} ({100*total_draws/episode:.1f}%)")
            print(f"  Avg Reward: {np.mean(total_rewards):.2f}")
            print(f"  Avg Steps: {np.mean(total_steps):.1f}")
    
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user!")
    
    finally:
        # 최종 통계
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        print(f"Total Episodes: {len(total_rewards)}")
        print(f"Wins: {total_wins} ({100*total_wins/len(total_rewards):.1f}%)")
        print(f"Losses: {total_losses} ({100*total_losses/len(total_rewards):.1f}%)")
        print(f"Draws: {total_draws} ({100*total_draws/len(total_rewards):.1f}%)")
        print(f"Average Reward: {np.mean(total_rewards):.2f} ± {np.std(total_rewards):.2f}")
        print(f"Average Steps: {np.mean(total_steps):.1f} ± {np.std(total_steps):.1f}")
        print(f"Best Reward: {max(total_rewards):.2f}")
        print(f"Worst Reward: {min(total_rewards):.2f}")
        print("="*60)
        
        # 연결 종료
        env.disconnect()
        print("\nDisconnected from game server.")


def main():
    parser = argparse.ArgumentParser(description='Play CrazyArcade with trained agent')
    parser.add_argument('--agent', type=str, default='dqn', choices=['dqn', 'ppo'],
                        help='Agent type (dqn or ppo)')
    parser.add_argument('--model', type=str, default=None,
                        help='Path to model file (default: models/{agent}_episode_1000.pth)')
    parser.add_argument('--episodes', type=int, default=10,
                        help='Number of episodes to play (default: 10)')
    parser.add_argument('--port', type=int, default=None, choices=[12345, 12346],
                        help='Game server port: 12345=Player1, 12346=Player2 (default: 12345)')
    parser.add_argument('--no-render', action='store_true',
                        help='Disable game rendering')
    
    args = parser.parse_args()
    
    play_game(
        agent_type=args.agent,
        model_path=args.model,
        num_episodes=args.episodes,
        render=not args.no_render,
        port=args.port
    )


if __name__ == "__main__":
    main()
