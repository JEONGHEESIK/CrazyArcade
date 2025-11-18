"""
단일 에이전트 학습 (DQN 또는 PPO)
"""
import torch
import numpy as np
from agent import DQNAgent
from ppo_agent import PPOAgent
from game_interface import GameEnvironment
import config
from datetime import datetime
import os


class SingleAgentTrainer:
    """단일 에이전트 트레이너"""
    
    def __init__(self, agent_type='dqn', port=12345, name='Agent', load_path=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.agent_type = agent_type
        self.name = name
        
        print(f"{'='*60}")
        print(f"{name} ({agent_type.upper()})")
        print(f"{'='*60}\n")
        
        # 에이전트 생성
        if agent_type.lower() == 'dqn':
            self.agent = DQNAgent(device=self.device)
        elif agent_type.lower() == 'ppo':
            self.agent = PPOAgent(device=self.device)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # 체크포인트 로드 (있다면)
        if load_path:
            try:
                self.agent.load(load_path)
                self.agent.set_train_mode()
                print(f"Loaded checkpoint: {load_path}")
            except FileNotFoundError:
                print(f"[Warning] Checkpoint not found: {load_path}. Starting from scratch.")
            except Exception as e:
                print(f"[Warning] Failed to load checkpoint '{load_path}': {e}")
        
        # 환경
        self.env = GameEnvironment(port=port)
        
        # 통계
        self.episode_rewards = []
        self.episode_lengths = []
        self.episode_losses = []
        self.wins = 0
        
        # 로그 디렉토리
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = f"logs/{name}_{timestamp}"
        self.model_dir = f"models/{name}_{timestamp}"
        
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
    
    def train(self, episodes=1000, max_steps=500):
        """
        학습 실행
        
        Args:
            episodes: 에피소드 수
            max_steps: 에피소드당 최대 스텝
        """
        print(f"Starting training: {episodes} episodes\n")
        
        # 연결
        if not self.env.connect():
            print("Failed to connect to game server!")
            return
        
        try:
            for episode in range(1, episodes + 1):
                reward, length, loss = self._run_episode(max_steps)
                
                self.episode_rewards.append(reward)
                self.episode_lengths.append(length)
                if loss is not None:
                    self.episode_losses.append(loss)
                
                # 로그
                if episode % 10 == 0:
                    self._log_progress(episode)
                
                # 모델 저장
                if episode % 500 == 0:
                    self._save_model(episode)
                
                # Epsilon 감소 (DQN만)
                if self.agent_type == 'dqn':
                    self.agent.decay_epsilon()
                    
                    # 타겟 네트워크 업데이트
                    if episode % config.TARGET_UPDATE_FREQUENCY == 0:
                        self.agent.update_target_network()
        
        except KeyboardInterrupt:
            print("\nTraining interrupted")
        
        finally:
            self.env.disconnect()
            self._save_model('final')
            print(f"\n{self.name} training completed!")
    
    def _run_episode(self, max_steps):
        """에피소드 실행"""
        state = self.env.reset()
        total_reward = 0
        steps = 0
        losses = []
        done = False
        
        while not done and steps < max_steps:
            # 행동 선택
            action = self.agent.select_action(state, training=True)
            
            # 환경 스텝
            next_state, reward, done, info = self.env.step(action)
            
            # 경험 저장
            self.agent.remember(state, action, reward, next_state, done)
            
            # 학습 (에이전트 유형별로 처리)
            loss = None
            if self.agent_type == 'dqn':
                loss = self.agent.train()
                if loss is not None:
                    losses.append(loss)
            
            # 상태 업데이트
            state = next_state
            total_reward += reward
            steps += 1
            
            # 승리 체크
            if info.get('result') == 'win':
                self.wins += 1
        
        # PPO는 에피소드 종료 후 학습 실행
        if self.agent_type == 'ppo':
            loss = self.agent.train()
            if loss is not None:
                losses.append(loss)
        
        avg_loss = np.mean(losses) if losses else None
        return total_reward, steps, avg_loss
    
    def _log_progress(self, episode):
        """진행 상황 로그"""
        avg_reward = np.mean(self.episode_rewards[-100:])
        avg_length = np.mean(self.episode_lengths[-100:])
        avg_loss = np.mean(self.episode_losses[-100:]) if self.episode_losses else 0
        win_rate = self.wins / episode * 100
        
        epsilon_str = ""
        if self.agent_type == 'dqn':
            epsilon_str = f"ε={self.agent.epsilon:.3f} "
        
        print(f"[{self.name}] Episode {episode:4d} | "
              f"Reward: {avg_reward:7.2f} | "
              f"Steps: {avg_length:4.0f} | "
              f"{epsilon_str}"
              f"Loss: {avg_loss:.4f} | "
              f"Wins: {win_rate:4.1f}%", flush=True)
    
    def _save_model(self, episode):
        """모델 저장"""
        filepath = f"{self.model_dir}/model_episode_{episode}.pth"
        self.agent.save(filepath)


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Single Agent Training')
    parser.add_argument('--agent', type=str, required=True, choices=['dqn', 'ppo'],
                       help='Agent type (dqn or ppo)')
    parser.add_argument('--port', type=int, required=True, help='Game server port')
    parser.add_argument('--episodes', type=int, default=1000, help='Number of episodes')
    parser.add_argument('--max-steps', type=int, default=500, help='Max steps per episode')
    parser.add_argument('--name', type=str, default='Agent', help='Agent name')
    parser.add_argument('--load-model', type=str, default=None, help='Path to checkpoint (.pth)')
    args = parser.parse_args()
    
    trainer = SingleAgentTrainer(
        agent_type=args.agent,
        port=args.port,
        name=args.name,
        load_path=args.load_model
    )
    
    trainer.train(episodes=args.episodes, max_steps=args.max_steps)


if __name__ == "__main__":
    main()
