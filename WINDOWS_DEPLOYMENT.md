# Windows에서 학습된 모델 실행하기

## 🎯 전체 흐름

```
Linux (H100) → 학습 → 모델 저장
     ↓
모델 파일 복사
     ↓
Windows → 모델 로드 → C++ 게임 실행
```

---

## 📦 필요한 파일

### 1. 학습된 모델 파일
```
Linux에서 생성:
/home/jeonghs/workspace/hidden/CrazyArcade/python_agent/models/
├── Player1_DQN_YYYYMMDD_HHMMSS/
│   ├── model_episode_100.pth
│   ├── model_episode_200.pth
│   └── model_episode_final.pth
└── Player2_PPO_YYYYMMDD_HHMMSS/
    ├── model_episode_100.pth
    └── model_episode_final.pth
```

### 2. Python 에이전트 코드
```
필요한 파일:
- dqn_agent.py
- ppo_agent.py
- config.py
- game_interface.py
- play_agent.py (실행용)
```

---

## 🚀 방법 1: 모델 파일만 복사 (추천)

### Step 1: Linux에서 모델 저장 확인
```bash
# 최신 모델 확인
cd /home/jeonghs/workspace/hidden/CrazyArcade/python_agent
ls -lh models/Player1_DQN_*/model_episode_final.pth
ls -lh models/Player2_PPO_*/model_episode_final.pth
```

### Step 2: 모델 파일 다운로드
```bash
# SCP로 Windows로 복사
# Windows에서 실행:
scp jeonghs@18ed97d5a6f0:/home/jeonghs/workspace/hidden/CrazyArcade/python_agent/models/Player1_DQN_*/model_episode_final.pth ./models/dqn_model.pth
scp jeonghs@18ed97d5a6f0:/home/jeonghs/workspace/hidden/CrazyArcade/python_agent/models/Player2_PPO_*/model_episode_final.pth ./models/ppo_model.pth
```

또는 **WinSCP, FileZilla** 등 GUI 도구 사용

### Step 3: Windows에서 Python 환경 설정
```bash
# Anaconda 설치 (이미 있으면 스킵)
# https://www.anaconda.com/download

# 가상환경 생성
conda create -n crazyarcade python=3.11
conda activate crazyarcade

# PyTorch 설치 (CPU 버전)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 기타 패키지
pip install numpy
```

### Step 4: Windows에서 실행
```python
# play_agent.py (Windows용)
import torch
from dqn_agent import DQNAgent
from game_interface import GameInterface
import config

# CPU 강제 사용
device = torch.device('cpu')

# 모델 로드
agent = DQNAgent(device=device)
agent.load('./models/dqn_model.pth')
agent.set_eval_mode()

# 게임 서버 연결 (C++ 게임)
env = GameInterface(host='127.0.0.1', port=12345)
env.connect()

# 게임 플레이
state = env.reset()
while True:
    action = agent.select_action(state, training=False)
    state, reward, done, info = env.step(action)
    if done:
        break
```

---

## 🚀 방법 2: ONNX 변환 (더 빠름)

### Step 1: Linux에서 ONNX로 변환
```python
# convert_to_onnx.py
import torch
import torch.onnx
from dqn_agent import DQNAgent
import config

# 모델 로드
agent = DQNAgent()
agent.load('./models/Player1_DQN_*/model_episode_final.pth')
agent.set_eval_mode()

# 더미 입력
dummy_input = torch.randn(1, config.STATE_SIZE)

# ONNX 변환
torch.onnx.export(
    agent.policy_net,
    dummy_input,
    "dqn_model.onnx",
    export_params=True,
    opset_version=11,
    input_names=['state'],
    output_names=['q_values']
)
```

### Step 2: Windows에서 ONNX 실행
```python
# play_agent_onnx.py
import onnxruntime as ort
import numpy as np

# ONNX 모델 로드
session = ort.InferenceSession("dqn_model.onnx")

# 추론
def select_action(state):
    state = np.array(state, dtype=np.float32).reshape(1, -1)
    q_values = session.run(None, {'state': state})[0]
    return np.argmax(q_values)
```

