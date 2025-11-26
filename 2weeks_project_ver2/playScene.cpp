#include "stdafx.h"
#include "playScene.h"
#include "itemFactory.h"
#include "player.h"
#include "designElement.h"
#include "bomb.h"
#include "item.h"
#include "AIController.h"

extern POINT ptMouse;

//물풍선관련 맵정보 정의 (처음엔 물풍선이 있는지 여부와, 놓은 바로직후여부 두개다 false)
CanIGo PlayScene::mapArr[BOARD_ROW][BOARD_COL] = { CanIGo() };
//아이템관련 맵정보 정의(처음엔 아이템이 있는지 여부와, 아이템의 종류가 각각 false, Not)
bool PlayScene::isItemArr[BOARD_ROW][BOARD_COL] = { false };
// AI Controller 전역 변수 정의
NetworkAIController* PlayScene::_globalController1 = nullptr;
NetworkAIController* PlayScene::_globalController2 = nullptr;

PlayScene::PlayScene()
	: _vvTile(BOARD_ROW, vector<Tile>(BOARD_COL, Tile()))
	, _mapType(MapTypeTag::Not)
	, _startTime(static_cast<int>(TIMEMANAGER->getWorldTime()))
	, _gameWords(nullptr)
	, _startWords(nullptr)
	, _blackBg(nullptr)
	, _gameGrayWords(nullptr)
	, _overWords(nullptr)
	, _setTime(false)
	, _setGameStateInit(false)
	, _check(false)
	, _autoRestart(true)
	, _gameOverStartTime(0)
{
	_stopGameRect = makeRect(842, 730, 181, 40);
}

PlayScene::~PlayScene()
{
}

void PlayScene::init()
{
	float randomNum1 = static_cast<float>(RANDOM->getIntFromTo(100, 300));
	float randomNum2 = static_cast<float>(RANDOM->getIntFromTo(400, 600));
	//캐릭터 생성
	//TODO: 지정해놓은 위치에, 랜덤하게 생성되오야 한다!!
	//2인 모드로 하면 2명의 player가 생성되어야한다
	if (_mode == ModeTypeTag::TwoPlayer) //2인 모드
	{
		Player* player1 = new Player(PlayerTypeTag::Player1, randomNum1, randomNum1);
		Player* player2 = new Player(PlayerTypeTag::Player2, randomNum2, randomNum2);


		// AI Controller 연결 (재시작 시에도 기존 연결 유지)
		if (_globalController1 == nullptr)
		{
			cout << "[DEBUG] Creating Player1 AI Controller..." << endl;
			cout.flush();
			_globalController1 = new NetworkAIController("127.0.0.1", 12345);
			cout << "[DEBUG] Connecting Player1..." << endl;
			cout.flush();
			if (!_globalController1->connect())
			{
				delete _globalController1;
				_globalController1 = nullptr;
				cout << "Player1 AI Controller connection failed" << endl;
				cout.flush();
			}
			else
			{
				cout << "Player1 AI Controller connected" << endl;
				cout.flush();
			}
		}

		if (_globalController2 == nullptr)
		{
			cout << "[DEBUG] Creating Player2 AI Controller..." << endl;
			cout.flush();
			_globalController2 = new NetworkAIController("127.0.0.1", 12346);
			cout << "[DEBUG] Connecting Player2..." << endl;
			cout.flush();
			if (!_globalController2->connect())
			{
				delete _globalController2;
				_globalController2 = nullptr;
				cout << "Player2 AI Controller connection failed" << endl;
				cout.flush();
			}
			else
			{
				cout << "Player2 AI Controller connected" << endl;
				cout.flush();
			}
		}

		// 기존 연결을 새 플레이어에 할당
		if (_globalController1)
		{
			player1->setAIController(_globalController1);
			cout << "[DEBUG] Player1 AI Controller attached" << endl;
		}
		if (_globalController2)
		{
			player2->setAIController(_globalController2);
			cout << "[DEBUG] Player2 AI Controller attached" << endl;
		}

		cout << "[DEBUG] AI Controllers setup complete" << endl;
		cout.flush();

		GAMEOBJMANGER->registerObj(player1);
		GAMEOBJMANGER->registerObj(player2);

	}
	else if (_mode == ModeTypeTag::Monster) //몬스터 모드
	{
		Player* player = new Player(PlayerTypeTag::SoloPlayer, 300.f, 300.f);
		GAMEOBJMANGER->registerObj(player);
	}

	//아이템 생성 -> ItemFactory에 위임
	ItemFactory::createItemAtRandomPosition();

	//레디시 그려질 애니메이션 요소들을 게임매니저를 통해 등록한다(최상단에 그려주기 위함)
	_gameWords = new DesignElement(IMAGEMANAGER->findImage("GAME"));
	GAMEOBJMANGER->registerObj(_gameWords);
	_startWords = new DesignElement(IMAGEMANAGER->findImage("START"));
	GAMEOBJMANGER->registerObj(_startWords);
	_blackBg = new DesignElement(IMAGEMANAGER->findImage("blackBg"), true);
	GAMEOBJMANGER->registerObj(_blackBg);


	_gameWords->getImage()->setX(292);   _gameWords->getImage()->setY(253);
	_startWords->getImage()->setX(175); _startWords->getImage()->setY(338);

}

