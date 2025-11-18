#include "stdafx.h"
#include "AIController.h"
#include "gameObjectManager.h"
#include "player.h"
#include "playScene.h"
#include <winsock2.h>
#include <ws2tcpip.h>
#include <sstream>

#pragma comment(lib, "ws2_32.lib")

// NetworkAIController 구현
NetworkAIController::NetworkAIController(const std::string& host, int port)
    : socketFd(INVALID_SOCKET), connected(false), host(host), port(port)
{
    // Winsock 초기화
    WSADATA wsaData;
    int result = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (result != 0) {
        cout << "WSAStartup failed: " << result << endl;
    }
}

NetworkAIController::~NetworkAIController()
{
    disconnect();
    WSACleanup();
}

bool NetworkAIController::connect()
{
    // 서버 소켓 생성
    SOCKET listenSocket = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listenSocket == INVALID_SOCKET) {
        cout << "Socket creation failed" << endl;
        return false;
    }

    // 주소 바인딩
    sockaddr_in serverAddr;
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(static_cast<u_short>(port));
    serverAddr.sin_addr.s_addr = INADDR_ANY;

    if (::bind(listenSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        cout << "Bind failed on port " << port << endl;
        closesocket(listenSocket);
        return false;
    }

    // 리스닝 시작
    if (listen(listenSocket, 1) == SOCKET_ERROR) {
        cout << "Listen failed" << endl;
        closesocket(listenSocket);
        return false;
    }

    cout << "Waiting for Python agent on port " << port << "..." << endl;

    // 클라이언트 접속 대기 (블로킹)
    socketFd = static_cast<SOCKET>(accept(listenSocket, nullptr, nullptr));
    closesocket(listenSocket);  // 리슨 소켓은 이제 필요 없음

    if (socketFd == INVALID_SOCKET) {
        cout << "Accept failed" << endl;
        return false;
    }

    connected = true;
    cout << "Python agent connected on port " << port << endl;
    return true;
}

void NetworkAIController::disconnect()
{
    if (socketFd != INVALID_SOCKET) {
        closesocket(socketFd);
        socketFd = INVALID_SOCKET;
    }
    connected = false;
}

AIAction NetworkAIController::getAction(const GameState& state, int playerIndex)
{
    if (!connected) {
        return AIAction::IDLE;
    }

    if (!sendGameState(state, playerIndex)) {
        return AIAction::IDLE;
    }

    return receiveAction();
}

void NetworkAIController::reset()
{
    if (!connected) return;

    // "RESET" 메시지 전송
    std::string msg = "RESET\n";
    send(socketFd, msg.c_str(), static_cast<int>(msg.length()), 0);
}

bool NetworkAIController::sendGameState(const GameState& state, int playerIndex)
{
    if (!connected) return false;

    // JSON 형식으로 상태 직렬화
    std::stringstream ss;
    ss << "{";
    ss << "\"player_index\":" << playerIndex << ",";

    // 자신의 정보
    if (playerIndex == 1) {
        ss << "\"my_x\":" << state.player1_x << ",";
        ss << "\"my_y\":" << state.player1_y << ",";
        ss << "\"my_speed\":" << state.player1_speed << ",";
        ss << "\"my_bomb_count\":" << state.player1_bomb_count << ",";
        ss << "\"my_power\":" << state.player1_power << ",";
        ss << "\"my_state\":" << state.player1_state << ",";
        ss << "\"my_alive\":" << (state.player1_alive ? "true" : "false") << ",";

        ss << "\"enemy_x\":" << state.player2_x << ",";
        ss << "\"enemy_y\":" << state.player2_y << ",";
        ss << "\"enemy_speed\":" << state.player2_speed << ",";
        ss << "\"enemy_bomb_count\":" << state.player2_bomb_count << ",";
        ss << "\"enemy_power\":" << state.player2_power << ",";
        ss << "\"enemy_state\":" << state.player2_state << ",";
        ss << "\"enemy_alive\":" << (state.player2_alive ? "true" : "false") << ",";
    }
    else {
        ss << "\"my_x\":" << state.player2_x << ",";
        ss << "\"my_y\":" << state.player2_y << ",";
        ss << "\"my_speed\":" << state.player2_speed << ",";
        ss << "\"my_bomb_count\":" << state.player2_bomb_count << ",";
        ss << "\"my_power\":" << state.player2_power << ",";
        ss << "\"my_state\":" << state.player2_state << ",";
        ss << "\"my_alive\":" << (state.player2_alive ? "true" : "false") << ",";

        ss << "\"enemy_x\":" << state.player1_x << ",";
        ss << "\"enemy_y\":" << state.player1_y << ",";
        ss << "\"enemy_speed\":" << state.player1_speed << ",";
        ss << "\"enemy_bomb_count\":" << state.player1_bomb_count << ",";
        ss << "\"enemy_power\":" << state.player1_power << ",";
        ss << "\"enemy_state\":" << state.player1_state << ",";
        ss << "\"enemy_alive\":" << (state.player1_alive ? "true" : "false") << ",";
    }

    // 맵 정보 (간단하게 1차원 배열로 변환)
    ss << "\"map_bombs\":[";
    for (int i = 0; i < 13; i++) {
        for (int j = 0; j < 15; j++) {
            ss << state.map_bombs[i][j];
            if (i < 12 || j < 14) ss << ",";
        }
    }
    ss << "],";

    ss << "\"map_items\":[";
    for (int i = 0; i < 13; i++) {
        for (int j = 0; j < 15; j++) {
            ss << state.map_items[i][j];
            if (i < 12 || j < 14) ss << ",";
        }
    }
    ss << "],";

    ss << "\"map_waves\":[";
    for (int i = 0; i < 13; i++) {
        for (int j = 0; j < 15; j++) {
            ss << state.map_waves[i][j];
            if (i < 12 || j < 14) ss << ",";
        }
    }
    ss << "],";

    ss << "\"game_time\":" << state.game_time << ",";
    ss << "\"game_over\":" << (state.game_over ? "true" : "false") << ",";
    ss << "\"winner\":" << state.winner;
    ss << "}\n";

    std::string json = ss.str();
    int result = send(socketFd, json.c_str(), static_cast<int>(json.length()), 0);

    return result != SOCKET_ERROR;
}

