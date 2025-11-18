#pragma once
#include <string>
#include <vector>
#include <winsock2.h>  // 이 줄 추가

// AI가 수행할 수 있는 행동
enum class AIAction
{
    IDLE = 0,
    UP = 1,
    DOWN = 2,
    LEFT = 3,
    RIGHT = 4,
    PLACE_BOMB = 5
};

// 게임 상태 구조체
struct GameState
{
    // 플레이어 1 정보
    float player1_x;
    float player1_y;
    float player1_speed;
    int player1_bomb_count;
    int player1_power;
    int player1_state;  // PlayerStateTag를 int로 변환
    bool player1_alive;

    // 플레이어 2 정보
    float player2_x;
    float player2_y;
    float player2_speed;
    int player2_bomb_count;
    int player2_power;
    int player2_state;
    bool player2_alive;

    // 맵 정보 (13x15)
    int map_bombs[13][15];      // 0: 없음, 1: 물풍선 있음
    int map_items[13][15];      // 0: 없음, 1-4: 아이템 종류
    int map_waves[13][15];      // 0: 없음, 1: 물줄기 있음
    int map_blocks[13][15];     // 0: 이동가능, 1: 블록

    // 게임 정보
    float game_time;
    bool game_over;
    int winner;  // 0: 진행중, 1: player1 승리, 2: player2 승리
};

// 보상 정보
struct RewardInfo
{
    float reward;
    bool done;
    std::string info;
};

// AI 컨트롤러 인터페이스
class AIController
{
public:
    virtual ~AIController() {}
    virtual AIAction getAction(const GameState& state, int playerIndex) = 0;
    virtual void reset() = 0;
};

// 네트워크 AI 컨트롤러 (Python과 통신)
class NetworkAIController : public AIController
{
private:
    SOCKET socketFd;  // int가 아닌 SOCKET 타입
    bool connected;
    std::string host;
    int port;

public:
    NetworkAIController(const std::string& host = "127.0.0.1", int port = 12345);
    ~NetworkAIController();

    bool connect();
    void disconnect();
    
    virtual AIAction getAction(const GameState& state, int playerIndex) override;
    virtual void reset() override;

    bool sendGameState(const GameState& state, int playerIndex);
    AIAction receiveAction();
    bool sendReward(const RewardInfo& reward);
};

// 게임 상태 추출 헬퍼
class GameStateExtractor
{
public:
    static GameState extractState();
    static RewardInfo calculateReward(const GameState& prevState, const GameState& currentState, int playerIndex);
};