void PlayScene::release()
{
	// DesignElement들은 GameObjectManager에 등록되어 있으므로
	// 여기서 직접 삭제하지 않음 (GameObjectManager가 정리함)
	// SAFE_DELETE는 포인터만 nullptr로 설정
	_gameWords = nullptr;
	_startWords = nullptr;
	_blackBg = nullptr;
	_gameGrayWords = nullptr;
	_overWords = nullptr;
}

void PlayScene::update()
{
	if (!GAMESTATEMANAGER->getGameOver())
	{
		if (_startTime + 2 < static_cast<int>(TIMEMANAGER->getWorldTime()))
			SOUNDMANAGER->repeatPlay(static_cast<int>(SoundTypeTag::PlayScene), SoundTypeTag::PlayScene);
	}
	//cout << static_cast<int>(_blackBg->getAlpha()) << endl;
	if (!GAMESTATEMANAGER->getGameStart())
	{
		if (_blackBg->getAlpha() > 20)
			_blackBg->setAlpha(_blackBg->getAlpha() - 10);

		//게임시작전에 게임스타트 문구 보이기
		int currentTime = static_cast<int>(TIMEMANAGER->getWorldTime());
		int diff = currentTime - _startTime;
		if (diff > 5)
		{
			_gameWords->getImage()->setY(_gameWords->getImage()->getY() - 20.f);
			_startWords->getImage()->setY(_startWords->getImage()->getY() + 20.f);
		}
		if (diff > 6)
		{
			_blackBg->setAlpha(0);
			GAMESTATEMANAGER->setGameStart(true);
			//사용자 입력을 받을 수 있음을 화면이 밝아지는 걸로 안내
		}
	}
	else
	{
		if (!_check)
		{
			_check = true;
			// 게임 재시작을 위한 플래그 리셋
			_setTime = false;
			_setGameStateInit = false;

			//게임이 시작하면 디자인구성요소들을 게임오브젝트 매니저에서 삭제한다
			GAMEOBJMANGER->removeObj(_gameWords->getId());
			GAMEOBJMANGER->removeObj(_startWords->getId());
			GAMEOBJMANGER->removeObj(_blackBg->getId());
		}
	}

	//게임 오버 상태이면
	if (GAMESTATEMANAGER->getGameOver())
	{
		//Game Over문구 보여주기
		if (!_setTime)
		{
			SOUNDMANAGER->stop(static_cast<int>(SoundTypeTag::PlayScene));
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::Lose), SoundTypeTag::Lose);
			_setTime = true;
			_startTime = static_cast<int>(TIMEMANAGER->getWorldTime());

			//게임오버시 그려질 애니메이션 요소들을 게임 매니저를 통해 등록한다
			_gameGrayWords = new DesignElement(IMAGEMANAGER->findImage("GAME_GRAY"));
			GAMEOBJMANGER->registerObj(_gameGrayWords);
			_overWords = new DesignElement(IMAGEMANAGER->findImage("OVER"));
			GAMEOBJMANGER->registerObj(_overWords);

			_gameGrayWords->getImage()->setX(242);  _gameGrayWords->getImage()->setY(-240);
			_overWords->getImage()->setX(193);      _overWords->getImage()->setY(WINSIZEY);
		}

		int currentTime = static_cast<int>(TIMEMANAGER->getWorldTime());
		int diff = currentTime - _startTime;
		if (diff <= 6)
		{
			if (_gameGrayWords->getImage()->getY() <= 240)
				_gameGrayWords->getImage()->setY(_gameGrayWords->getImage()->getY() + 10.f);
			if (_overWords->getImage()->getY() >= 349)
				_overWords->getImage()->setY(_overWords->getImage()->getY() - 10.f);
		}
		// AI 학습용: 게임 시간 제한 (60초) - 아무도 안 죽으면 강제 종료
		if (diff > 60 && _autoRestart && !_setGameStateInit && !GAMESTATEMANAGER->getGameOver())
		{
			cout << "[AUTO] Game timeout (60s) - forcing game over" << endl;
			GAMESTATEMANAGER->setGameOver(true);
			_startTime = currentTime;  // 타이머 리셋
		}

		// AI 학습용 자동 재시작 (3초 후 바로 게임 재시작)
		if (diff > 3 && _autoRestart && !_setGameStateInit && GAMESTATEMANAGER->getGameOver())
		{
			_setGameStateInit = true;

			// AI Controller에게 에피소드 종료 알림 (game_over=true 상태 전송)
			if (_globalController1) {
				GameState finalState = GameStateExtractor::extractState();
				// game_over=true인 상태를 전송
				_globalController1->sendGameState(finalState, 1);
			}
			if (_globalController2) {
				GameState finalState = GameStateExtractor::extractState();
				// game_over=true인 상태를 전송
				_globalController2->sendGameState(finalState, 2);
			}

			cout << "[AUTO] Restarting game..." << endl;

			// GAME STATE 재설정
			GAMESTATEMANAGER->setGameStart(false);
			GAMESTATEMANAGER->setGameOver(false);

			// 게임 오브젝트 제거
			GAMEOBJMANGER->removeObjAll();

			// 맵 초기화
			for (int i = 0; i < BOARD_ROW; i++) {
				for (int j = 0; j < BOARD_COL; j++) {
					mapArr[i][j].isBomb = false;
					mapArr[i][j].rightAfter = false;
					isItemArr[i][j] = false;
				}
			}

			// 타일 재로드
			loadTile();

			// 게임 재시작 (모드와 맵 타입 유지)
			_startTime = static_cast<int>(TIMEMANAGER->getWorldTime());
			_check = false;
			_setTime = false;
			_setGameStateInit = false;

			// 디자인 요소 초기화
			_gameWords = nullptr;
			_startWords = nullptr;
			_blackBg = nullptr;
			_gameGrayWords = nullptr;
			_overWords = nullptr;

			// 게임 재시작
			init();

			cout << "[AUTO] Game restarted!" << endl;
		}
		// 수동 모드: 6초 후 로비로
		else if (diff > 6 && !_autoRestart)
		{
			if (!_setGameStateInit)
			{
				GAMESTATEMANAGER->setGameStart(false);
				GAMESTATEMANAGER->setGameOver(false);
				_setGameStateInit = true;
			}
			GAMEOBJMANGER->removeObjAll();
			SCENEMANAGER->changeScene(SceneTag::Lobby);
		}
	}

	//나가기 버튼을 누르면
	if (KEYMANAGER->isOnceKeyDown(VK_LBUTTON))
	{
		if (PtInRect(&_stopGameRect, ptMouse))
		{
			SOUNDMANAGER->stop(static_cast<int>(SoundTypeTag::PlayScene));
			//GAME STATE 재설정
			GAMESTATEMANAGER->setGameStart(false);
			GAMESTATEMANAGER->setGameOver(false);

			GAMEOBJMANGER->removeObjAll(); //게임오브젝트들 다 날리기
			SCENEMANAGER->changeScene(SceneTag::ModeSelect); //씬 바꾸기
		}
	}

}

