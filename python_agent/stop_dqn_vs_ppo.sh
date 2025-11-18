#!/bin/bash
# DQN vs PPO 중단 스크립트

echo "DQN vs PPO 중단 중..."

pkill -f mock_game_server_dual
pkill -f train_single_agent

echo "모든 프로세스 종료됨"
