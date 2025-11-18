"""
강화학습 학습 스크립트
"""
import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from torch.utils.tensorboard import SummaryWriter

from agent import DQNAgent, DoubleDQNAgent
from game_interface import GameEnvironment
import config


class Trainer:
    """학습 관리 클래스"""
    
    def __init__(self, agent_type="dqn", use_tensorboard=True):
        """
        Args:
            agent_type: "dqn" 또는 "double_dqn"
            use_tensorboard: TensorBoard 사용 여부
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {self.device}")
        
        # 에이전트 생성
        if agent_type == "double_dqn":
            self.agent = DoubleDQNAgent(device=self.device)
        else:
            self.agent = DQNAgent(device=self.device)
        
        # 게임 환경
        self.env = GameEnvironment()
        
        # 로그 디렉토리 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(config.LOG_DIR) / timestamp
        self.model_dir = Path(config.MODEL_DIR) / timestamp
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # TensorBoard
        self.use_tensorboard = use_tensorboard
        if use_tensorboard:
            self.writer = SummaryWriter(config.TENSORBOARD_DIR + f"/{timestamp}")
        
        # 통계
        self.episode_rewards = []
        self.episode_lengths = []
        self.losses = []
        
        print(f"Trainer initialized")
        print(f"Log directory: {self.log_dir}")
        print(f"Model directory: {self.model_dir}")
    
    def train(self, max_episodes=None, max_steps=None):
        """
        학습 실행
        
        Args:
            max_episodes: 최대 에피소드 수
            max_steps: 에피소드당 최대 스텝 수
        """
        max_episodes = max_episodes or config.MAX_EPISODES
        max_steps = max_steps or config.MAX_STEPS_PER_EPISODE
        
        print(f"\n{'='*60}")
        print(f"Starting training: {max_episodes} episodes")
        print(f"{'='*60}\n")
        
        # 게임 서버 연결
        if not self.env.connect():
            print("Failed to connect to game server!")
            return
        
        try:
            for episode in range(1, max_episodes + 1):
                episode_reward, episode_length, episode_loss = self._run_episode(episode, max_steps)
                
                # 통계 저장
                self.episode_rewards.append(episode_reward)
                self.episode_lengths.append(episode_length)
                if episode_loss is not None:
                    self.losses.append(episode_loss)
                
                # 타겟 네트워크 업데이트
                if episode % config.TARGET_UPDATE_FREQUENCY == 0:
                    self.agent.update_target_network()
                
                # Epsilon 감소
                self.agent.decay_epsilon()
                
                # 로그 출력
                self._log_episode(episode, episode_reward, episode_length, episode_loss)
                
                # 모델 저장
                if episode % config.SAVE_FREQUENCY == 0:
                    self._save_checkpoint(episode)
                
                # 통계 플롯
                if episode % 100 == 0:
                    self._plot_statistics()
        
        except KeyboardInterrupt:
            print("\n\nTraining interrupted by user")
        
        finally:
            # 최종 모델 저장
            self._save_checkpoint("final")
            self.env.disconnect()
            if self.use_tensorboard:
                self.writer.close()
            
            print(f"\n{'='*60}")
            print(f"Training completed!")
            print(f"{'='*60}\n")
    
    def _run_episode(self, episode, max_steps):
        """
        에피소드 실행
        
        Returns:
            (total_reward, steps, avg_loss)
        """
        state = self.env.reset()
        if state is None:
            print(f"Episode {episode}: Failed to reset environment")
            return 0.0, 0, None
        
        total_reward = 0.0
        episode_losses = []
        
        for step in range(max_steps):
            # 행동 선택
            action = self.agent.select_action(state, training=True)
            
            # 환경에서 행동 실행
            next_state, reward, done, info = self.env.step(action)
            
            if next_state is None:
                print(f"Episode {episode}: Connection lost at step {step}")
                break
            
            # 경험 저장
            self.agent.remember(state, action, reward, next_state, done)
            
            # 학습
            loss = self.agent.train()
            if loss is not None:
                episode_losses.append(loss)
            
            total_reward += reward
            state = next_state
            
            if done:
                break
        
        avg_loss = np.mean(episode_losses) if episode_losses else None
        
        return total_reward, step + 1, avg_loss
    
    def _log_episode(self, episode, reward, length, loss):
        """에피소드 로그 출력"""
        # 최근 100 에피소드 평균
        recent_rewards = self.episode_rewards[-100:]
        avg_reward = np.mean(recent_rewards)
        
        loss_str = f"{loss:.4f}" if loss is not None else "0.0000"
        
        print(f"Episode {episode:5d} | "
              f"Reward: {reward:8.2f} | "
              f"Avg(100): {avg_reward:8.2f} | "
              f"Steps: {length:4d} | "
              f"Epsilon: {self.agent.epsilon:.4f} | "
              f"Loss: {loss_str}", flush=True)
        
        # TensorBoard 로그
        if self.use_tensorboard:
            self.writer.add_scalar('Reward/Episode', reward, episode)
            self.writer.add_scalar('Reward/Average', avg_reward, episode)
            self.writer.add_scalar('Episode/Length', length, episode)
            self.writer.add_scalar('Agent/Epsilon', self.agent.epsilon, episode)
            if loss is not None:
                self.writer.add_scalar('Loss/Episode', loss, episode)
    
    def _save_checkpoint(self, episode):
        """체크포인트 저장"""
        filepath = self.model_dir / f"model_episode_{episode}.pth"
        self.agent.save(filepath)
    
    def _plot_statistics(self):
        """통계 플롯"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 에피소드 보상
        axes[0, 0].plot(self.episode_rewards, alpha=0.6, label='Episode Reward')
        if len(self.episode_rewards) >= 100:
            moving_avg = np.convolve(self.episode_rewards, np.ones(100)/100, mode='valid')
            axes[0, 0].plot(range(99, len(self.episode_rewards)), moving_avg, 
                           label='Moving Average (100)', linewidth=2)
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Reward')
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # 에피소드 길이
        axes[0, 1].plot(self.episode_lengths, alpha=0.6)
        axes[0, 1].set_xlabel('Episode')
        axes[0, 1].set_ylabel('Steps')
        axes[0, 1].set_title('Episode Lengths')
        axes[0, 1].grid(True)
        
        # 손실
        if self.losses:
            axes[1, 0].plot(self.losses, alpha=0.6)
            axes[1, 0].set_xlabel('Training Step')
            axes[1, 0].set_ylabel('Loss')
            axes[1, 0].set_title('Training Loss')
            axes[1, 0].grid(True)
        
        # Epsilon 감소
        epsilons = [config.EPSILON_START * (config.EPSILON_DECAY ** i) 
                   for i in range(len(self.episode_rewards))]
        epsilons = [max(e, config.EPSILON_MIN) for e in epsilons]
        axes[1, 1].plot(epsilons)
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('Epsilon')
        axes[1, 1].set_title('Exploration Rate (Epsilon)')
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig(self.log_dir / 'training_statistics.png', dpi=150)
        plt.close()


def main():
    """메인 함수"""
    # 학습 설정
    trainer = Trainer(agent_type="dqn", use_tensorboard=True)
    
    # 학습 시작
    trainer.train(
        max_episodes=config.MAX_EPISODES,
        max_steps=config.MAX_STEPS_PER_EPISODE
    )


if __name__ == "__main__":
    main()
