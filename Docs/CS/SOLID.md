# SOLID 원칙 정리

SOLID는 객체지향 설계에서 자주 언급되는 5가지 원칙이다.

실무에서는 이 원칙들을 무조건 지키기보다는, 코드가 커지면서 유지보수가 어려워지거나 수정 범위가 점점 넓어질 때 구조를 다시 보는 기준으로 사용하는 게 더 맞다고 생각한다.

아래 코드는 구조를 설명하기 위해 선언과 구현을 일부 생략한 예시다. `U`나 `A` 접두사를 쓴 클래스도 실제 프로젝트에서는 `UObject`·`AActor` 상속과 리플렉션 매크로 등 필요한 선언을 갖춰야 한다. 예제의 일반 C++ 인터페이스와 언리얼의 `UInterface` 선언 방식도 구분해서 보면 된다.

---

## 1. SRP - 단일 책임 원칙

**Single Responsibility Principle**

하나의 클래스가 너무 많은 역할을 담당하지 않도록 하는 원칙이다.

조금 더 풀어서 말하면, 하나의 클래스가 여러 이유 때문에 계속 수정되고 있다면 책임이 너무 많이 들어가 있는지 확인해볼 필요가 있다.

예를 들어 다음과 같은 `InventoryManager`가 있다고 하자.

```cpp
class UInventoryManager
{
public:
    void AddItem();
    void RemoveItem();

    void SaveInventory();
    void SendInventoryToServer();
    void PlayAcquireSound();
    void ShowAcquirePopup();
};
```

이름은 `InventoryManager`지만 실제로는 인벤토리 관리뿐만 아니라 저장, 네트워크, 사운드, UI까지 담당하고 있다.

이런 구조에서는 인벤토리 기능을 수정할 때뿐만 아니라 서버 통신 방식이나 UI 연출이 변경될 때도 `InventoryManager`를 수정하게 된다.

프로젝트가 작을 때는 큰 문제가 없어 보이지만 기능이 계속 추가되면 클래스가 점점 비대해지고 다른 시스템과의 의존성도 많아진다.

이럴 때는 역할을 나눌 수 있다.

```text
InventoryManager
- 아이템 추가/삭제
- 아이템 검색
- 인벤토리 상태 관리

InventorySaveService
- 인벤토리 저장

InventoryNetworkService
- 서버 통신

InventoryWidget
- 화면 표시
```

인벤토리가 변경되었다는 사실만 외부에 전달하고,

```cpp
OnInventoryChanged.Broadcast();
```

UI에서 해당 이벤트를 받아 화면을 갱신하도록 만들 수도 있다.

언리얼에서는 기능 단위로 `ActorComponent`를 분리하는 것도 비슷한 예다.

```text
Character
 ├─ HealthComponent
 ├─ InventoryComponent
 └─ AbilityComponent
```

다만 SRP를 적용한다고 해서 함수 하나마다 클래스를 따로 만들 필요는 없다.

```cpp
AddItem();
RemoveItem();
FindItem();
SortItem();
```

이 함수들은 모두 인벤토리라는 같은 책임에 속하기 때문에 하나의 클래스에 있어도 자연스럽다.

### 이런 경우 한번 확인해볼 만하다

- 클래스가 계속 커지고 있다.
- 관련 없는 `include`가 많아지고 있다.
- UI를 수정했는데 Manager도 수정해야 한다.
- 네트워크 변경 때문에 게임 로직까지 같이 수정된다.
- 하나의 Manager가 너무 많은 시스템을 알고 있다.

---

## 2. OCP - 개방 폐쇄 원칙

**Open-Closed Principle**

기존 코드를 계속 수정하지 않고 새로운 기능을 추가할 수 있도록 만드는 원칙이다.

예를 들어 효과 타입을 아래처럼 처리한다고 해보자.