---

## 🎮 방법 3: C++ 게임과 통합

### C++ 게임 서버 실행
```cpp
// Windows에서 C++ 게임 실행
// Visual Studio에서 빌드 후:
CrazyArcade.exe --ai-mode --port 12345
```

### Python 에이전트 연결
```python
# Windows에서
python play_agent.py --model ./models/dqn_model.pth --port 12345
```

---

## 💡 CPU vs GPU 성능

### 추론 속도
```
H100 (GPU):  ~0.1ms/step
CPU (Intel): ~1-5ms/step
```

**게임 플레이에는 CPU로도 충분합니다!** (60 FPS 가능)

---

## 📁 파일 구조 (Windows)

```
CrazyArcade/
├── CrazyArcade.exe          # C++ 게임
├── python_agent/
│   ├── models/
│   │   ├── dqn_model.pth    # 학습된 모델
│   │   └── ppo_model.pth
│   ├── dqn_agent.py
│   ├── ppo_agent.py
│   ├── config.py
│   ├── game_interface.py
│   └── play_agent.py        # 실행 스크립트
└── README.md
```

---

## 🔧 config.py 수정 (Windows용)

```python
# config.py
import torch

# Windows에서는 CPU 사용
DEVICE = 'cpu'  # 'cuda' → 'cpu'

# 나머지는 동일
STATE_SIZE = 607
ACTION_SIZE = 6
```

---

## 🚀 실행 스크립트 (Windows)

### play_dqn.bat
```batch
@echo off
echo DQN Agent Playing...
conda activate crazyarcade
python play_agent.py --agent dqn --model models/dqn_model.pth --port 12345
pause
```

### play_ppo.bat
```batch
@echo off
echo PPO Agent Playing...
conda activate crazyarcade
python play_agent.py --agent ppo --model models/ppo_model.pth --port 12345
pause
```

---

## 📊 성능 최적화 (Windows)

### 1. TorchScript 사용
```python
# Linux에서 변환
scripted_model = torch.jit.script(agent.policy_net)
scripted_model.save("dqn_model_scripted.pt")

# Windows에서 로드
model = torch.jit.load("dqn_model_scripted.pt")
model.eval()
```

### 2. 양자화 (Quantization)
```python
# 모델 크기 감소 + 속도 증가
quantized_model = torch.quantization.quantize_dynamic(
    agent.policy_net,
    {torch.nn.Linear},
    dtype=torch.qint8
)
```

---

## 🎯 전체 워크플로우

### 1. Linux (학습)
```bash
# 학습 실행
./run_dqn_vs_ppo.sh

# 학습 완료 후 모델 확인
ls models/Player1_DQN_*/model_episode_final.pth
```

### 2. 파일 전송
```bash
# WinSCP, FileZilla 등으로
# .pth 파일을 Windows로 복사
```

### 3. Windows (실행)
```batch
# Python 환경 설정
conda activate crazyarcade

# C++ 게임 실행
CrazyArcade.exe --ai-mode

# Python 에이전트 실행
python play_agent.py --model models/dqn_model.pth
```

---

## 🐛 문제 해결

### 문제 1: PyTorch 버전 불일치
```bash
# Linux 버전 확인
python -c "import torch; print(torch.__version__)"

# Windows에서 같은 버전 설치
pip install torch==2.1.0
```

### 문제 2: CUDA 오류 (Windows)
```python
# config.py 또는 play_agent.py
import torch
device = torch.device('cpu')  # 강제로 CPU 사용
```

### 문제 3: 모델 로드 실패
```python
# map_location 사용
model.load_state_dict(
    torch.load('model.pth', map_location='cpu')
)
```

---

## 🎯 결론

### 추천 방법
```
1. Linux에서 학습 (H100)
2. .pth 파일만 Windows로 복사
3. Windows에서 CPU로 실행
```

### 장점
```
✅ 학습은 빠른 GPU 사용
✅ 실행은 CPU로 충분
✅ 파일 전송만 하면 됨
✅ 실시간 게임 플레이 가능
```

**Windows CPU로도 게임 플레이는 문제없습니다!** 🎮
