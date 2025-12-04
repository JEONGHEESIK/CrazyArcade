"""
PPO 에이전트 학습 스크립트 (Player 2)
"""
import sys
import os
import time
import numpy as np
import torch
from game_interface import GameEnvironment
from ppo_agent import PPOAgent
import config

def train_ppo(episodes=1000, port=12346, model_path=None):
    """
    PPO 에이전트 학습
    
    Args:
        episodes: 학습 에피소드 수
        port: 게임 서버 포트
        model_path: 기존 모델 경로 (계속 학습 시)
    """
    print(f"=== PPO Training Started (Port: {port}) ===")
    
    # 환경 및 에이전트 초기화
    env = GameEnvironment(port=port)
    agent = PPOAgent()
    
    # 기존 모델 로드
    if model_path and os.path.exists(model_path):
        agent.load(model_path)
        print(f"Loaded existing model from {model_path}")
    
    # 환경 연결
    if not env.connect():
        print("Failed to connect to game server!")
        return
    
    print("Connected to game server. Waiting for game to start...")
    time.sleep(2)
    
    # 학습 통계
    episode_rewards = []
    episode_lengths = []
    wins = 0
    losses = 0
    draws = 0
    
    try:
        for episode in range(episodes):
            print(f"\n[PPO] Starting Episode {episode + 1}/{episodes}")
            state = env.reset()
            if state is None:
                print(f"[PPO] Episode {episode + 1}: Failed to reset environment")
                continue
            
            print(f"[PPO] Episode {episode + 1}: Environment reset successful")
            total_reward = 0
            steps = 0
            done = False
            
            # 에피소드 실행 (게임 1판 = 1 에피소드)
            while not done:
                # 행동 선택
                action = agent.select_action(state, training=True)
                
                # 행동 실행
                next_state, reward, done, info = env.step(action)
                
                if next_state is None:
                    print(f"[PPO] Episode {episode + 1}, Step {steps}: Connection lost")
                    break
                
                # 10스텝마다 진행 상황 출력
                if steps % 10 == 0:
                    print(f"[PPO] Episode {episode + 1}, Step {steps}: reward={reward:.2f}, done={done}")
                
                # 경험 저장
                agent.remember(state, action, reward, next_state, done)
                
                state = next_state
                total_reward += reward
                steps += 1
                
                # 최대 스텝 제한 (안전장치)
                if steps >= config.MAX_STEPS_PER_EPISODE:
                    print(f"Episode {episode + 1}: Max steps reached")
                    done = True
            
            # 에피소드 종료 후 학습
            loss = agent.train()
            
            # 에피소드 종료 통계
            episode_rewards.append(total_reward)
            episode_lengths.append(steps)
            
            # 승패 기록
            if 'result' in info:
                if info['result'] == 'win':
                    wins += 1
                elif info['result'] == 'died':
                    losses += 1
                elif info['result'] == 'draw':
                    draws += 1
            
            # 로그 출력
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(episode_rewards[-10:])
                avg_length = np.mean(episode_lengths[-10:])
                total_eps = episode + 1
                win_rate = wins / total_eps if total_eps > 0 else 0
                
                print(f"Episode {episode + 1}/{episodes}")
                print(f"  Avg Reward (last 10): {avg_reward:.2f}")
                print(f"  Avg Length (last 10): {avg_length:.1f}")
                print(f"  Win Rate: {win_rate:.2%} (W/L/D = {wins}/{losses}/{draws})")
                print(f"  Loss: {loss:.4f}" if loss else "  Loss: N/A")
                print(f"  Memory: {len(agent.memory.states)}")
            
            # 모델 저장
            if (episode + 1) % config.SAVE_FREQUENCY == 0:
                save_path = f"{config.MODEL_DIR}/ppo_episode_{episode + 1}.pth"
                os.makedirs(config.MODEL_DIR, exist_ok=True)
                agent.save(save_path)
                print(f"Model saved to {save_path}")
    
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
    
    finally:
        # 최종 모델 저장
        final_path = f"{config.MODEL_DIR}/ppo_final.pth"
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        agent.save(final_path)
        print(f"Final model saved to {final_path}")
        
        # 환경 종료
        env.disconnect()
        
        # 최종 통계
        print("\n=== Training Summary ===")
        total_eps = len(episode_rewards)
        print(f"Total Episodes: {total_eps}")
        print(f"Total Wins: {wins}")
        print(f"Total Losses: {losses}")
        print(f"Total Draws: {draws}")
        print(f"Win Rate: {wins / total_eps if total_eps > 0 else 0:.2%}")
        print(f"Avg Reward: {np.mean(episode_rewards):.2f}")
        print(f"Avg Episode Length: {np.mean(episode_lengths):.1f}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train PPO agent")
    parser.add_argument("--episodes", type=int, default=1000, help="Number of episodes")
    parser.add_argument("--port", type=int, default=12346, help="Game server port")
    parser.add_argument("--model", type=str, default=None, help="Path to existing model")
    
    args = parser.parse_args()
    
    train_ppo(episodes=args.episodes, port=args.port, model_path=args.model)
