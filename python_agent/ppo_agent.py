"""
PPO (Proximal Policy Optimization) 에이전트 (수정됨: 초기화 균형 + 엔트로피 강화)
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical
import numpy as np
import config


class ActorCritic(nn.Module):
    """
    하이브리드 Actor-Critic: 시각(CNN)과 감각(MLP)의 융합
    """
    
    def __init__(self, state_size, action_size, hidden_size=512):
        super(ActorCritic, self).__init__()
        
        # ==========================================
        # 1. 시각(Vision) 처리 영역 (Shared Feature)
        # ==========================================
        # 입력: (Batch, 3, 13, 15) -> 폭탄맵, 아이템맵, 물줄기맵
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        
        # CNN 출력을 펼쳤을 때의 크기: 13 * 15 * 64 = 12480
        self.cnn_out_size = 13 * 15 * 64
        
        # ==========================================
        # 2. 감각(Sensor) 처리 영역 (Shared Feature)
        # ==========================================
        # 입력: 전체 607개 중 맵(585개)을 뺀 나머지 (22개)
        self.sensor_fc = nn.Linear(22, 64)
        
        # ==========================================
        # 3. 통합 특징 추출 (Fusion)
        # ==========================================
        # 입력: CNN출력(12480) + 센서출력(64) = 12544
        self.fusion_fc = nn.Linear(self.cnn_out_size + 64, hidden_size)
        
        # ==========================================
        # 4. 머리(Head) 분리 - Actor와 Critic
        # ==========================================
        
        # Actor (행동 결정): 어떤 행동을 할 확률 (Softmax)
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, action_size),
            nn.Softmax(dim=-1)
        )
        
        # Critic (가치 판단): 이 상태가 얼마나 좋은가 (Scalar)
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1)
        )
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        """가중치 초기화 (CNN과 Linear를 구분하여 초기화 + Actor 균등화)"""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
        
        # 🔥 [핵심 수정] Actor의 마지막 레이어(판단 영역)를 강제로 0에 가깝게 초기화
        # 이렇게 하면 학습 시작 시 모든 행동의 확률이 거의 균등(1/6)하게 나옴
        # 특정 행동(IDLE)으로 초반에 쏠리는 것을 방지함
        actor_output_layer = self.actor[2] # Sequential의 2번째가 마지막 Linear
        if isinstance(actor_output_layer, nn.Linear):
            nn.init.constant_(actor_output_layer.weight, 0.01)
            nn.init.constant_(actor_output_layer.bias, 0)
    
    def forward(self, x):
        """
        데이터 흐름: Input -> (Slicing) -> CNN/MLP -> Fusion -> Split -> Actor/Critic
        """
        batch_size = x.size(0)
        
        # === 데이터 분리 수술 (DQN과 동일한 로직) ===
        # 1. 맵 데이터 추출 (18번 인덱스부터 585개)
        map_bombs = x[:, 18 : 18+195].view(batch_size, 1, 13, 15)
        map_items = x[:, 18+195 : 18+195*2].view(batch_size, 1, 13, 15)
        map_waves = x[:, 18+195*2 : 18+195*3].view(batch_size, 1, 13, 15)
        
        visual_input = torch.cat([map_bombs, map_items, map_waves], dim=1) # (Batch, 3, 13, 15)
        
        # 2. 센서 데이터 추출 (앞 18개 + 뒤 4개)
        sensor_input = torch.cat([x[:, :18], x[:, -4:]], dim=1)  # (Batch, 22)
        
        # === Feature Extraction ===
        
        # 시각 처리
        v = F.relu(self.conv1(visual_input))
        v = F.relu(self.conv2(v))
        v = F.relu(self.conv3(v))
        v = v.view(batch_size, -1)  # Flatten
        
        # 감각 처리
        s = F.relu(self.sensor_fc(sensor_input))
        
        # 결합 (Fusion)
        combined = torch.cat([v, s], dim=1)
        shared_features = F.relu(self.fusion_fc(combined))
        
        # === Dual Head Output ===
        action_probs = self.actor(shared_features)
        state_value = self.critic(shared_features)
        
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
                 c2=0.05,  # 🔥 [수정] Entropy coefficient 상향 (0.02 -> 0.05) : 탐험 강제
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