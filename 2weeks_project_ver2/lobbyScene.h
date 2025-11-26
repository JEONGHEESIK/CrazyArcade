#pragma once
class LobbyScene : public Scene
{
private:
    RECT _rc;
    RECT _rcBack;
    MapTypeTag _mapType;
    ModeTypeTag _mode;

    bool _isMapSet;
    bool _check1;
    bool _check2;
    bool _autoRestartGame;  // AI 학습용 자동 재시작
public:
    LobbyScene();
    ~LobbyScene();

    virtual void init() override;
    virtual void release() override;
    virtual void update() override;
    virtual void render(HDC hdc) override;
    virtual void handleArgs(vector<int> args) override;
};