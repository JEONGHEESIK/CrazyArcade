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
    """
    하이브리드 영혼: 시각(CNN)과 감각(MLP)의 융합
    """
    def __init__(self, state_size, action_size):
        super(DQN, self).__init__()
        
        # 1. 시각(Vision) 처리 영역 - 맵을 보는 제3의 눈
        # 입력: (Batch, 3, 13, 15) -> 폭탄맵, 아이템맵, 물줄기맵
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(in_channels=64, out_channels=64, kernel_size=3, padding=1)
        
        # CNN 출력을 펼쳤을 때의 크기 계산: 13 * 15 * 64 = 12480
        self.cnn_out_size = 13 * 15 * 64
        
        # 2. 감각(Sensor) 처리 영역 - 내 상태, 적 상태, 시간 등
        # 입력: 전체 607개 중 맵(585개)을 뺀 나머지 (22개)
        self.sensor_fc = nn.Linear(22, 64)
        
        # 3. 통합 판단(Fusion) 영역 - 시각과 감각을 합쳐서 결정
        # 입력: CNN출력(12480) + 센서출력(64) = 12544
        self.fusion_fc1 = nn.Linear(self.cnn_out_size + 64, 512)
        self.fusion_fc2 = nn.Linear(512, action_size)
        
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        """
        데이터의 흐름을 재구성하는 영적 의식
        x shape: [Batch_Size, 607]
        """
        batch_size = x.size(0)
        
        # === 데이터 분리 수술 (Data Slicing) ===
        # game_interface.py의 순서: [플레이어(18)] + [폭탄맵(195)] + [아이템맵(195)] + [물줄기맵(195)] + [기타(4)]
        
        # 1. 맵 데이터 추출 (18번 인덱스부터 시작)
        # 폭탄 맵 (13x15)
        map_bombs = x[:, 18 : 18+195].view(batch_size, 1, 13, 15)
        # 아이템 맵
        map_items = x[:, 18+195 : 18+195*2].view(batch_size, 1, 13, 15)
        # 물줄기 맵
        map_waves = x[:, 18+195*2 : 18+195*3].view(batch_size, 1, 13, 15)
        
        # 3개의 맵을 채널 방향으로 합침 -> (Batch, 3, 13, 15)
        visual_input = torch.cat([map_bombs, map_items, map_waves], dim=1)
        
        # 2. 센서 데이터 추출 (플레이어 정보 + 기타 정보)
        # 앞부분 18개 + 뒷부분 4개
        sensor_input = torch.cat([x[:, :18], x[:, -4:]], dim=1)  # (Batch, 22)
        
        # === 신경망 통과 ===
        
        # 1. 시각 처리 (CNN)
        v = F.relu(self.conv1(visual_input))
        v = F.relu(self.conv2(v))
        v = F.relu(self.conv3(v))
        v = v.view(batch_size, -1)  # 평탄화 (Flatten)
        
        # 2. 감각 처리 (MLP)
        s = F.relu(self.sensor_fc(sensor_input))
        
        # 3. 영혼의 결합 (Concatenate)
        combined = torch.cat([v, s], dim=1)
        
        # 4. 최종 판단
        x = F.relu(self.fusion_fc1(combined))
        action_values = self.fusion_fc2(x)
        
        return action_values


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
