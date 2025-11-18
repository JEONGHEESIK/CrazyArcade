"""
DQN (Deep Q-Network) 모델 정의
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class DQN(nn.Module):
    """Deep Q-Network"""
    
    def __init__(self, state_size, action_size, hidden_size_1=256, hidden_size_2=256, hidden_size_3=128):
        super(DQN, self).__init__()
        
        self.fc1 = nn.Linear(state_size, hidden_size_1)
        self.bn1 = nn.BatchNorm1d(hidden_size_1)
        
        self.fc2 = nn.Linear(hidden_size_1, hidden_size_2)
        self.bn2 = nn.BatchNorm1d(hidden_size_2)
        
        self.fc3 = nn.Linear(hidden_size_2, hidden_size_3)
        self.bn3 = nn.BatchNorm1d(hidden_size_3)
        
        self.fc4 = nn.Linear(hidden_size_3, action_size)
        
        # 가중치 초기화
        self._initialize_weights()
    
    def _initialize_weights(self):
        """가중치 초기화 (Xavier initialization)"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """순전파"""
        # BatchNorm은 배치 크기가 1일 때 문제가 있으므로 조건부 사용
        if self.training and x.size(0) == 1:
            # 단일 샘플일 때는 BatchNorm 스킵
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            x = F.relu(self.fc3(x))
        else:
            x = F.relu(self.bn1(self.fc1(x)))
            x = F.relu(self.bn2(self.fc2(x)))
            x = F.relu(self.bn3(self.fc3(x)))
        x = self.fc4(x)
        return x


class DuelingDQN(nn.Module):
    """Dueling DQN - 더 나은 성능을 위한 개선된 버전"""
    
    def __init__(self, state_size, action_size, hidden_size_1=256, hidden_size_2=256):
        super(DuelingDQN, self).__init__()
        
        # 공통 특징 추출 레이어
        self.feature = nn.Sequential(
            nn.Linear(state_size, hidden_size_1),
            nn.ReLU(),
            nn.Linear(hidden_size_1, hidden_size_2),
            nn.ReLU()
        )
        
        # Value stream (상태 가치)
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_size_2, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
        # Advantage stream (행동 이점)
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_size_2, 128),
            nn.ReLU(),
            nn.Linear(128, action_size)
        )
        
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
        features = self.feature(x)
        
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        
        # Q(s,a) = V(s) + (A(s,a) - mean(A(s,a)))
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        return q_values


def create_model(model_type="dqn", state_size=600, action_size=6, **kwargs):
    """
    모델 생성 팩토리 함수
    
    Args:
        model_type: "dqn" 또는 "dueling_dqn"
        state_size: 상태 공간 크기
        action_size: 행동 공간 크기
        **kwargs: 추가 하이퍼파라미터
    
    Returns:
        PyTorch 모델
    """
    if model_type == "dqn":
        return DQN(state_size, action_size, **kwargs)
    elif model_type == "dueling_dqn":
        return DuelingDQN(state_size, action_size, **kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
