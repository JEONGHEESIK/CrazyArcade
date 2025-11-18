#!/bin/bash
# DQN vs PPO 실행 스크립트

echo "============================================================"
echo "DQN vs PPO 대결 시작"
echo "============================================================"
echo ""

# 기존 프로세스 종료
echo "1️⃣  기존 프로세스 정리 중..."
pkill -f mock_game_server 2>/dev/null
pkill -f train 2>/dev/null
sleep 1

# Dual Mock 서버 시작
echo ""
echo "2️⃣  Dual Mock 서버 시작 중..."
python mock_game_server_dual.py --port1 12345 --port2 12346 &
SERVER_PID=$!
echo "   서버 PID: $SERVER_PID"
sleep 3

# Player 1 (DQN) 시작
echo ""
echo "3️⃣  Player 1 (DQN) 시작 중..."
python train_single_agent.py --agent dqn --port 12345 --episodes 5000 --name Player1_DQN &
DQN_PID=$!
echo "   DQN PID: $DQN_PID"
sleep 2

# Player 2 (PPO) 시작
echo ""
echo "4️⃣  Player 2 (PPO) 시작 중..."
python train_single_agent.py --agent ppo --port 12346 --episodes 5000 --name Player2_PPO &
PPO_PID=$!
echo "   PPO PID: $PPO_PID"

echo ""
echo "============================================================"
echo "🎮 게임 시작!"
echo "============================================================"
echo ""
echo "프로세스 ID:"
echo "  - 서버: $SERVER_PID"
echo "  - DQN:  $DQN_PID"
echo "  - PPO:  $PPO_PID"
echo ""
echo "로그 확인:"
echo "  - tail -f logs/Player1_DQN_*/training.log"
echo "  - tail -f logs/Player2_PPO_*/training.log"
echo ""
echo "중단: Ctrl+C 또는 ./stop_dqn_vs_ppo.sh"
echo "============================================================"
echo ""

# 사용자 입력 대기
trap "echo ''; echo '중단 요청...'; kill $SERVER_PID $DQN_PID $PPO_PID 2>/dev/null; exit" INT

# 프로세스 모니터링
wait $SERVER_PID $DQN_PID $PPO_PID
