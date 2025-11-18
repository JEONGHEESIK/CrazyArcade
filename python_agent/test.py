"""
학습된 에이전트 테스트 스크립트
"""
import torch
import numpy as np
from pathlib import Path
import argparse

from agent import DQNAgent
from game_interface import GameEnvironment
import config


def test_agent(model_path, num_episodes=10, render=True):
    """
    학습된 에이전트 테스트
    
    Args:
        model_path: 모델 파일 경로
        num_episodes: 테스트 에피소드 수
        render: 렌더링 여부
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # 에이전트 생성 및 모델 로드
    agent = DQNAgent(device=device)
    agent.load(model_path)
    agent.set_eval_mode()
    
    # 게임 환경
    env = GameEnvironment()
    
    if not env.connect():
        print("Failed to connect to game server!")
        return
    
    try:
        total_rewards = []
        total_lengths = []
        wins = 0
        losses = 0
        
        for episode in range(1, num_episodes + 1):
            state = env.reset()
            if state is None:
                print(f"Episode {episode}: Failed to reset")
                continue
            
            episode_reward = 0.0
            steps = 0
            
            while True:
                # 행동 선택 (탐험 없이)
                action = agent.select_action(state, training=False)
                
                # 환경에서 행동 실행
                next_state, reward, done, info = env.step(action)
                
                if next_state is None:
                    print(f"Episode {episode}: Connection lost")
                    break
                
                episode_reward += reward
                steps += 1
                state = next_state
                
                if done:
                    if info.get('result') == 'win':
                        wins += 1
                    elif info.get('result') == 'died':
                        losses += 1
                    break
            
            total_rewards.append(episode_reward)
            total_lengths.append(steps)
            
            print(f"Episode {episode:3d} | "
                  f"Reward: {episode_reward:8.2f} | "
                  f"Steps: {steps:4d} | "
                  f"Result: {info.get('result', 'unknown')}")
        
        # 통계 출력
        print(f"\n{'='*60}")
        print(f"Test Results ({num_episodes} episodes)")
        print(f"{'='*60}")
        print(f"Average Reward: {np.mean(total_rewards):.2f} ± {np.std(total_rewards):.2f}")
        print(f"Average Length: {np.mean(total_lengths):.2f} ± {np.std(total_lengths):.2f}")
        print(f"Wins: {wins} ({wins/num_episodes*100:.1f}%)")
        print(f"Losses: {losses} ({losses/num_episodes*100:.1f}%)")
        print(f"{'='*60}\n")
    
    finally:
        env.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Test trained DQN agent')
    parser.add_argument('--model', type=str, required=True, help='Path to model file')
    parser.add_argument('--episodes', type=int, default=10, help='Number of test episodes')
    parser.add_argument('--no-render', action='store_true', help='Disable rendering')
    
    args = parser.parse_args()
    
    test_agent(
        model_path=args.model,
        num_episodes=args.episodes,
        render=not args.no_render
    )


if __name__ == "__main__":
    main()
