실험 설계
알고리즘 비교
DQN (Deep Q-Network)
Off-policy 알고리즘
매 스텝마다 Replay Buffer에서 샘플링하여 학습
데이터 효율성 높음 (과거 경험 재사용)
PPO (Proximal Policy Optimization)
On-policy 알고리즘
에피소드 종료 후 수집된 데이터로 학습
데이터 효율성 낮음 (현재 정책 데이터만 사용)
하지만 학습 안정성 높음
예상 결과
초반 학습 속도: DQN > PPO (데이터 재사용 효과)
학습 안정성: PPO > DQN (정책 업데이트 제한)
최종 성능: 환경에 따라 다름
하이퍼파라미터 공정성
Learning rate: DQN=0.0001, PPO=0.001 (알고리즘 특성 반영)
탐험: DQN은 ε-greedy, PPO는 entropy bonus