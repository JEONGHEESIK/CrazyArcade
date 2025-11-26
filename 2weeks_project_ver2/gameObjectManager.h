#pragma once
#include "singletonBase.h"
#include "GameObject.h"
class GameObjectManager : public SingletonBase<GameObjectManager>
{
private:
    vector<GameObject*> _gameObj;
    vector<int> _removeQueue;  // 삭제 대기 목록
    vector<GameObjectTag> _layerOrders;
    int _instance_id;
    GameObject* _lastUpdateObj;  // 디버그용: 마지막 업데이트 객체
public:
    GameObjectManager();
    ~GameObjectManager();

    size_t getGameObjSize()
    {
        return _gameObj.size();
    }
    vector<GameObject*> getGameObject()
    {
        return _gameObj;
    }

    void registerObj(GameObject* gameObj);
    void removeObj(int id);
    void removeObjAll();

    void updateObj();
    void renderObj(HDC hdc);
    void releaseObj();


    void notifyCollisions();

    string showTagForDebug(GameObjectTag tag);
    void debug(HDC hdc);
};