```cpp
void ApplyEffect(EEffectType Type)
{
    switch (Type)
    {
    case EEffectType::Fire:
        ApplyFire();
        break;

    case EEffectType::Ice:
        ApplyIce();
        break;

    case EEffectType::Poison:
        ApplyPoison();
        break;
    }
}
```

처음에는 단순하지만 새로운 타입이 계속 추가된다면 문제가 생긴다.

```text
Lightning 추가 → switch 수정
Bleeding 추가  → switch 수정
Holy 추가      → switch 수정
```

비슷한 `switch`가 프로젝트 여러 곳에 있다면 새로운 타입 하나를 추가할 때 여러 파일을 수정해야 할 수도 있다.

이런 부분은 인터페이스나 다형성으로 분리할 수 있다.

```cpp
class IEffect
{
public:
    virtual ~IEffect() = default;
    virtual void Apply() = 0;
};
```

```cpp
class FFireEffect : public IEffect
{
public:
    virtual void Apply() override
    {
        // Fire 처리
    }
};
```

새로운 효과가 필요하면 새로운 클래스를 추가한다.

```cpp
class FLightningEffect : public IEffect
{
public:
    virtual void Apply() override
    {
        // Lightning 처리
    }
};
```

호출하는 쪽도 구체적인 효과가 아니라 공통 인터페이스를 사용해야 한다.

```cpp
void ApplyEffect(IEffect& Effect)
{
    Effect.Apply();
}
```

이렇게 하면 효과가 늘어나도 호출 코드는 그대로 둘 수 있다. 어떤 효과를 생성할지 결정하는 등록 코드나 조립 지점은 바뀔 수 있다. OCP는 모든 수정을 없애는 것보다, 자주 바뀌는 부분과 안정적으로 유지할 부분을 나누는 데 가깝다.

언리얼에서는 코드로 분기하지 않고 데이터로 처리하는 방법도 많이 사용한다.

예를 들어:

```cpp
if (Level == 1)
{
    Cost = 100;
}
else if (Level == 2)
{
    Cost = 200;
}
```

