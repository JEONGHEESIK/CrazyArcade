"""
경험 재생 버퍼 (Experience Replay Buffer)
"""
import random
import numpy as np
from collections import deque, namedtuple


# 경험 튜플 정의
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])


class ReplayBuffer:
    """경험 재생 버퍼"""
    
    def __init__(self, capacity=100000):
        """
        Args:
            capacity: 버퍼 최대 크기
        """
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        """경험 저장"""
        self.buffer.append(Experience(state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        """무작위 샘플링"""
        experiences = random.sample(self.buffer, batch_size)
        
        states = np.array([e.state for e in experiences], dtype=np.float32)
        actions = np.array([e.action for e in experiences], dtype=np.int64)
        rewards = np.array([e.reward for e in experiences], dtype=np.float32)
        next_states = np.array([e.next_state for e in experiences], dtype=np.float32)
        dones = np.array([e.done for e in experiences], dtype=np.float32)
        
        return states, actions, rewards, next_states, dones
    
    def __len__(self):
        """버퍼 크기 반환"""
        return len(self.buffer)


class PrioritizedReplayBuffer:
    """우선순위 경험 재생 버퍼 (Prioritized Experience Replay)"""
    
    def __init__(self, capacity=100000, alpha=0.6):
        """
        Args:
            capacity: 버퍼 최대 크기
            alpha: 우선순위 지수 (0: uniform, 1: full prioritization)
        """
        self.capacity = capacity
        self.alpha = alpha
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.size = 0
    
    def push(self, state, action, reward, next_state, done):
        """경험 저장 (최대 우선순위로 초기화)"""
        max_priority = self.priorities.max() if self.size > 0 else 1.0
        
        if self.size < self.capacity:
            self.buffer.append(Experience(state, action, reward, next_state, done))
        else:
            self.buffer[self.position] = Experience(state, action, reward, next_state, done)
        
        self.priorities[self.position] = max_priority
        self.position = (self.position + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def sample(self, batch_size, beta=0.4):
        """
        우선순위 기반 샘플링
        
        Args:
            batch_size: 배치 크기
            beta: 중요도 샘플링 보정 지수 (0: no correction, 1: full correction)
        
        Returns:
            states, actions, rewards, next_states, dones, indices, weights
        """
        if self.size < batch_size:
            batch_size = self.size
        
        # 우선순위 기반 확률 계산
        priorities = self.priorities[:self.size]
        probabilities = priorities ** self.alpha
        probabilities /= probabilities.sum()
        
        # 샘플링
        indices = np.random.choice(self.size, batch_size, p=probabilities, replace=False)
        
        # 중요도 샘플링 가중치 계산
        weights = (self.size * probabilities[indices]) ** (-beta)
        weights /= weights.max()  # 정규화
        
        # 경험 추출
        experiences = [self.buffer[idx] for idx in indices]
        
        states = np.array([e.state for e in experiences], dtype=np.float32)
        actions = np.array([e.action for e in experiences], dtype=np.int64)
        rewards = np.array([e.reward for e in experiences], dtype=np.float32)
        next_states = np.array([e.next_state for e in experiences], dtype=np.float32)
        dones = np.array([e.done for e in experiences], dtype=np.float32)
        
        return states, actions, rewards, next_states, dones, indices, weights
    
    def update_priorities(self, indices, priorities):
        """우선순위 업데이트"""
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority
    
    def __len__(self):
        """버퍼 크기 반환"""
        return self.size
