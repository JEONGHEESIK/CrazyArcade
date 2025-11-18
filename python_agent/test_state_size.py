#!/usr/bin/env python
"""STATE_SIZE 확인 스크립트"""
import sys
import config
from game_interface import GameInterface
import numpy as np

print("="*60)
print("STATE_SIZE 확인")
print("="*60)

print(f"\n1. config.py STATE_SIZE: {config.STATE_SIZE}")

# 더미 상태 생성
dummy_state = {
    'player_index': 1,
    'my_x': 200.0, 'my_y': 200.0,
    'my_speed': 2.0, 'my_bomb_count': 1, 'my_power': 1,
    'my_state': 2, 'my_alive': True,
    'my_trapped': False, 'my_trap_timer': 0,
    
    'enemy_x': 500.0, 'enemy_y': 500.0,
    'enemy_speed': 2.0, 'enemy_bomb_count': 1, 'enemy_power': 1,
    'enemy_state': 2, 'enemy_alive': True,
    'enemy_trapped': False, 'enemy_trap_timer': 0,
    
    'map_bombs': [0] * 195,
    'map_items': [0] * 195,
    'map_waves': [0] * 195,
    
    'game_time': 0.0,
    'game_over': False,
    'winner': 0
}

# GameInterface로 변환
interface = GameInterface()
state_vector = interface._dict_to_vector(dummy_state)

print(f"2. 실제 state vector 크기: {len(state_vector)}")
print(f"3. 예상 크기: 607")
print(f"   - 플레이어 정보: 18 (9 x 2)")
print(f"   - 맵 정보: 585 (195 x 3)")
print(f"   - 게임 정보: 4")
print(f"   - 총합: 18 + 585 + 4 = 607")

if len(state_vector) == config.STATE_SIZE:
    print(f"\n✅ 정상: STATE_SIZE 일치!")
else:
    print(f"\n❌ 오류: STATE_SIZE 불일치!")
    print(f"   config: {config.STATE_SIZE}")
    print(f"   actual: {len(state_vector)}")
    print(f"   차이: {len(state_vector) - config.STATE_SIZE}")

print("\n" + "="*60)
