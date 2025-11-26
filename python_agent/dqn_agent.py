"""
DQN (Deep Q-Network) 에이전트
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import random
from collections import deque
import config


class DQN(nn.Module):
    """DQN 네트워크"""
    
    def __init__(self, state_size, action_size, hidden_size=256):
        super(DQN, self).__init__()
        
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc4 = nn.Linear(hidden_size // 2, action_size)
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        """가중치 초기화"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """순전파"""
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        return self.fc4(x)


class ReplayMemory:
    """경험 재생 메모리"""
    
    def __init__(self, capacity=50000):
        self.memory = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """경험 저장"""
        self.memory.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        """배치 샘플링"""
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )
    
    def __len__(self):
        return len(self.memory)


class DQNAgent:
    """DQN 에이전트"""
    
    def __init__(self,
                 state_size=config.STATE_SIZE,
                 action_size=config.ACTION_SIZE,
                 device=None,
                 learning_rate=0.0001,
                 gamma=None,
                 epsilon_start=None,
                 epsilon_min=None,
                 epsilon_decay=None,
                 memory_size=None,
                 batch_size=None):
        
        self.state_size = state_size
        self.action_size = action_size
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 하이퍼파라미터
        self.learning_rate = learning_rate if learning_rate is not None else config.LEARNING_RATE
        self.gamma = gamma if gamma is not None else config.GAMMA
        self.epsilon = epsilon_start if epsilon_start is not None else config.EPSILON_START
        self.epsilon_min = epsilon_min if epsilon_min is not None else config.EPSILON_MIN
        self.epsilon_decay = epsilon_decay if epsilon_decay is not None else config.EPSILON_DECAY
        self.batch_size = batch_size if batch_size is not None else config.BATCH_SIZE
        
        # 네트워크
        self.policy_net = DQN(state_size, action_size).to(self.device)
        self.target_net = DQN(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # 옵티마이저
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        
        # 메모리
        memory_capacity = memory_size if memory_size is not None else config.MEMORY_SIZE
        self.memory = ReplayMemory(memory_capacity)
        
        print(f"DQN Agent initialized on {self.device}")
    
    def select_action(self, state, training=True):
        """
        행동 선택 (ε-greedy)
        
        Args:
            state: 현재 상태
            training: 학습 모드 여부
        
        Returns:
            action: 선택된 행동
        """
        if training and random.random() < self.epsilon:
            # 탐험: 랜덤 행동
            return random.randrange(self.action_size)
        else:
            # 활용: 최적 행동
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.policy_net(state_tensor)
                return q_values.argmax().item()
    
    def remember(self, state, action, reward, next_state, done):
        """
        경험 저장
        
        Args:
            state: 현재 상태
            action: 행동
            reward: 보상
            next_state: 다음 상태
            done: 종료 여부
        """
        self.memory.push(state, action, reward, next_state, done)
    
    def train(self):
        """
        DQN 학습
        
        Returns:
            loss: 손실 값
        """
        # 메모리가 배치 크기보다 작으면 학습 안 함
        if len(self.memory) < self.batch_size:
            return None
        
        # 배치 샘플링
        states, actions, rewards, next_states, dones = self.memory.sample(self.batch_size)
        
        # Tensor 변환
        states_tensor = torch.FloatTensor(states).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        rewards_tensor = torch.FloatTensor(rewards).to(self.device)
        next_states_tensor = torch.FloatTensor(next_states).to(self.device)
        dones_tensor = torch.FloatTensor(dones).to(self.device)
        
        # 현재 Q 값
        current_q_values = self.policy_net(states_tensor).gather(1, actions_tensor.unsqueeze(1)).squeeze(1)
        
        # 다음 Q 값 (Double DQN)
        with torch.no_grad():
            next_actions = self.policy_net(next_states_tensor).argmax(1)
            next_q_values = self.target_net(next_states_tensor).gather(1, next_actions.unsqueeze(1)).squeeze(1)
            target_q_values = rewards_tensor + (1 - dones_tensor) * self.gamma * next_q_values
        
        # 손실 계산
        loss = F.mse_loss(current_q_values, target_q_values)
        
        # 역전파
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # Epsilon 감소
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return loss.item()
    
    def update_target_network(self):
        """타겟 네트워크 업데이트"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def save(self, filepath):
        """모델 저장"""
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
        }, filepath)
        print(f"DQN model saved to {filepath}")
    
    def load(self, filepath):
        """모델 로드"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint.get('epsilon', self.epsilon_min)
        print(f"DQN model loaded from {filepath}")
    
    def set_eval_mode(self):
        """평가 모드 설정"""
        self.policy_net.eval()
    
    def set_train_mode(self):
        """학습 모드 설정"""
        self.policy_net.train()