처럼 작성하는 대신 DataTable에 데이터를 넣을 수 있다. 행 구조와 테이블을 이용한 데이터 관리 방식은 [Data Driven Gameplay 공식 문서](https://dev.epicgames.com/documentation/unreal-engine/data-driven-gameplay-elements-in-unreal-engine?lang=en-US)를 참고하면 된다.

| Level | Cost | SuccessRate |
| ---: | ---: | ---: |
| 1 | 100 | 100 |
| 2 | 200 | 80 |
| 3 | 500 | 60 |

테이블의 행을 읽어 처리하도록 코드를 만들어두면, 같은 계산 규칙을 사용하는 단계는 데이터만 추가해서 늘릴 수 있다. 계산 방식 자체가 달라지는 경우에는 코드 수정도 필요하다.

언리얼에서는 다음 구조들과 연결해서 생각할 수 있다.

```text
DataTable
DataAsset
GameplayTag
Strategy Pattern
Factory Pattern
Gameplay Ability
GameFeature
```

DataTable이나 GameplayTag를 사용했다는 사실만으로 OCP를 지킨 것도 아니다. 태그마다 다시 분기문을 늘리고 있다면 변경 부담은 그대로 남을 수 있다.

물론 `if`나 `switch`가 있다는 이유만으로 OCP에 문제가 있는 것은 아니다.

변경 가능성이 높고 새로운 타입이 계속 추가될 것으로 예상되는 부분에 적용하는 것이 중요하다.

---

## 3. LSP - 리스코프 치환 원칙

**Liskov Substitution Principle**

부모 클래스를 사용하는 코드에 자식 클래스를 넣어도 기존 동작이 깨지지 않아야 한다는 원칙이다.

예를 들어:

```cpp
class ABird
{
public:
    virtual ~ABird() = default;
    virtual void Fly() = 0;
};
```

라는 부모 클래스가 있다고 하자.

```cpp
class APenguin : public ABird
{
public:
    virtual void Fly() override
    {
        checkNoEntry();
    }
};
```

코드상으로는 상속이 가능하지만 `Penguin`은 `Fly()`라는 부모의 기능을 정상적으로 수행하지 못한다.

그러면 이런 코드에서 문제가 생긴다.

```cpp
void MakeBirdFly(ABird* Bird)
{
    Bird->Fly();
}
```

`ABird` 대신 어떤 자식이 들어오더라도 정상적으로 동작할 것이라고 기대했는데 `Penguin`을 넣으면 그 전제가 깨진다.

이런 경우 상속 관계를 다시 나누는 방법이 있다.

```text
Bird
 ├─ FlyingBird
 │   ├─ Eagle
 │   └─ Sparrow
 │
 └─ Penguin
```

혹은 행동을 인터페이스로 분리할 수도 있다.

```text
Bird
 ├─ Eagle
 └─ Penguin

IFlyable
   ↑
 Eagle
```

이렇게 하면 `Eagle`만 날 수 있다는 기능을 가지게 된다.

언리얼에서는 `UInterface`나 `ActorComponent`를 이용해 이런 기능을 분리하는 경우가 많다.

예를 들어:

```text
IInteractable
IDamageable
IFlyable
ISwimmable
```

또는 기능 자체를 Component로 빼는 방법도 있다. 아래 이름은 엔진 클래스 목록이 아니라 이동 기능을 분리하는 개념적인 예시다.

```text
Character
   ↓
MovementComponent

 ├─ GroundMovement
 ├─ FlyingMovement
 └─ SwimmingMovement
```

### 이런 코드가 많다면 상속 구조를 확인해볼 만하다

```cpp
checkNoEntry();
```

```cpp
return false;
```

```cpp
return nullptr;
```

특히 자식 클래스마다

```text
"이 클래스에서는 이 함수 호출하면 안 됩니다."
```

같은 예외 설명이 많아진다면 부모가 너무 많은 행동을 요구하고 있는 것은 아닌지 볼 필요가 있다.

부모를 사용하는 곳에서 특정 자식을 계속 검사하는 것도 비슷한 신호다.

```cpp
if (Object->IsA<ASpecialChild>())
{
    // 예외 처리
}
```

다만 `false`나 `nullptr`를 반환한다고 무조건 LSP 위반은 아니다. 부모의 계약에서 실패나 값이 없는 경우를 허용했다면 정상적인 결과다. 호출자가 기대하는 입력 조건, 결과, 상태 변화를 자식도 지키는지가 기준이다.

상속은 단순히 코드 재사용을 위한 기능이라기보다 부모가 제공하는 행동을 자식도 지킨다는 관계로 보는 게 좋다.

---

## 4. ISP - 인터페이스 분리 원칙

**Interface Segregation Principle**

인터페이스를 사용하는 쪽이 필요하지 않은 기능까지 의존하지 않도록 나누는 원칙이다. 구현하는 쪽에서 쓰지 않는 함수를 억지로 채우고 있다면 이 문제를 의심해볼 수 있다.

예를 들어:

```cpp
class IGameObject
{
public:
    virtual ~IGameObject() = default;
    virtual void Attack() = 0;
    virtual void Fly() = 0;
    virtual void Swim() = 0;
    virtual void Interact() = 0;
};
```

이 인터페이스를 `Door`가 구현한다고 하면:

```cpp
class ADoor : public IGameObject
{
public:
    virtual void Attack() override {}
    virtual void Fly() override {}
    virtual void Swim() override {}

    virtual void Interact() override
    {
        Open();
    }
};
```

Door는 `Interact()`만 필요하지만 나머지 함수도 억지로 구현해야 한다.

이런 경우 기능 단위로 나눌 수 있다.

```cpp
class IAttackable
{
public:
    virtual ~IAttackable() = default;
    virtual void Attack() = 0;
};
```

```cpp
class IInteractable
{
public:
    virtual ~IInteractable() = default;
    virtual void Interact() = 0;
};
```

```cpp
class IFlyable
{
public:
    virtual ~IFlyable() = default;
    virtual void Fly() = 0;
};
```

그러면 필요한 기능만 선택해서 구현할 수 있다.

```text
Door
→ IInteractable

Dragon
→ IAttackable
→ IFlyable

NPC
→ IInteractable
→ IAttackable
```

언리얼의 `UInterface`도 이런 식으로 사용하기 좋다. 엔진 리플렉션에 노출할 인터페이스는 `UINTERFACE` 클래스와 실제 함수를 선언하는 `I` 클래스를 함께 정의한다. 선언 방식은 [언리얼 인터페이스 공식 문서](https://dev.epicgames.com/documentation/unreal-engine/interfaces-in-unreal-engine)에서 확인할 수 있다.

```text
IInteractable
IDamageable
ITargetable
ISelectable
ISaveable
```

Player 입장에서는 Door, NPC, Chest 같은 구체 클래스를 알 필요 없이 `IInteractable`만 확인하면 된다.

다만 인터페이스를 지나치게 잘게 나누는 것도 복잡도를 높일 수 있다.

예를 들어:

```text
ICanOpen
ICanClose
ICanLock
ICanUnlock
ICanToggle
```

이 기능들이 항상 같이 사용된다면 하나의 `IDoorInteraction`으로 묶는 편이 오히려 관리하기 쉬울 수 있다.

### 확인해볼 부분

인터페이스를 구현한 클래스에서 다음과 같은 코드가 반복된다면 인터페이스가 너무 큰지 볼 수 있다.

```cpp
virtual void Fly() override
{
}
```

또는:

```cpp
checkNoEntry();
```

```cpp
return false;
```

---

## 5. DIP - 의존성 역전 원칙

**Dependency Inversion Principle**

고수준의 게임 로직이 HTTP, 파일 저장, 플랫폼 API 같은 구체적인 구현에 직접 묶이지 않도록 하는 원칙이다. 게임 로직과 구현체가 모두 추상화에 의존하고, 그 추상화가 특정 통신 방식의 세부사항에 끌려가지 않도록 한다.

예를 들어:

```cpp
class UQuestManager
{
private:
    UHttpQuestService* QuestService;
};
```

`QuestManager`는 퀘스트 규칙을 담당하고 있지만 내부에서 `HttpQuestService`라는 구체적인 통신 구현을 직접 알고 있다.

```text
QuestManager
     ↓
HttpQuestService
```

나중에 통신 방식이 바뀐다면:

```text
HTTP
 ↓
WebSocket
 ↓
Offline
 ↓
Mock
```

QuestManager까지 수정해야 할 가능성이 높아진다.

이때 중간에 인터페이스를 둘 수 있다.

```cpp
class IQuestService
{
public:
    virtual ~IQuestService() = default;
    virtual void RequestQuest() = 0;
};
```

실제 HTTP 구현은:

```cpp
class FHttpQuestService : public IQuestService
{
public:
    virtual void RequestQuest() override
    {
        // HTTP 통신
    }
};
```

QuestManager는 인터페이스만 알도록 한다.

```cpp
class FQuestManager
{
public:
    void Init(IQuestService* InQuestService);

    void RequestQuest()
    {
        check(QuestService != nullptr);
        QuestService->RequestQuest();
    }

private:
    IQuestService* QuestService = nullptr;
};
```

구조는 다음처럼 된다.

```text
            IQuestService
            ↑           ↑

QuestManager        HttpQuestService
```

QuestManager는 실제 구현이 HTTP인지 다른 방식인지 알 필요가 없다.

구현체를 외부에서 넣어주면 테스트에도 유리하다.

```cpp
void FQuestManager::Init(IQuestService* InQuestService)
{
    QuestService = InQuestService;
}
```

실제 게임에서는:

```cpp
QuestManager.Init(&HttpQuestService);
```

테스트에서는:

```cpp
QuestManager.Init(&MockQuestService);
```

처럼 사용할 수 있다.

이 예제에서는 유효한 서비스를 `Init()`으로 먼저 전달하고, 서비스를 사용하는 동안 외부에서 그 수명을 보장한다고 가정한다. `check`만으로 제품 코드의 수명이나 오류 처리가 해결되는 것은 아니다.

이 방식이 Dependency Injection이고, DIP를 구현할 때 자주 사용하는 방법 중 하나다. 구체 클래스 포인터를 외부에서 넣어주는 것만으로 DIP가 충족되는 것은 아니다. 무엇에 의존하는지와 어떻게 전달하는지는 구분할 필요가 있다.

통신 구현을 바꿀 때마다 퀘스트 로직까지 수정하거나, 단위 테스트를 하려는데 실제 서버에 꼭 연결해야 한다면 의존성을 다시 볼 만하다.

언리얼에서는 다음과 연결해서 볼 수 있다.

```text
UInterface
Pure C++ Interface
Abstract Class
Module Interface
Subsystem
Plugin 경계
Service abstraction
```

Subsystem이나 Plugin으로 코드를 옮겼다는 이유만으로 DIP가 적용되는 것도 아니다. 경계 너머의 구체 구현을 그대로 참조하고 있다면 의존성은 남아 있다.

`GameplayMessageSubsystem`도 직접 참조를 줄이는 데 도움이 되지만 DIP와 완전히 같은 개념은 아니다.

```cpp
BroadcastMessage(TAG_QuestCompleted, Message);
```

GameplayMessage는 Sender와 Receiver가 서로를 몰라도 되도록 만드는 Event Bus에 가깝고, DIP는 구체적인 구현보다 추상화에 의존하는 것이 핵심이다.

---

## 코드에서 이런 문제가 보이면

| 상황 | 확인해볼 원칙 | 개선 방향 |
| --- | --- | --- |
| 클래스가 너무 커지고 여러 기능이 섞임 | SRP | 책임 단위로 Component, Manager, Service 분리 |
| 타입 하나 추가할 때 여러 코드 수정 | OCP | Interface, Strategy, Factory, Data Driven 검토 |
| 특정 자식에서 부모 함수를 사용할 수 없음 | LSP | 상속 구조 재검토, Interface/Composition 사용 |
| 인터페이스에 사용하지 않는 함수가 많음 | ISP | 역할 단위로 인터페이스 분리 |
| 게임 로직이 HTTP, UI, File 구현을 직접 알고 있음 | DIP | 추상화 계층 추가, DI 검토 |

---

## Unreal과 연결해서 보면

```text
SRP
→ ActorComponent나 Manager를 책임 단위로 분리

OCP
→ DataTable / DataAsset
→ Strategy / Factory
→ Gameplay Ability / GameFeature

LSP
→ Actor / Component 상속 관계가 적절한지 확인

ISP
→ 기능 단위 UInterface

DIP
→ UInterface / C++ Interface
→ Module Interface
→ Service abstraction
```

---

## 정리

```text
SRP
한 클래스가 너무 많은 일을 하지 않게 한다.

OCP
기능을 추가할 때 기존 코드를 계속 수정하지 않도록 한다.

LSP
자식 클래스가 부모가 약속한 행동을 깨지 않게 한다.

ISP
필요하지 않은 인터페이스까지 구현하도록 강요하지 않는다.

DIP
핵심 로직이 구체적인 구현에 직접 묶이지 않게 한다.
```

SOLID는 코드에 무조건 적용해야 하는 규칙이라기보다, 프로젝트가 커지면서 구조가 복잡해졌을 때 어떤 부분을 분리하거나 추상화할지 판단하는 기준으로 사용하는 게 좋다.

작은 기능에 Interface, Factory, Strategy, Service를 전부 적용하면 오히려 구조를 이해하기 어려워질 수 있기 때문에 실제 변경 가능성과 유지보수 비용을 보고 필요한 곳에 적용하는 것이 중요하다.

[메인 README의 CS 목차로 돌아가기](../../README.md#cs)
