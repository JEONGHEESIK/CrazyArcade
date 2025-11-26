#include "stdafx.h"
#include "lobbyScene.h"
#include "playScene.h"

extern POINT ptMouse;

LobbyScene::LobbyScene()
	: _mapType(MapTypeTag::Not)
	, _mode(ModeTypeTag::Not)
	, _isMapSet(false)
	, _check1(false)
	, _check2(false)
	, _autoRestartGame(false)
{
	_rc = makeRect(666, 641, 250, 74);
	_rcBack = makeRect(16, 743, 40, 32);
}

LobbyScene::~LobbyScene()
{
}

void LobbyScene::init()
{
	//기존에 있던 플레이씬을 지우고 새로운 플레이씬을 생성한다
	SCENEMANAGER->deleteScene(SceneTag::Play);
	PlayScene* play = new PlayScene;
	SCENEMANAGER->registerScene(SceneTag::Play, play);

	// AI 학습용 자동 재시작 (로비 진입 시 바로 게임 시작)
	if (_autoRestartGame)
	{
		cout << "[AUTO] Restarting game..." << endl;
		_mode = ModeTypeTag::TwoPlayer;
		_mapType = MapTypeTag::Forest;
		SOUNDMANAGER->stop(static_cast<int>(SoundTypeTag::LobbyScene));
		SCENEMANAGER->changeScene(SceneTag::Play, vector<int>{static_cast<int>(_mode), static_cast<int>(_mapType)});
	}
}

void LobbyScene::release()
{
}

void LobbyScene::update()
{
	// 자동 재시작 모드가 아닐 때만 음악 재생
	if (!_autoRestartGame)
	{
		SOUNDMANAGER->repeatPlay(static_cast<int>(SoundTypeTag::LobbyScene), SoundTypeTag::LobbyScene);
	}
	//TODO: 버튼에 따라
	//캐릭터 선택도 넘겨준다
	if (!_isMapSet)
	{
		_mapType = MapTypeTag::Forest; //우선 포레스트로 셋
	}

	if (PtInRect(&_rc, ptMouse))
	{
		if (KEYMANAGER->isOnceKeyDown(VK_LBUTTON))
		{
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::Click), SoundTypeTag::Click);
			SOUNDMANAGER->stop(static_cast<int>(SoundTypeTag::LobbyScene));
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::GameStart), SoundTypeTag::GameStart);
			SCENEMANAGER->changeScene(SceneTag::Play, vector<int>{static_cast<int>(_mode), static_cast<int>(_mapType)});
		}
		if (!_check1)
		{
			_check1 = true;
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::PtInRect), SoundTypeTag::PtInRect);
		}
	}
	else
	{
		_check1 = false;
	}

	if (PtInRect(&_rcBack, ptMouse))
	{
		if (KEYMANAGER->isOnceKeyDown(VK_LBUTTON))
		{
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::Click), SoundTypeTag::Click);
			SOUNDMANAGER->stop(static_cast<int>(SoundTypeTag::LobbyScene));

			SCENEMANAGER->changeScene(SceneTag::ModeSelect);
		}
		if (!_check2)
		{
			_check2 = true;
			SOUNDMANAGER->play(static_cast<int>(SoundTypeTag::PtInRect), SoundTypeTag::PtInRect);
		}
	}
	else
	{
		_check2 = false;
	}

}

void LobbyScene::render(HDC hdc)
{
	IMAGEMANAGER->findImage("lobbySceneBg")->render(hdc, 0, 0);
}

void LobbyScene::handleArgs(vector<int> args)
{
	// args[0] == 1이면 자동 재시작 모드
	if (!args.empty() && args[0] == 1)
	{
		_autoRestartGame = true;
		cout << "[LOBBY] Auto-restart mode enabled" << endl;
	}
	else if (!args.empty())
	{
		// 기존 로직: ModeSelect에서 넘어올 때
		_mode = static_cast<ModeTypeTag>(args.at(0));
		_autoRestartGame = false;
	}
	else
	{
		_autoRestartGame = false;
	}
}
