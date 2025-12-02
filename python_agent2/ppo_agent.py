"""
PPO (Proximal Policy Optimization) 에이전트
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import config


class ActorCritic(nn.Module):
    """Actor-Critic 네트워크"""
    
    def __init__(self, state_size, action_size, hidden_size=256):
        super(ActorCritic, self).__init__()
        
        # 공유 레이어
        self.shared = nn.Sequential(
            nn.Linear(state_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU()
        )
        
        # Actor (정책 네트워크)
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, action_size),
            nn.Softmax(dim=-1)
        )
        
        # Critic (가치 네트워크)
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1)
        )
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        """가중치 초기화"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """순전파"""
        shared = self.shared(x)
        action_probs = self.actor(shared)
        state_value = self.critic(shared)
        return action_probs, state_value


class PPOMemory:
    """PPO 메모리 (에피소드 단위)"""
    
    def __init__(self):
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
    
    def store(self, state, action, reward, value, log_prob, done):
        """경험 저장"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)
    
    def clear(self):
        """메모리 초기화"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
    
    def get_batches(self):
        """배치 데이터 반환"""
        return (
            np.array(self.states),
            np.array(self.actions),
            np.array(self.rewards),
            np.array(self.values),
            np.array(self.log_probs),
            np.array(self.dones)
        )


class PPOAgent:
    """PPO 에이전트"""
    
    def __init__(self, 
                 state_size=config.STATE_SIZE,
                 action_size=config.ACTION_SIZE,
                 device=None,
                 learning_rate=0.0005,
                 gamma=None,
                 gae_lambda=0.95,
                 clip_epsilon=0.2,
                 c1=0.5,  # Value loss coefficient
                 c2=0.02,  # Entropy coefficient (탐험 강화)
                 epochs=10,
                 batch_size=64):
        
        self.state_size = state_size
        self.action_size = action_size
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 하이퍼파라미터
        self.gamma = gamma if gamma is not None else config.GAMMA
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.c1 = c1
        self.c2 = c2
        self.epochs = epochs
        self.batch_size = batch_size
        
        # 네트워크
        self.policy = ActorCritic(state_size, action_size).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=learning_rate)
        
        # 메모리
        self.memory = PPOMemory()
        
        print(f"PPO Agent initialized on {self.device}")
    
    def select_action(self, state, training=True):
        """
        행동 선택
        
        Args:
            state: 현재 상태
            training: 학습 모드 여부
        
        Returns:
            action: 선택된 행동
        """
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action_probs, state_value = self.policy(state_tensor)
        
        if training:
            # 확률 분포에서 샘플링
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            
            # 메모리에 저장 (나중에 사용)
            self._last_state = state
            self._last_action = action.item()
            self._last_value = state_value.item()
            self._last_log_prob = log_prob.item()
        else:
            # 가장 높은 확률의 행동 선택
            action = torch.argmax(action_probs, dim=1)
        
        return action.item()
    
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
        # select_action에서 저장한 정보 사용
        self.memory.store(
            self._last_state,
            self._last_action,
            reward,
            self._last_value,
            self._last_log_prob,
            done
        )
    
    def train(self):
        """
        PPO 학습
        
        Returns:
            loss: 평균 손실
        """
        # 메모리가 비어있으면 학습 안 함
        if len(self.memory.states) == 0:
            return None
        
        # 배치 데이터 가져오기
        states, actions, rewards, values, old_log_probs, dones = self.memory.get_batches()
        
        # Advantage 계산 (GAE)
        advantages = self._compute_gae(rewards, values, dones)
        returns = advantages + values
        
        # 정규화
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Tensor 변환
        states_tensor = torch.FloatTensor(states).to(self.device)
        actions_tensor = torch.LongTensor(actions).to(self.device)
        old_log_probs_tensor = torch.FloatTensor(old_log_probs).to(self.device)
        returns_tensor = torch.FloatTensor(returns).to(self.device).squeeze()
        advantages_tensor = torch.FloatTensor(advantages).to(self.device)
        
        # 여러 에포크 학습
        total_loss = 0
        for _ in range(self.epochs):
            # 순전파
            action_probs, state_values = self.policy(states_tensor)
            state_values = state_values.squeeze()
            
            # 현재 log probability 계산
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions_tensor)
            entropy = dist.entropy().mean()
            
            # Ratio 계산
            ratio = torch.exp(new_log_probs - old_log_probs_tensor)
            
            # Surrogate loss
            surr1 = ratio * advantages_tensor
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages_tensor
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            critic_loss = F.mse_loss(state_values, returns_tensor)
            
            # Total loss
            loss = actor_loss + self.c1 * critic_loss - self.c2 * entropy
            
            # 역전파
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            self.optimizer.step()
            
            total_loss += loss.item()
        
        # 메모리 초기화
        self.memory.clear()
        
        return total_loss / self.epochs
    
    def _compute_gae(self, rewards, values, dones):
        """
        Generalized Advantage Estimation (GAE) 계산
        
        Args:
            rewards: 보상 배열
            values: 가치 배열
            dones: 종료 여부 배열
        
        Returns:
            advantages: Advantage 배열
        """
        advantages = np.zeros_like(rewards)
        last_gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            advantages[t] = last_gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * last_gae
        
        return advantages
    
    def save(self, filepath):
        """모델 저장"""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, filepath)
        print(f"PPO model saved to {filepath}")
    
    def load(self, filepath):
        """모델 로드"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        print(f"PPO model loaded from {filepath}")
    
    def set_eval_mode(self):
        """평가 모드 설정"""
        self.policy.eval()
    
    def set_train_mode(self):
        """학습 모드 설정"""
        self.policy.train()
