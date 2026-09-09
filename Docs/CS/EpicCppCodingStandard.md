# Unreal Engine C++ 코딩 표준

<a id="contents"></a>

## 목차

1. [코딩 표준을 사용하는 이유](#purpose)
2. [클래스 선언 순서](#class-organization)
3. [이름 규칙](#naming)
4. [타입 접두사](#type-prefixes)
5. [함수와 변수 이름](#functions-and-variables)
6. [이식성을 고려한 타입](#portable-types)
7. [const 정확성](#const-correctness)
8. [주석 작성](#comments)
9. [Modern C++ 사용](#modern-cpp)
10. [코드 형식](#formatting)
11. [Namespace와 Macro](#namespaces)
12. [Header와 물리적 의존성](#dependencies)
13. [캡슐화와 클래스 크기](#encapsulation)
14. [표준 라이브러리 사용](#standard-library)
15. [리뷰할 때 확인할 것](#checklist)
16. [정리](#summary)

---

이 문서는 [Epic C++ Coding Standard for Unreal Engine 5.8](https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine?application_version=5.8)을 기준으로, 프로젝트에서 자주 확인할 내용을 추려 정리한 것이다.

공식 문서는 Unreal Engine 코드와 Epic 내부 코드에 적용되는 표준이다. 개인 프로젝트에서는 팀 규칙과 기존 코드의 일관성을 먼저 확인하되, 엔진 코드와 함께 읽었을 때 이질적이지 않도록 기본 방향을 맞추는 편이 좋다.

---

<a id="purpose"></a>

## 1. 코딩 표준을 사용하는 이유

코딩 표준의 목적은 코드를 같은 모양으로 꾸미는 데 있지 않다. 시간이 지난 뒤 다른 사람이 코드를 읽고 수정할 때 같은 기준으로 이해할 수 있게 만드는 데 있다.

Unreal 프로젝트에서는 다음 이유도 중요하다.

- Unreal Header Tool이 일부 타입 접두사와 선언 형식을 요구한다.
- 여러 컴파일러와 플랫폼에서 같은 코드가 동작해야 한다.
- Engine 코드와 프로젝트 코드를 오갈 때 읽는 방식이 달라지지 않는다.
- Header 의존성을 관리하면 빌드와 반복 작업 시간을 줄이는 데 도움이 된다.
- 코드 리뷰에서 형식보다 실제 동작과 설계에 집중할 수 있다.

한 번 정한 규칙은 새 코드에만 적용하고 끝내기보다, 수정하는 코드에도 같은 방향으로 적용하는 편이 좋다. 다만 형식만 바꾸는 대규모 수정은 실제 변경사항을 가릴 수 있으므로 기능 수정과 분리해서 진행하는 것이 안전하다.

---

<a id="class-organization"></a>

## 2. 클래스 선언 순서

클래스는 작성하는 사람보다 사용하는 사람이 읽기 쉽게 정리한다. 외부에서 먼저 확인할 public 영역을 위에 두고, protected와 private 구현을 그다음에 둔다.

```cpp
UCLASS()
class UNREALENGINELAB_API AMonster : public ACharacter
{
	GENERATED_BODY()

public:
	AMonster();

	void StartCombat();
	bool IsDead() const;

protected:
	virtual void BeginPlay() override;

private:
	void UpdateTarget();

	UPROPERTY()
	TObjectPtr<AActor> Target;

	float CurrentHealth = 100.f;
};
```

모든 멤버를 기계적으로 접근 지정자 순서에 맞추는 것보다, 관련 있는 함수와 데이터를 찾기 쉽게 묶는 것도 중요하다. 클래스가 너무 커져 어느 영역에 있는지 찾기 어렵다면 정렬 방식보다 책임 분리가 먼저 필요한 상황일 수 있다.

Epic이 공개 배포하는 소스 파일에는 정해진 저작권 문구가 필요하지만, 개인 프로젝트 파일에 Epic의 저작권 문구를 붙이라는 의미는 아니다. 프로젝트 소유권과 배포 정책에 맞는 문구를 사용한다.

---

<a id="naming"></a>

## 3. 이름 규칙

Unreal C++에서는 타입, 함수, 변수 이름에 PascalCase를 사용한다.

```cpp
float CurrentHealth;
int32 RemainingItemCount;
FVector LastKnownLocation;

void UpdateTarget();
bool CanAttack() const;
```

다음과 같은 이름은 피한다.

```cpp
float currentHealth;
int32 remaining_item_count;
void update_target();
```

이름은 짧은 것보다 역할이 분명한 것이 우선이다. 범위가 넓고 오래 유지되는 타입일수록 축약어보다 설명할 수 있는 이름이 필요하다.

```cpp
// 의미를 바로 알기 어렵다.
int32 Cnt;
void Proc();

// 역할이 드러난다.
int32 ActiveEnemyCount;
void RefreshEnemyList();
```

공식 표준은 코드와 주석에 미국식 영어 철자와 문법을 사용한다. 프로젝트에서 한글 주석을 사용하더라도 타입과 API 이름은 엔진 코드와 일관된 영어로 정하는 편이 검색과 협업에 유리하다.

---

<a id="type-prefixes"></a>

## 4. 타입 접두사

Unreal 타입은 종류를 구분할 수 있도록 접두사를 사용한다.

| 접두사 | 대상 | 예시 |
| --- | --- | --- |
| `A` | `AActor` 파생 클래스 | `AMonster` |
| `U` | `UObject` 파생 클래스 | `UHealthComponent` |
| `S` | `SWidget` 파생 클래스 | `SInventoryPanel` |
| `I` | 추상 Interface | `IInteractable` |
| `T` | Template 클래스 | `TArray`, `TAttribute` |
| `E` | Enum | `EMonsterState` |
| `C` | Concept와 비슷한 구조체 | `CStaticClassProvider` |
| `F` | 그 외 대부분의 클래스와 구조체 | `FVector`, `FAttackResult` |

Boolean 변수에는 `b`를 붙인다.

```cpp
bool bIsDead = false;
bool bCanAttack = true;
bool bPendingDestroy = false;
```

접두사는 꾸밈이 아니라 타입의 성격을 빠르게 파악하기 위한 정보다. 특히 `U`와 `A` 접두사는 Unreal Header Tool과도 연결되므로 임의로 바꾸지 않는다.

Template 매개변수와 내부 별칭을 구분해야 한다면 입력 타입에 `In`을 붙일 수 있다.

```cpp
template <typename InElementType>
class TContainer
{
public:
	using ElementType = InElementType;
};
```

---

<a id="functions-and-variables"></a>

## 5. 함수와 변수 이름

타입과 변수 이름은 명사로, 동작을 수행하는 함수는 효과가 드러나는 동사로 짓는다.

```cpp
FString PlayerName;
TArray<FItemData> InventoryItems;

void AddItem(const FItemData& Item);
void RemoveExpiredEffects();
```

Boolean을 반환하는 함수는 참이 무엇을 의미하는지 질문 형태로 드러내는 것이 좋다.

```cpp
// true가 무엇을 뜻하는지 모호하다.
bool CheckTarget() const;

// 반환값의 의미가 드러난다.
bool IsTargetValid() const;
bool CanAttack() const;
bool ShouldClearTarget() const;
```

함수가 출력 참조를 변경한다면 `Out` 접두사를 사용해 호출자에게 알려준다.

```cpp
bool TryFindTarget(AActor*& OutTarget) const;
void BuildPath(TArray<FVector>& OutPath) const;
```

Boolean 출력 매개변수라면 `bOutResult`처럼 `b`를 앞에 둔다.

변수는 한 줄에 하나씩 선언한다.

```cpp
int32 Width;
int32 Height;
```

한 줄 선언은 변수마다 의미를 설명하기 쉽고, 포인터나 참조 선언을 잘못 읽는 일도 줄여준다.

---

<a id="portable-types"></a>

## 6. 이식성을 고려한 타입

크기가 중요한 데이터에는 너비가 분명한 Unreal 타입을 사용한다.

| 타입 | 크기 |
| --- | ---: |
| `int8`, `uint8` | 1 byte |
| `int16`, `uint16` | 2 bytes |
| `int32`, `uint32` | 4 bytes |
| `int64`, `uint64` | 8 bytes |
| `float` | 4 bytes |
| `double` | 8 bytes |

`int`와 `unsigned int`는 너비가 중요하지 않은 일반 연산에는 사용할 수 있다. 다만 직렬화, Replication, 파일 형식, 네트워크 패킷처럼 크기가 약속의 일부라면 `int32`처럼 명시적인 타입을 사용한다.

`bool`과 `TCHAR`의 크기는 가정하지 않는다. 포인터를 담을 수 있는 정수가 필요하다면 `PTRINT`를 사용한다.

문자열 Literal은 `TEXT()`로 감싼다.

```cpp
const FString StateName = TEXT("Chase");
UE_LOG(LogTemp, Log, TEXT("Current state: %s"), *StateName);
```

---

<a id="const-correctness"></a>

## 7. const 정확성

`const`는 컴파일러를 위한 제한이면서 코드를 읽는 사람에게 변경 여부를 알려주는 문서다.

함수에서 수정하지 않을 객체는 const Pointer나 Reference로 받는다.

```cpp
void ApplyResult(const FAttackResult& Result);
```

객체 상태를 바꾸지 않는 멤버 함수에는 `const`를 붙인다.

```cpp
float GetCurrentHealth() const;
bool CanAttack() const;
```

Container를 수정하지 않는 반복문에서도 const Reference를 사용한다.

```cpp
for (const FItemData& Item : Items)
{
	DisplayItem(Item);
}
```

출력값을 변경하는 Reference에는 `Out` 이름을 함께 사용하면 입력과 출력이 더 분명해진다.

```cpp
void CalculateDamage(
	const FAttackData& AttackData,
	FDamageResult& OutResult
) const;
```

---

<a id="comments"></a>

## 8. 주석 작성

코드는 구현을 보여주고 주석은 의도와 제약을 설명한다.

이미 코드에 그대로 보이는 내용을 반복하지 않는다.

```cpp
// ItemCount를 1 증가시킨다.
++ItemCount;
```

왜 이런 처리가 필요한지 코드만으로 알기 어려울 때 주석이 도움이 된다.

```cpp
// 서버의 PresetIndex는 1부터 시작하므로 배열 접근 전에 보정한다.
const int32 ArrayIndex = PresetIndexFromServer - 1;
```

좋은 주석에는 다음 내용이 들어갈 수 있다.

- 클래스가 해결하는 문제와 만들어진 이유
- 함수의 목적과 호출자가 알아야 할 조건
- 매개변수의 단위, 범위, 유효하지 않은 값
- 반환값이나 오류 코드의 의미
- 외부 시스템 때문에 생긴 제약
- 변경할 때 주의할 점

공개 함수의 설명은 선언부에 한 번만 작성한다. 구현 과정의 세부사항은 필요한 위치의 구현 코드에 적는다.

주석과 코드가 다르면 주석도 버그가 된다. 동작을 바꿀 때 주석이 여전히 맞는지 함께 확인한다.

---

<a id="modern-cpp"></a>

## 9. Modern C++ 사용

Unreal Engine 5.8은 기본적으로 C++20을 사용하며, Engine을 빌드하려면 최소 C++20이 필요하다. 그렇다고 지원되는 모든 문법을 프로젝트에서 자유롭게 사용한다는 뜻은 아니다. 여러 컴파일러와 엔진 관례를 함께 고려해야 한다.

### override와 final

가상 함수를 재정의할 때는 `override`를 사용한다. 상속을 허용하지 않는 타입이나 함수에는 `final`을 검토한다.

```cpp
void BeginPlay() override;
void Tick(float DeltaTime) override;

class FFinalProcessor final : public IProcessor
{
};
```

### nullptr

C 스타일 `NULL` 대신 `nullptr`를 사용한다.

```cpp
AActor* Target = nullptr;
```

### auto

공식 표준은 타입이 독자에게 보이도록 `auto` 사용을 제한한다. 다음 경우처럼 타입을 직접 쓰기 어렵거나 오히려 가독성을 떨어뜨릴 때 사용할 수 있다.

- Lambda를 변수에 저장할 때
- Iterator 타입이 지나치게 길 때
- 표현식 타입을 쉽게 적을 수 없는 Template 코드

```cpp
const auto IsAlive = [](const AActor* Actor)
{
	return IsValid(Actor) && !Actor->IsActorBeingDestroyed();
};
```

C++20 Structured Binding도 사실상 여러 `auto`를 만드는 문법이므로 Epic 표준에서는 사용하지 않는다.

### Range-based for

Container 순회는 범위 기반 for를 우선한다.

```cpp
for (const TPair<FName, int32>& Pair : ItemCounts)
{
	UE_LOG(
		LogTemp,
		Log,
		TEXT("%s: %d"),
		*Pair.Key.ToString(),
		Pair.Value
	);
}
```

### Strongly-typed enum

기존 방식보다 `enum class`를 사용한다. Blueprint에 노출하는 Enum의 기반 타입은 `uint8`로 둔다.

```cpp
UENUM(BlueprintType)
enum class EMonsterState : uint8
{
	Idle,
	Chase,
	Attack,
	Dead
};
```

### Move semantics

`TArray`, `TMap`, `TSet`, `FString` 등은 Move를 지원한다. 소유권을 넘길 때는 `MoveTemp`를 사용할 수 있다.

```cpp
void FInventory::SetItems(TArray<FItemData> InItems)
{
	Items = MoveTemp(InItems);
}
```

Deferred Lambda에서 Reference나 UObject Pointer를 무심코 Capture하면 수명 문제가 생길 수 있다. `CreateWeakLambda`, `TWeakObjectPtr`처럼 수명을 확인할 수 있는 방식을 사용하고, 자동 Capture보다 필요한 값을 명시하는 편이 안전하다.

---

<a id="formatting"></a>

## 10. 코드 형식

### 중괄호

중괄호는 새 줄에 두고, 본문이 한 줄이어도 생략하지 않는다.

```cpp
if (bCanAttack)
{
	StartAttack();
}
else
{
	MoveToTarget();
}
```

다음과 같이 한 줄로 합치지 않는다.

```cpp
if (bCanAttack) StartAttack();
```

중괄호를 항상 사용하면 조건문에 코드를 추가할 때 실수로 조건 밖에 놓는 일을 줄일 수 있다.

### 들여쓰기

실행 Block 단위로 들여쓴다. 줄 시작의 들여쓰기는 Tab을 사용하고 Tab 크기는 4칸으로 설정한다. Tab이 아닌 문자 뒤의 내용을 맞출 때는 Space를 사용할 수 있다.

### switch

각 `case`는 `break`, `return`, `continue`처럼 흐름이 끝나는 지점을 명확히 표시한다. 의도적으로 다음 `case`로 이어진다면 주석으로 밝힌다. `default`도 항상 둔다.

```cpp
switch (State)
{
case EMonsterState::Idle:
	StopMovement();
	break;

case EMonsterState::Chase:
	StartChasing();
	break;

case EMonsterState::Attack:
	StartAttack();
	return;

default:
	break;
}
```

### 그 외 확인할 것

- 함수 이름과 여는 괄호 사이에 Space를 넣지 않는다.
- 컴파일러 Warning은 가능한 한 원인을 수정한다.
- `#pragma`로 Warning을 숨기는 것은 마지막 수단으로 둔다.
- `.h`와 `.cpp` 파일 마지막에는 빈 줄을 둔다.
- 정리되지 않은 Debug 코드는 Commit하지 않는다.
- 복잡한 조건은 의미 있는 중간 변수로 나눈다.

---

<a id="namespaces"></a>

## 11. Namespace와 Macro

Unreal Header Tool은 Namespace 안의 `UCLASS`, `USTRUCT` 같은 Reflected Type을 지원하지 않는다.

```cpp
// Reflected Type은 전역 범위에서 선언한다.
USTRUCT()
struct FAttackResult
{
	GENERATED_BODY()
};
```

Reflected Type이 아닌 새 API는 `UE::` 아래에 프로젝트나 기능 Namespace를 둘 수 있다.

```cpp
namespace UE::UnrealEngineLab
{
	class FDamageCalculator
	{
	};
}
```

외부에 노출하지 않을 구현 세부사항은 `Private` Namespace로 구분할 수 있다.

```cpp
namespace UE::UnrealEngineLab::Private
{
	int32 CalculateInternalScore();
}
```

전역 범위에 `using namespace`나 `using` 선언을 두지 않는다. Unity Build에서 다른 코드에 영향을 줄 수 있다.

Macro는 Namespace에 넣을 수 없으므로 전체 대문자와 밑줄을 사용하고 `UE_` 접두사를 붙인다.

```cpp
#define UE_UNREALENGINELAB_TRACE_COMBAT 1
```

---

<a id="dependencies"></a>

## 12. Header와 물리적 의존성

모든 Header는 `#pragma once`로 중복 Include를 막는다.

```cpp
#pragma once
```

Pointer나 Reference 선언만 필요하다면 Forward Declaration을 먼저 고려한다.

```cpp
// Monster.h
class UCombatComponent;

UCLASS()
class AMonster : public ACharacter
{
	GENERATED_BODY()

private:
	UPROPERTY()
	TObjectPtr<UCombatComponent> CombatComponent;
};
```

실제 멤버 함수를 사용하는 `.cpp`에서 Header를 Include한다.

```cpp
// Monster.cpp
#include "Monster.h"

#include "CombatComponent.h"
```

다만 상속하거나 값을 직접 보관하는 타입처럼 완전한 정의가 필요한 경우에는 Header를 Include해야 한다.

Unreal의 Include What You Use 방향은 다음과 같다.

- 각 Header는 자신이 컴파일되는 데 필요한 의존성을 직접 Include한다.
- 다른 Header가 우연히 Include해준 파일에 의존하지 않는다.
- `.cpp`는 자신과 짝인 `.h`를 먼저 Include한다.
- `Core.h` 같은 큰 Header 대신 필요한 Header를 세밀하게 Include한다.
- 외부 Module에 필요한 선언만 `Public`에 두고 나머지는 `Private`에 둔다.

Header 의존성을 줄이는 이유는 형식 때문만이 아니다. 자주 바뀌는 Header가 넓게 Include되면 작은 수정도 많은 파일을 다시 Build하게 만든다.

---

<a id="encapsulation"></a>

## 13. 캡슐화와 클래스 크기

멤버 변수는 public이나 protected Interface의 일부가 아니라면 private으로 둔다.

```cpp
class FHealth
{
public:
	float GetCurrentHealth() const
	{
		return CurrentHealth;
	}

	void ApplyDamage(float Damage);

private:
	float CurrentHealth = 100.f;
};
```

파생 클래스에서만 사용할 값도 무조건 protected 변수로 열기보다 private 상태와 protected Accessor를 제공하는 방법을 검토한다. 나중에 내부 표현을 바꿀 때 파생 클래스까지 한꺼번에 깨지는 일을 줄일 수 있다.

상속을 목적으로 만들지 않은 클래스에는 `final`을 사용한다.

큰 함수는 의미 있는 하위 함수로 나눈다. 하지만 한 줄짜리 함수를 많이 만드는 것이 목적은 아니다. 호출 순서를 읽는 것만으로 전체 흐름을 파악할 수 있고, 세부 구현은 필요할 때 내려가 볼 수 있게 만드는 것이 좋다.

```cpp
void AMonster::HandleDeath()
{
	StopCombat();
	ClearStatusEffects();
	DisableMovement();
	NotifyDeath();
}
```

`FORCEINLINE`과 지나치게 많은 Inline 함수는 신중하게 사용한다. Header의 구현이 바뀔 때 다시 Build해야 하는 범위를 넓힐 수 있으므로, 성능상 필요하다는 근거가 있는지 확인한다.

---

<a id="standard-library"></a>

## 14. 표준 라이브러리 사용

Unreal이 표준 라이브러리를 전부 금지하는 것은 아니다. 같은 기능을 제공한다면 결과와 기존 코드의 일관성을 비교해 선택한다.

공식 표준은 다음 표준 기능의 사용 방향을 따로 설명한다.

| 기능 | 방향 |
| --- | --- |
| `<atomic>` | 새 코드에서는 표준 Atomic 사용 |
| `<type_traits>` | Unreal Trait과 겹치면 표준 Trait 사용 |
| `<initializer_list>` | Braced Initializer 지원에 사용 |
| `<limits>` | 전체 사용 가능 |
| `<cmath>` | 부동소수점 함수 사용 가능 |
| `<regex>` | Editor 전용 코드 안에 캡슐화해서 사용 |

Unreal API와 표준 라이브러리 방식을 하나의 공개 API에서 섞으면 호출자가 두 관례를 모두 알아야 한다. 프로젝트의 Gameplay 코드에서는 `TArray`, `TMap`, `FString` 같은 Unreal 타입을 기본으로 사용하고, 외부 라이브러리와 연결하는 경계에서는 변환 위치를 분명하게 두는 편이 관리하기 쉽다.

표준 Container와 String은 Interop 코드가 아니라면 피하는 것이 Epic 표준의 기본 방향이다.

---

<a id="checklist"></a>

## 15. 리뷰할 때 확인할 것

### 이름

- 타입과 함수, 변수에 PascalCase를 사용했는가?
- Unreal 타입 접두사가 실제 상속 관계와 맞는가?
- Boolean 변수에 `b`를 붙였는가?
- Boolean 반환 함수의 참 의미가 이름에 드러나는가?
- 출력 매개변수에 `Out`을 표시했는가?
- 지나친 축약어나 모호한 동사를 사용하지 않았는가?

### 타입과 C++

- 크기가 중요한 데이터에 명시적 크기 타입을 사용했는가?
- 문자열 Literal에 `TEXT()`를 사용했는가?
- 수정하지 않는 값과 함수에 `const`를 적용했는가?
- 가상 함수 재정의에 `override`를 붙였는가?
- `NULL` 대신 `nullptr`를 사용했는가?
- `auto`를 쓴 이유가 타입을 감추는 비용보다 분명한가?
- Deferred Lambda의 Capture 대상 수명이 안전한가?

### 형식

- 중괄호를 새 줄에 두고 한 줄 Block에도 사용했는가?
- 줄 시작 들여쓰기에 Tab을 사용했는가?
- `switch`의 흐름과 `default`가 분명한가?
- 파일 마지막에 빈 줄이 있는가?
- Compiler Warning과 임시 Debug 코드를 정리했는가?

### 의존성과 구조

- Header가 필요한 의존성을 직접 Include하는가?
- Forward Declaration으로 충분한 타입을 불필요하게 Include하지 않았는가?
- `.cpp`가 자신의 Header를 먼저 Include하는가?
- 외부 Module에 필요하지 않은 선언이 `Public`에 노출되지 않았는가?
- 멤버 상태가 필요 이상으로 public이나 protected에 열려 있지 않은가?
- 큰 함수와 복잡한 조건을 의미 있는 단위로 읽을 수 있는가?

---

<a id="summary"></a>

## 16. 정리

자주 확인하는 규칙만 줄이면 다음과 같다.

```text
이름
PascalCase와 Unreal 타입 접두사를 사용한다.

Boolean
b 접두사를 붙이고 함수 이름은 참의 의미를 드러낸다.

타입
크기가 중요한 데이터에는 int32 같은 명시적 타입을 사용한다.

const
바꾸지 않는 값과 함수는 변경하지 않는다는 사실을 코드에 표시한다.

형식
중괄호는 새 줄에 두고 한 줄 Block에도 생략하지 않는다.

Modern C++
override, final, nullptr, enum class를 사용하고 auto는 제한한다.

Header
필요한 Header만 직접 Include하고 가능한 곳은 Forward Declaration을 사용한다.

주석
코드의 동작을 반복하기보다 의도와 제약을 설명한다.
```

코딩 표준을 지키는 이유는 규칙 자체가 목적이어서가 아니다. 엔진 코드와 프로젝트 코드를 같은 방식으로 읽고, 시간이 지난 뒤에도 수정 범위와 의도를 빠르게 파악하기 위해서다.

세부 규칙은 Engine 버전에 따라 달라질 수 있으므로 애매한 부분은 [Epic 공식 C++ 코딩 표준](https://dev.epicgames.com/documentation/unreal-engine/epic-cplusplus-coding-standard-for-unreal-engine?application_version=5.8)에서 다시 확인한다.

---

[목차로 돌아가기](#contents) · [메인 README의 CS 목차로 돌아가기](../../README.md#cs)