void PlayScene::render(HDC hdc)
{
	//배경
	IMAGEMANAGER->findImage("playBg")->render(hdc);

	//타일
	for (int i = 0; i < BOARD_ROW; ++i)
	{
		for (int j = 0; j < BOARD_COL; ++j)
		{
			IMAGEMANAGER->findImage(_vvTile[i][j].getStrKey())->render(hdc, BOARD_STARTX + (BOARD_RECTSIZE * j), BOARD_STARTY + (BOARD_RECTSIZE * i));
			/* 격자 출력하는 거 요기따!!!! */
			//drawRect(hdc, BOARD_STARTX + (BOARD_RECTSIZE * j), BOARD_STARTY + (BOARD_RECTSIZE * i), BOARD_RECTSIZE, BOARD_RECTSIZE);
		}
	}

	//화면 정보
	//Text(15, 10, WINSIZEY - 22, "Play Scene")(hdc);
	//if (_mode == ModeTypeTag::TwoPlayer)
	//{
	//    Text(15, 100, WINSIZEY - 22, "(2인 모드)")(hdc);
	//}
	//else if (_mode == ModeTypeTag::Monster)
	//{
	//    Text(15, 100, WINSIZEY - 22, "(몬스터 모드)")(hdc);
	//}

	//맵 정보
	if (_mapType == MapTypeTag::Forest)
	{
		Text(18, 62, 10, "포레스트", WHITE)(hdc);
	}

	//디버그용
	//debug(hdc);
}

