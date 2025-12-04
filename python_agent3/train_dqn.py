"""
DQN 에이전트 학습 스크립트 (Player 1)
"""
import sys
import os
import time
import numpy as np
import torch
from game_interface import GameEnvironment
from dqn_agent import DQNAgent
import config

def train_dqn(episodes=1000, port=12345, model_path=None):
    """
    DQN 에이전트 학습
    
    Args:
        episodes: 학습 에피소드 수
        port: 게임 서버 포트
        model_path: 기존 모델 경로 (계속 학습 시)
    """
    print(f"=== DQN Training Started (Port: {port}) ===")
    
    # 환경 및 에이전트 초기화
    env = GameEnvironment(port=port)
    agent = DQNAgent()
    
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
    
    try:
        for episode in range(episodes):
            print(f"\n[DQN] Starting Episode {episode + 1}/{episodes}")
            state = env.reset()
            if state is None:
                print(f"[DQN] Episode {episode + 1}: Failed to reset environment")
                continue
            
            print(f"[DQN] Episode {episode + 1}: Environment reset successful")
            total_reward = 0
            steps = 0
            done = False
            
            # 에피소드 실행 (게임 1판 = 1 에피소드)
            while not done:
                # 행동 선택
                action = agent.select_action(state)
                
                # 행동 실행
                next_state, reward, done, info = env.step(action)
                
                if next_state is None:
                    print(f"[DQN] Episode {episode + 1}, Step {steps}: Connection lost")
                    break
                
                # 10스텝마다 진행 상황 출력
                if steps % 10 == 0:
                    print(f"[DQN] Episode {episode + 1}, Step {steps}: reward={reward:.2f}, done={done}")
                
                # 경험 저장
                agent.remember(state, action, reward, next_state, done)
                
                # 학습
                loss = agent.train()
                
                state = next_state
                total_reward += reward
                steps += 1
                
                # 최대 스텝 제한 (안전장치)
                if steps >= config.MAX_STEPS_PER_EPISODE:
                    print(f"Episode {episode + 1}: Max steps reached")
                    done = True
            
            # 에피소드 종료 통계
            episode_rewards.append(total_reward)
            episode_lengths.append(steps)
            
            # 승패 기록
            if 'result' in info:
                if info['result'] == 'win':
                    wins += 1
                elif info['result'] == 'died':
                    losses += 1
            
            # 타겟 네트워크 업데이트
            if (episode + 1) % config.TARGET_UPDATE_FREQUENCY == 0:
                agent.update_target_network()
            
            # 로그 출력
            if (episode + 1) % 10 == 0:
                avg_reward = np.mean(episode_rewards[-10:])
                avg_length = np.mean(episode_lengths[-10:])
                win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
                
                print(f"Episode {episode + 1}/{episodes}")
                print(f"  Avg Reward: {avg_reward:.2f}")
                print(f"  Avg Length: {avg_length:.1f}")
                print(f"  Win Rate: {win_rate:.2%} ({wins}W / {losses}L)")
                print(f"  Epsilon: {agent.epsilon:.3f}")
                print(f"  Memory: {len(agent.memory)}")
            
            # 모델 저장
            if (episode + 1) % config.SAVE_FREQUENCY == 0:
                save_path = f"{config.MODEL_DIR}/dqn_episode_{episode + 1}.pth"
                os.makedirs(config.MODEL_DIR, exist_ok=True)
                agent.save(save_path)
                print(f"Model saved to {save_path}")
    
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
    
    finally:
        # 최종 모델 저장
        final_path = f"{config.MODEL_DIR}/dqn_final.pth"
        os.makedirs(config.MODEL_DIR, exist_ok=True)
        agent.save(final_path)
        print(f"Final model saved to {final_path}")
        
        # 환경 종료
        env.disconnect()
        
        # 최종 통계
        print("\n=== Training Summary ===")
        print(f"Total Episodes: {len(episode_rewards)}")
        print(f"Total Wins: {wins}")
        print(f"Total Losses: {losses}")
        print(f"Win Rate: {wins / (wins + losses) if (wins + losses) > 0 else 0:.2%}")
        print(f"Avg Reward: {np.mean(episode_rewards):.2f}")
        print(f"Avg Episode Length: {np.mean(episode_lengths):.1f}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train DQN agent")
    parser.add_argument("--episodes", type=int, default=1000, help="Number of episodes")
    parser.add_argument("--port", type=int, default=12345, help="Game server port")
    parser.add_argument("--model", type=str, default=None, help="Path to existing model")
    
    args = parser.parse_args()
    
    train_dqn(episodes=args.episodes, port=args.port, model_path=args.model)
