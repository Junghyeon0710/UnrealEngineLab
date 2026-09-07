# 아키텍처와 의존성

<a id="contents"></a>

## 목차

1. [먼저 정해둘 방향](#direction)
2. [Owner가 소유 객체를 호출할 때](#owner-to-child)
3. [소유 객체가 사건을 알릴 때](#child-to-owner)
4. [Interface로 공통 기능 호출하기](#interface)
5. [Interface와 Delegate 구분하기](#interface-vs-delegate)
6. [형제 Component가 협력할 때](#sibling-components)
7. [Component 사이에서 값을 조회할 때](#queries)
8. [특정 Owner 전용 Component](#owner-specific)
9. [Interface와 Abstract Base](#interface-vs-abstract)
10. [Struct와 DTO](#dto)
11. [Owner와 Orchestrator의 책임](#orchestrator)
12. [God Object 피하기](#god-object)
13. [순환 의존성과 Include 관리](#circular-dependencies)
14. [통신 수단 선택 기준](#decision-table)
15. [정리](#summary)

---

이 문서의 내용은 모든 클래스에 똑같이 적용하는 절대적인 규칙이 아니다. 시스템 사이의 구체 타입 의존을 필요한 범위로 제한하고, 직접 호출과 Interface, Delegate, DTO를 언제 사용할지 판단하기 위해 정리한 기준이다.

작은 기능까지 무조건 Interface나 Delegate로 바꾸면 오히려 호출 흐름을 찾기 어려워질 수 있다. 관계가 분명한 곳은 직접 호출하고, 변경 가능성이나 재사용 범위가 커지는 지점에 추상화를 적용하는 편이 낫다.

---

<a id="direction"></a>

## 1. 먼저 정해둘 방향

Character가 여러 Component를 소유하는 상황을 예로 들어보자.

```text
AMyCharacter
├─ UHealthComponent
├─ UCombatComponent
├─ UAttributeComponent
└─ UStatusEffectComponent
```

이 구조에서는 다음 방향을 기본으로 생각할 수 있다.

```text
Owner → 소유 객체
직접 호출

소유 객체 → Owner
사건 알림은 Delegate 우선

소유 객체 → 다른 소유 객체
Owner가 협력 과정을 조율
```

중요한 것은 화살표의 수를 무조건 줄이는 일이 아니다. 각 객체가 누구를 알고 있고, 그 관계가 필요한 이유를 설명할 수 있어야 한다.

---

<a id="owner-to-child"></a>

## 2. Owner가 소유 객체를 호출할 때

Owner가 직접 만들고 수명을 관리하는 Component라면 구체 타입으로 호출해도 자연스럽다.

```cpp
void AMyCharacter::StartCombat()
{
    CombatComponent->StartCombat();
}
```

Character가 사망했을 때 자신이 소유한 Component를 순서대로 정리하는 것도 Owner의 역할로 볼 수 있다.

```cpp
void AMyCharacter::HandleDeath()
{
    CombatComponent->StopCombat();
    StatusEffectComponent->ClearAllEffects();
    GetCharacterMovement()->DisableMovement();
}
```

Owner가 해당 Component의 존재를 아는 것이 설계에 포함되어 있다면 중간에 Interface를 넣는다고 의존성이 사라지는 것은 아니다. 오히려 실제 관계만 감추고 코드를 따라가기 어렵게 만들 수도 있다.

다음 질문에 답해보면 판단하기 쉽다.

> 이 객체를 내가 소유하고 있고, 구체 타입을 알아도 되는가?

그렇다면 직접 호출을 먼저 고려한다.

---

<a id="child-to-owner"></a>

## 3. 소유 객체가 사건을 알릴 때

Component에서 사건이 발생했을 때는 Owner에게 다음 행동까지 지시하기보다 자신에게 일어난 일을 알리는 쪽이 역할을 분리하기 좋다.

HealthComponent는 체력이 0이 됐다는 사실만 알린다.

```cpp
DECLARE_MULTICAST_DELEGATE(FOnHealthZero);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnHealthChanged, float);

void UHealthComponent::ApplyDamage(float Damage)
{
    if (Damage <= 0.f)
    {
        return;
    }

    CurrentHealth = FMath::Max(0.f, CurrentHealth - Damage);
    OnHealthChanged.Broadcast(CurrentHealth);

    if (CurrentHealth == 0.f)
    {
        OnHealthZero.Broadcast();
    }
}
```

Character는 그 사건을 구독하고 이후의 흐름을 결정한다.

```cpp
void AMyCharacter::BeginPlay()
{
    Super::BeginPlay();

    HealthComponent->OnHealthZero.AddUObject(
        this,
        &AMyCharacter::HandleHealthZero
    );
}
```

```cpp
void AMyCharacter::HandleHealthZero()
{
    CombatComponent->StopCombat();
    StatusEffectComponent->ClearAllEffects();
    GetCharacterMovement()->DisableMovement();
}
```

이렇게 하면 HealthComponent는 Combat이나 Movement를 알 필요가 없다. 사망 시 처리할 기능이 늘어나도 체력 계산 코드까지 함께 수정할 가능성이 줄어든다.

Multicast Delegate는 여러 함수를 구독시킬 수 있지만 반환값을 사용할 수 없고 호출 순서도 보장되지 않는다. 순서나 결과가 중요한 작업을 Delegate 체인에 맡기지 않는 편이 좋다. 자세한 동작은 [Unreal Engine Multicast Delegate 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/multicast-delegates-in-unreal-engine)에서 확인할 수 있다.

---

<a id="interface"></a>

## 4. Interface로 공통 기능 호출하기

호출 대상의 구체 타입은 다르지만 같은 기능을 제공해야 할 때 Interface가 잘 맞는다.

```text
Player
  │
  └─ IInteractable
       ├─ Door
       ├─ NPC
       ├─ PickupItem
       └─ Chest
```

Player는 대상이 Door인지 NPC인지 구분할 필요 없이 상호작용이 가능한지만 확인하면 된다.

다음은 C++과 Blueprint 양쪽에서 구현할 수 있는 Interface의 간단한 예다. 실제 코드에서는 모듈의 API 매크로와 필요한 헤더도 함께 선언해야 한다.

```cpp
UINTERFACE(MinimalAPI, Blueprintable)
class UInteractable : public UInterface
{
    GENERATED_BODY()
};

class IInteractable
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, BlueprintNativeEvent)
    void Interact(AActor* Interactor);
};
```

C++ 클래스에서는 `_Implementation` 함수를 구현한다.

```cpp
void ADoor::Interact_Implementation(AActor* Interactor)
{
    OpenDoor();
}
```

호출할 때는 `Execute_` 함수를 사용한다.

```cpp
void UInteractionComponent::TryInteract(AActor* Target)
{
    if (!Target ||
        !Target->GetClass()->ImplementsInterface(UInteractable::StaticClass()))
    {
        return;
    }

    IInteractable::Execute_Interact(Target, GetOwner());
}
```

이 방식은 Interface가 C++이나 Blueprint 중 어디에서 구현됐는지 호출하는 쪽이 구분하지 않아도 된다. `BlueprintNativeEvent`와 `Execute_` 호출 방식은 [Unreal Engine Interface 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/interfaces-in-unreal-engine)에서 더 자세히 볼 수 있다.

Interface가 없다면 호출하는 쪽에서 구체 타입을 계속 확인하게 되기 쉽다.

```cpp
if (ADoor* Door = Cast<ADoor>(Target))
{
    Door->OpenDoor();
}
else if (ANPC* NPC = Cast<ANPC>(Target))
{
    NPC->StartDialogue();
}
else if (APickupItem* Item = Cast<APickupItem>(Target))
{
    Item->Pickup(GetOwner());
}
```

대상 종류가 늘어날 때마다 이 분기까지 수정해야 한다면 공통 역할을 Interface로 묶을 수 있는지 살펴볼 만하다.

---

<a id="interface-vs-delegate"></a>

## 5. Interface와 Delegate 구분하기

둘의 차이는 요청과 사건으로 생각하면 이해하기 쉽다.

```text
Interface 또는 직접 호출
"너 이 작업을 해줘."

Delegate
"나에게 이런 일이 생겼어."
```

| 구분 | Interface 또는 직접 호출 | Delegate |
| --- | --- | --- |
| 목적 | 특정 대상에게 행동 요청 | 사건이나 상태 변화 알림 |
| 대상 | 호출할 객체가 분명함 | 구독자가 없거나 여러 명일 수 있음 |
| 반환값 | 사용할 수 있음 | Multicast Delegate는 반환값을 사용하지 않음 |
| 예시 | `Interact()`, `CanInteract()` | `OnHealthChanged`, `OnAttackFinished` |

Delegate로 명령처럼 보이는 이벤트를 보내는 것도 기술적으로는 가능하다.

```cpp
OnRequestOpenDoor.Broadcast();
```

하지만 반드시 한 대상이 문을 열어야 하는 상황이라면 구독자가 없거나 여러 명인 Delegate보다 직접 호출이나 Interface가 의도를 더 잘 보여준다.

UI처럼 요청 자체를 이벤트로 취급하고 여러 계층이 반응할 수 있는 구조라면 `OnCloseRequested` 같은 이름도 자연스러울 수 있다. 이름만 보고 결정하기보다 구독자 수, 처리 보장, 반환값, 실행 순서가 필요한지를 함께 봐야 한다.

---

<a id="sibling-components"></a>

## 6. 형제 Component가 협력할 때

CombatComponent가 StatusEffectComponent를 직접 찾아 명령한다고 해보자.

```cpp
void UCombatComponent::ApplyAttackResult()
{
    UStatusEffectComponent* StatusComponent =
        GetOwner()->FindComponentByClass<UStatusEffectComponent>();

    if (StatusComponent)
    {
        StatusComponent->ApplyStun();
    }
}
```

이제 CombatComponent는 StatusEffectComponent의 구체 타입과 기능을 알아야 한다. 이런 관계가 여러 방향으로 늘어나면 Component를 따로 나눈 의미가 흐려지고 변경 범위도 커진다.

Component는 자신의 결과를 알리고 Owner가 다음 작업을 조율하도록 만들 수 있다.

```cpp
DECLARE_MULTICAST_DELEGATE_OneParam(
    FOnAttackHit,
    const FAttackResult&
);

void UCombatComponent::HandleHit(const FAttackResult& Result)
{
    OnAttackHit.Broadcast(Result);
}
```

```cpp
void AMyCharacter::HandleAttackHit(const FAttackResult& Result)
{
    if (Result.bApplyStun)
    {
        StatusEffectComponent->ApplyStun();
    }
}
```

흐름은 다음과 같다.

```text
CombatComponent
      │
      │ 공격 적중
      ▼
   Character
      │
      ▼
StatusEffectComponent
```

다만 두 Component가 항상 함께 사용되고 그 관계가 단순하다면 직접 참조가 더 이해하기 쉬울 수도 있다. Owner를 거치면서 전달 코드만 늘어나는지, 두 Component를 독립적으로 바꾸거나 재사용할 가능성이 있는지를 보고 선택한다.

---

<a id="queries"></a>

## 7. Component 사이에서 값을 조회할 때

값을 읽는 Query는 상태를 바꾸는 Command보다 비교적 느슨하게 볼 수 있다.

```cpp
const UAttributeComponent* AttributeComponent =
    GetOwner()->FindComponentByClass<UAttributeComponent>();

if (AttributeComponent)
{
    const float AttackPower = AttributeComponent->GetAttackPower();
}
```

단순한 조회까지 모두 Owner나 Delegate를 거치면 코드가 불필요하게 복잡해질 수 있다. 필요한 범위에서는 직접 Query나 읽기 전용 Interface를 사용할 수 있다.

다만 조회를 핑계로 상대 객체의 내부 상태를 직접 수정하지 않는다.

```cpp
// 외부에서 직접 변경하지 않는다.
AttributeComponent->CurrentAttackPower = 9999.f;
```

Query가 여러 곳에 퍼지고 서로의 내부 상태를 지나치게 많이 알아야 한다면 Shared State나 별도의 조회 모델이 필요한지 다시 살펴본다.

---

<a id="owner-specific"></a>

## 8. 특정 Owner 전용 Component

모든 Component를 범용으로 만들 필요는 없다.

`UPlayerCustomizationComponent`가 `AMyPlayerCharacter`에서만 사용되고 앞으로도 재사용할 계획이 없다면 구체 Owner 의존을 허용할 수 있다.

```cpp
if (AMyPlayerCharacter* Character =
        Cast<AMyPlayerCharacter>(GetOwner()))
{
    Character->RefreshCustomization();
}
```

범용 Component인 것처럼 만들어놓고 내부에서 특정 Character만 가정하는 것보다, 제한된 사용 범위를 이름과 문서로 분명하게 밝히는 편이 낫다.

```text
재사용을 목표로 하는 Component
Interface와 Delegate를 우선 검토

특정 Owner 전용 Component
필요한 구체 타입 의존 허용
```

---

<a id="interface-vs-abstract"></a>

## 9. Interface와 Abstract Base

Interface는 서로 다른 클래스가 같은 기능을 제공하게 만들고 싶을 때 적합하다.

```text
Door
NPC
PickupItem
Chest
  │
  └─ IInteractable
```

Abstract Base는 공통 호출 규칙뿐 아니라 상태와 기본 구현도 공유해야 할 때 사용할 수 있다.

```cpp
UCLASS(Abstract)
class UUpgradeComponentBase : public UActorComponent
{
    GENERATED_BODY()

protected:
    UPROPERTY()
    int32 UpgradeLevel = 0;

public:
    virtual void Upgrade()
        PURE_VIRTUAL(UUpgradeComponentBase::Upgrade, );
};
```

선택 기준은 비교적 단순하다.

```text
공통 기능의 약속만 필요
Interface

공통 상태와 기본 구현도 필요
Abstract Base
```

상속 관계가 자연스러운지, 공유하는 상태가 실제로 같은 규칙을 가지는지도 함께 확인해야 한다.

---

<a id="dto"></a>

## 10. Struct와 DTO

시스템 사이에 관련된 데이터를 함께 전달해야 한다면 Struct나 DTO(Data Transfer Object)를 사용할 수 있다.

```cpp
USTRUCT(BlueprintType)
struct FAttackResult
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly)
    float Damage = 0.f;

    UPROPERTY(BlueprintReadOnly)
    bool bCritical = false;

    UPROPERTY(BlueprintReadOnly)
    bool bApplyStun = false;
};
```

Delegate에도 하나의 의미 있는 데이터로 전달할 수 있다.

```cpp
OnAttackHit.Broadcast(Result);
```

관련 인자가 계속 늘어나는 함수보다 데이터의 의미가 드러나는 타입이 변경에 대응하기 쉽다.

```cpp
// 인자만 보고 각 값의 관계를 파악하기 어렵다.
ReceiveDamage(
    Damage,
    SkillID,
    Instigator,
    HitLocation,
    bCritical
);

// 하나의 요청이라는 의미가 드러난다.
ReceiveDamage(DamageRequest);
```

DTO는 데이터 전달에 집중하도록 두고, 전투 계산이나 상태 변경 같은 로직은 해당 책임을 가진 Component나 System에서 처리한다.

---

<a id="orchestrator"></a>

## 11. Owner와 Orchestrator의 책임

Owner는 자신이 소유한 Component 사이의 협력 순서와 전체 흐름을 담당할 수 있다.

```cpp
void AMyCharacter::HandleHealthZero()
{
    CombatComponent->StopCombat();
    StatusEffectComponent->ClearAllEffects();
    InventoryComponent->DropDeathItems();
    GetCharacterMovement()->DisableMovement();
}
```

```text
Owner
누가 언제 무엇을 할지 조율

Component
각 기능을 실제로 처리
```

Owner가 모든 사건을 직접 조율하면 흐름을 한곳에서 찾기 쉽다는 장점이 있다. 반면 기능이 늘면서 Owner가 수많은 Component의 세부 순서까지 알게 되면 새로운 병목이 될 수 있다.

조율 코드가 계속 커진다면 별도의 Coordinator나 Gameplay System으로 흐름을 옮길 시점인지 확인한다.

---

<a id="god-object"></a>

## 12. God Object 피하기

Owner가 Orchestrator라고 해서 모든 계산과 세부 구현까지 직접 맡아야 하는 것은 아니다.

다음처럼 Character가 전투의 모든 규칙을 계산하기 시작하면 책임이 빠르게 커진다.

```cpp
void AMyCharacter::Attack()
{
    // 공격력 계산
    // 방어력 계산
    // 크리티컬 계산
    // 버프 계산
    // 스킬 계수 계산
    // 상태 이상 계산
}
```

Character는 흐름만 시작하고 계산은 전투 책임을 가진 Component에 맡길 수 있다.

```cpp
void AMyCharacter::Attack(AActor* Target)
{
    CombatComponent->Attack(Target);
}
```

Owner에는 조율 로직을, Component에는 실제 기능 로직을 둔다는 경계를 유지한다.

---

<a id="circular-dependencies"></a>

## 13. 순환 의존성과 Include 관리

구체 타입이 서로를 알아야 하는 구조가 늘어나면 변경하기 어렵고 헤더 의존성도 커진다.

```text
Character
    │
    ▼
CombatComponent
    │
    └──── 다시 Character를 참조
```

헤더가 서로를 Include하는 구조도 피하는 편이 좋다.

```cpp
// Character.h
#include "CombatComponent.h"

// CombatComponent.h
#include "Character.h"
```

포인터나 참조 타입의 선언만 필요하다면 헤더에서는 Forward Declaration을 쓰고 실제 구현이 필요한 `.cpp`에서 Include할 수 있다.

```cpp
// Character.h
class UCombatComponent;
```

```cpp
// Character.cpp
#include "CombatComponent.h"
```

Forward Declaration만으로 해결되지 않는 경우도 있다. 상속할 부모 타입이나 값으로 보관하는 타입처럼 완전한 정의가 필요한 대상은 해당 헤더를 Include해야 한다.

무조건 Include를 없애는 것이 목적은 아니다. 자신이 사용하는 타입의 헤더는 직접 포함하고, 불필요한 전이 의존을 줄이는 것이 중요하다. Unreal의 기본 방향은 [Include What You Use 문서](https://dev.epicgames.com/documentation/en-us/unreal-engine/include-what-you-use-iwyu-for-unreal-engine-programming)에서 확인할 수 있다.

---

<a id="decision-table"></a>

## 14. 통신 수단 선택 기준

| 상황 | 먼저 고려할 방식 |
| --- | --- |
| Owner가 소유 Component에 작업 요청 | 직접 함수 호출 |
| Component에서 사건이나 상태 변화 발생 | Delegate |
| 특정 객체에 작업 요청 | 직접 함수 또는 Interface |
| 구체 타입을 모르는 여러 객체에 같은 기능 호출 | Interface |
| 반환값이나 처리 보장이 필요 | 직접 함수 또는 Interface |
| 형제 Component 사이의 Command | Owner 조율 |
| 형제 Component 사이의 단순 Query | 제한적인 직접 조회 또는 읽기 전용 Interface |
| 관련된 여러 값 전달 | Struct 또는 DTO |
| 공통 상태와 기본 구현 공유 | Abstract Base |

표의 선택이 언제나 정답은 아니다. 호출 흐름을 쉽게 추적할 수 있는지, 처리 대상이 분명한지, 반환값이나 순서가 필요한지, 이후에 구현이 바뀔 가능성이 있는지를 함께 본다.

---

<a id="summary"></a>

## 15. 정리

```text
Owner → 소유 객체
직접 호출

특정 대상에게 작업 요청
직접 함수 또는 Interface

사건이나 상태 변화 알림
Delegate

형제 Component 사이의 Command
Owner가 조율

단순한 읽기 Query
필요한 범위에서 직접 조회

여러 관련 데이터 전달
Struct 또는 DTO
```

가장 자주 쓰는 구분은 다음 두 문장이다.

> **“너 이 작업을 해줘”라면 직접 호출이나 Interface를 먼저 생각한다.**
>
> **“나에게 이런 일이 생겼어”라면 Delegate를 먼저 생각한다.**

그다음에는 소유 관계와 재사용 범위, 반환값, 처리 순서, 디버깅 비용을 확인한다. 구조를 복잡하게 만드는 것보다 현재 의존 관계를 설명할 수 있고 변경할 위치를 쉽게 찾을 수 있게 만드는 것이 더 중요하다.

---

[목차로 돌아가기](#contents) · [메인 README의 CS 목차로 돌아가기](../../README.md#cs)