void PlayScene::handleArgs(vector<int> args)
{
	assert(args.size() == 2); //반드시 지켜져야할 사항, 선예외처리 #include <cassert>, 디버그용 x -> 안정성용
	_mapType = static_cast<MapTypeTag>(args.at(1));
	_mode = static_cast<ModeTypeTag>(args.at(0));
	loadTile();
}

void PlayScene::loadTile()
{
	_vvTile = TileFactory::makeMapTile(_mapType);
}

void PlayScene::changeMapArr(int row, int col, bool isBomb, bool rightAfter)
{
	mapArr[row][col].isBomb = isBomb;
	mapArr[row][col].rightAfter = rightAfter;
}

void PlayScene::setIsItem(int row, int col, bool isItem)
{
	isItemArr[row][col] = isItem;
}

bool PlayScene::getIsItem(int row, int col)
{
	return isItemArr[row][col];
}

void PlayScene::debug(HDC hdc)
{
	//디버깅용 맵 위에 갈 수 있는지 없는 지 여부 나타내기
	//for (int i = 0; i < BOARD_ROW; ++i)
	//{
	//    for (int j = 0; j < BOARD_COL; ++j)
	//    {
	//        Text(10, BOARD_STARTX + j * BOARD_RECTSIZE, BOARD_STARTY + i * BOARD_RECTSIZE, to_string(PlayScene::mapArr[i][j].isBomb))(hdc);
	//        Text(10, BOARD_STARTX + j * BOARD_RECTSIZE, BOARD_STARTY + 10 + i * BOARD_RECTSIZE, to_string(PlayScene::mapArr[i][j].rightAfter))(hdc);
	//        //TextOut(hdc, BOARD_STARTX + j * BOARD_RECTSIZE, BOARD_STARTY + i * BOARD_RECTSIZE, to_string(PlayScene::mapArr[i][j].isBomb).c_str(), to_string(PlayScene::mapArr[i][j].isBomb).size());
	//        //TextOut(hdc, BOARD_STARTX + j * BOARD_RECTSIZE, BOARD_STARTY + 10 + i * BOARD_RECTSIZE, to_string(PlayScene::mapArr[i][j].rightAfter).c_str(), to_string(PlayScene::mapArr[i][j].rightAfter).size());
	//    }
	//}
	drawRect(hdc, _stopGameRect.left, _stopGameRect.top, _stopGameRect.right - _stopGameRect.left, _stopGameRect.bottom - _stopGameRect.top);
}