AIAction NetworkAIController::receiveAction()
{
    char buffer[1024] = { 0 };
    int bytesReceived = recv(socketFd, buffer, sizeof(buffer) - 1, 0);

    if (bytesReceived <= 0) {
        return AIAction::IDLE;
    }

    // 간단한 파싱 (숫자만 받음)
    int action = atoi(buffer);

    if (action >= 0 && action <= 5) {
        return static_cast<AIAction>(action);
    }

    return AIAction::IDLE;
}

bool NetworkAIController::sendReward(const RewardInfo& reward)
{
    if (!connected) return false;

    std::stringstream ss;
    ss << "{";
    ss << "\"reward\":" << reward.reward << ",";
    ss << "\"done\":" << (reward.done ? "true" : "false") << ",";
    ss << "\"info\":\"" << reward.info << "\"";
    ss << "}\n";

    std::string json = ss.str();
    int result = send(socketFd, json.c_str(), static_cast<int>(json.length()), 0);

    return result != SOCKET_ERROR;
}

// GameStateExtractor 구현
GameState GameStateExtractor::extractState()
{
    GameState state;
    memset(&state, 0, sizeof(GameState));

    // 게임 오브젝트 매니저에서 플레이어 찾기
    vector<GameObject*> gameObjects = GAMEOBJMANGER->getGameObject();

    Player* player1 = nullptr;
    Player* player2 = nullptr;

    for (auto obj : gameObjects) {
        if (obj->getTag() == GameObjectTag::Player) {
            Player* player = dynamic_cast<Player*>(obj);
            if (player) {
                if (player->getPlayerType() == PlayerTypeTag::Player1) {
                    player1 = player;
                }
                else if (player->getPlayerType() == PlayerTypeTag::Player2) {
                    player2 = player;
                }
            }
        }
    }

    // Player 1 정보
    if (player1) {
        state.player1_x = player1->getStartX();
        state.player1_y = player1->getStartY();
        state.player1_speed = player1->getSpeed();
        state.player1_bomb_count = player1->getUsableBombs();
        state.player1_power = player1->getPower();
        state.player1_state = static_cast<int>(player1->getPlayerState());
        state.player1_alive = player1->getLive();
        // 추가 정보는 Player 클래스에 getter 필요
    }

    // Player 2 정보
    if (player2) {
        state.player2_x = player2->getStartX();
        state.player2_y = player2->getStartY();
        state.player2_speed = player2->getSpeed();
        state.player2_bomb_count = player2->getUsableBombs();
        state.player2_power = player2->getPower();
        state.player2_state = static_cast<int>(player2->getPlayerState());
        state.player2_alive = player2->getLive();
    }

    // 맵 정보 추출
    for (int i = 0; i < 13; i++) {
        for (int j = 0; j < 15; j++) {
            state.map_bombs[i][j] = PlayScene::mapArr[i][j].isBomb ? 1 : 0;
            state.map_items[i][j] = PlayScene::getIsItem(i, j) ? 1 : 0;
        }
    }

    state.game_time = TIMEMANAGER->getWorldTime();
    state.game_over = GAMESTATEMANAGER->getGameOver();

    return state;
}

RewardInfo GameStateExtractor::calculateReward(const GameState& prevState, const GameState& currentState, int playerIndex)
{
    RewardInfo reward;
    reward.reward = 0.0f;
    reward.done = currentState.game_over;
    reward.info = "";

    bool myAlive = (playerIndex == 1) ? currentState.player1_alive : currentState.player2_alive;
    bool myPrevAlive = (playerIndex == 1) ? prevState.player1_alive : prevState.player2_alive;
    bool enemyAlive = (playerIndex == 1) ? currentState.player2_alive : currentState.player1_alive;
    bool enemyPrevAlive = (playerIndex == 1) ? prevState.player2_alive : prevState.player1_alive;

    // 사망 체크
    if (myPrevAlive && !myAlive) {
        reward.reward -= 1000.0f;
        reward.info = "died";
        reward.done = true;
        return reward;
    }

    // 상대 처치
    if (enemyPrevAlive && !enemyAlive) {
        reward.reward += 1000.0f;
        reward.info = "killed_enemy";
        reward.done = true;
        return reward;
    }

    // 시간 패널티
    reward.reward -= 0.1f;

    return reward;
}
