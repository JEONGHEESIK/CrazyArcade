"""
DQN 에이전트
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from pathlib import Path

from model import create_model
from replay_buffer import ReplayBuffer
import config


class DQNAgent:
    """DQN 강화학습 에이전트"""
    
    def __init__(self, state_size=None, action_size=None, device=None):
        """
        Args:
            state_size: 상태 공간 크기
            action_size: 행동 공간 크기
            device: 학습 디바이스 (cuda/cpu)
        """
        self.state_size = state_size or config.STATE_SIZE
        self.action_size = action_size or config.ACTION_SIZE
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 하이퍼파라미터
        self.gamma = config.GAMMA
        self.epsilon = config.EPSILON_START
        self.epsilon_min = config.EPSILON_MIN
        self.epsilon_decay = config.EPSILON_DECAY
        self.learning_rate = config.LEARNING_RATE
        self.batch_size = config.BATCH_SIZE
        self.target_update_freq = config.TARGET_UPDATE_FREQUENCY
        
        # 네트워크 생성
        self.policy_net = create_model(
            "dqn",
            self.state_size,
            self.action_size,
            hidden_size_1=config.HIDDEN_SIZE_1,
            hidden_size_2=config.HIDDEN_SIZE_2,
            hidden_size_3=config.HIDDEN_SIZE_3
        ).to(self.device)
        
        self.target_net = create_model(
            "dqn",
            self.state_size,
            self.action_size,
            hidden_size_1=config.HIDDEN_SIZE_1,
            hidden_size_2=config.HIDDEN_SIZE_2,
            hidden_size_3=config.HIDDEN_SIZE_3
        ).to(self.device)
        
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # 옵티마이저
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        
        # 경험 재생 버퍼
        self.memory = ReplayBuffer(config.MEMORY_SIZE)
        
        # 통계
        self.steps = 0
        self.episodes = 0
        
        print(f"DQN Agent initialized on {self.device}")
        print(f"State size: {self.state_size}, Action size: {self.action_size}")
    
    def select_action(self, state, training=True):
        """
        행동 선택 (Epsilon-greedy)
        
        Args:
            state: 현재 상태
            training: 학습 모드 여부
        
        Returns:
            선택된 행동 (0-5)
        """
        if training and random.random() < self.epsilon:
            # 탐험: 무작위 행동
            return random.randrange(self.action_size)
        
        # 활용: Q값이 최대인 행동
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax(dim=1).item()
    
    def remember(self, state, action, reward, next_state, done):
        """경험 저장"""
        self.memory.push(state, action, reward, next_state, done)
    
    def train(self):
        """
        네트워크 학습 (1 step)
        
        Returns:
            loss 값
        """
        if len(self.memory) < self.batch_size:
            return None
        
        # 미니배치 샘플링
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # Tensor 변환
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # 현재 Q값 계산
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # 다음 Q값 계산 (타겟 네트워크 사용)
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # 손실 계산 및 역전파 (Huber loss로 안정화)
        loss_fn = nn.SmoothL1Loss()
        loss = loss_fn(current_q_values, target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping (안정성 향상)
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        
        self.optimizer.step()
        
        self.steps += 1
        
        return loss.item()
    
    def update_target_network(self):
        """타겟 네트워크 업데이트"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def decay_epsilon(self):
        """Epsilon 감소"""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
    
    def save(self, filepath):
        """모델 저장"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps': self.steps,
            'episodes': self.episodes,
        }, filepath)
        
        print(f"Model saved to {filepath}")
    
    def load(self, filepath):
        """모델 로드"""
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.steps = checkpoint['steps']
        self.episodes = checkpoint['episodes']
        
        print(f"Model loaded from {filepath}")
    
    def set_train_mode(self):
        """학습 모드 설정"""
        self.policy_net.train()
    
    def set_eval_mode(self):
        """평가 모드 설정"""
        self.policy_net.eval()


class DoubleDQNAgent(DQNAgent):
    """Double DQN 에이전트 (개선된 버전)"""
    
    def train(self):
        """Double DQN 학습"""
        if len(self.memory) < self.batch_size:
            return None
        
        # 미니배치 샘플링
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # Tensor 변환
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # 현재 Q값 계산
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Double DQN: policy net으로 행동 선택, target net으로 Q값 계산
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1)
            next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # 손실 계산 및 역전파
        loss = nn.MSELoss()(current_q_values, target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        self.steps += 1
        
        return loss.item()
