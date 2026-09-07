# 객체지향 프로그래밍

<a id="contents"></a>

## 목차

1. [객체지향 프로그래밍이란?](#oop)
2. [캡슐화](#encapsulation)
3. [추상화](#abstraction)
4. [상속](#inheritance)
5. [다형성](#polymorphism)
6. [네 가지 특징 한눈에 보기](#overview)
7. [Unreal Engine과 연결해서 보면](#unreal)
8. [정리](#summary)
9. [내가 중요하게 생각하는 객체지향의 특징](#my-perspective)

---

<a id="oop"></a>

## 1. 객체지향 프로그래밍이란?

객체지향 프로그래밍(OOP, Object-Oriented Programming)은 프로그램을 여러 객체로 나누고, 각 객체가 자신의 데이터와 기능을 가지며 서로 협력하도록 설계하는 방식이다.

게임으로 보면 다음처럼 역할을 나눠 생각할 수 있다.

```text
Character
- HP
- AttackPower
- Move()
- Attack()

Inventory
- ItemList
- AddItem()
- RemoveItem()

Quest
- Progress
- UpdateQuest()
```

각 객체는 자신이 관리해야 할 상태와 그 상태를 다루는 기능을 가진다. 객체지향의 핵심은 단순히 클래스를 많이 만드는 것이 아니다.

> **어떤 객체가 어떤 책임을 가져야 하는지 나누고, 객체끼리 어떻게 관계를 맺을지 설계하는 것**

이 중요하다.

---

<a id="encapsulation"></a>

## 2. 캡슐화

**Encapsulation**

캡슐화는 객체의 데이터와 기능을 하나로 묶고, 외부에서 내부 상태를 마음대로 변경하지 못하도록 필요한 부분만 공개하는 것이다.

```cpp
class FCharacter
{
public:
    void TakeDamage(int32 Damage)
    {
        if (Damage <= 0)
        {
            return;
        }

        HP = FMath::Max(0, HP - Damage);
    }

    int32 GetHP() const
    {
        return HP;
    }

private:
    int32 HP = 100;
};
```

외부에서 `HP`를 직접 바꾸는 대신 정해진 함수를 통해 상태를 변경한다.

```cpp
Character.TakeDamage(10);
```

이렇게 하면 대미지 검증이나 최소 체력 보장 같은 규칙을 객체 안에서 일관되게 관리할 수 있다.

### 캡슐화의 목적

- 잘못된 데이터 변경을 방지한다.
- 객체가 자신의 상태와 규칙을 관리한다.
- 내부 구현이 바뀌어도 외부에 미치는 영향을 줄인다.
- 외부에는 사용에 필요한 기능만 보여준다.

쉽게 말하면 다음과 같다.

> **내 데이터와 규칙은 내가 관리한다.**

---

<a id="abstraction"></a>

## 3. 추상화

**Abstraction**

추상화는 구체적인 세부사항을 모두 드러내기보다, 객체를 사용하는 데 필요한 중요한 특징과 공통 역할을 뽑아 표현하는 것이다.

예를 들어 전사, 마법사, 궁수는 공격 방식이 서로 다르다.

```text
Warrior → 검으로 공격
Mage    → 마법으로 공격
Archer  → 활로 공격
```

구체적인 방식은 다르지만 모두 **공격할 수 있는 캐릭터**라는 공통 역할을 가진다.

```cpp
class FCharacter
{
public:
    virtual ~FCharacter() = default;
    virtual void Attack() = 0;
};
```

이 클래스는 어떻게 공격하는지까지 정하지 않는다. 캐릭터라면 `Attack()`이라는 기능을 제공해야 한다는 중요한 개념만 표현한다.

> **구체적인 세부사항은 감추고, 사용하는 쪽에 필요한 개념을 드러낸다.**

추상화는 추상 클래스만을 의미하지 않는다. 인터페이스나 잘 설계된 함수도 불필요한 세부사항을 숨기고 필요한 기능만 제공한다면 추상화의 한 방법이 될 수 있다.

---

<a id="inheritance"></a>

## 4. 상속

**Inheritance**

상속은 기존 클래스의 데이터와 기능을 자식 클래스가 물려받아 재사용하거나 확장하는 것이다.

```cpp
class FCharacter
{
public:
    void Move();
};

class FWarrior : public FCharacter
{
public:
    void UseSword();
};
```

`FWarrior`는 `FCharacter`의 `Move()`를 사용할 수 있고, 자신만의 `UseSword()`도 추가할 수 있다.

```text
Character
├─ Warrior
├─ Mage
└─ Archer
```

쉽게 말하면 다음과 같다.

> **공통적인 것은 부모에 두고, 자식은 부모의 특성을 물려받아 확장한다.**

다만 공통 코드가 있다는 이유만으로 상속 관계를 만드는 것은 피하는 편이 좋다. 자식이 부모의 한 종류라고 자연스럽게 말할 수 있고 부모가 보장한 동작을 지킬 수 있는지 먼저 확인해야 한다.

기능을 조합하거나 실행 중에 바꿔야 한다면 상속보다 Composition이 더 잘 맞을 수 있다.

```text
Character
├─ HealthComponent
├─ InventoryComponent
└─ AbilityComponent
```

---

<a id="polymorphism"></a>

## 5. 다형성

**Polymorphism**

다형성은 같은 인터페이스나 부모 타입을 통해 호출하더라도 실제 객체에 따라 다른 동작이 실행되는 성질이다.

```cpp
class FCharacter
{
public:
    virtual ~FCharacter() = default;
    virtual void Attack() = 0;
};

class FWarrior : public FCharacter
{
public:
    void Attack() override
    {
        // 검 공격
    }
};

class FMage : public FCharacter
{
public:
    void Attack() override
    {
        // 마법 공격
    }
};
```

사용하는 쪽은 구체적인 캐릭터 종류를 알지 않아도 부모 타입을 통해 같은 방식으로 호출할 수 있다.

```cpp
void PerformAttack(FCharacter& Character)
{
    Character.Attack();
}
```

하지만 실제로 전달된 객체에 따라 결과는 달라진다.

```text
Warrior → 검 공격
Mage    → 마법 공격
```

> **같은 요청을 보내도 실제 객체에 따라 다르게 행동한다.**

호출하는 코드는 `Warrior`, `Mage` 같은 구체 타입마다 분기하지 않아도 된다. 부모가 약속한 인터페이스를 지키는 새로운 캐릭터가 추가되어도 같은 코드를 이용할 수 있다.

---

<a id="overview"></a>

## 6. 네 가지 특징 한눈에 보기

| 특징 | 의미 | 확인할 질문 |
| --- | --- | --- |
| **캡슐화** | 내부 상태와 규칙을 객체가 관리하고 필요한 기능만 공개한다. | 외부에서 이 객체의 상태를 마음대로 바꿀 수 있는가? |
| **추상화** | 세부사항을 감추고 사용하는 데 필요한 개념을 표현한다. | 사용하는 쪽이 불필요한 구현까지 알아야 하는가? |
| **상속** | 부모의 특성을 자식이 물려받아 확장한다. | 자식을 부모의 한 종류라고 자연스럽게 볼 수 있는가? |
| **다형성** | 같은 호출이 실제 객체에 따라 다르게 동작한다. | 구체 타입을 몰라도 공통된 방식으로 사용할 수 있는가? |

네 특징은 서로 완전히 떨어진 개념이 아니다. 추상화한 공통 역할을 상속이나 인터페이스로 표현하고, 내부 상태는 캡슐화하며, 사용하는 쪽에서는 다형성을 통해 여러 구현을 같은 방식으로 다룰 수 있다.

---

<a id="unreal"></a>

## 7. Unreal Engine과 연결해서 보면

### 캡슐화

Actor나 Component가 자신의 상태를 직접 관리하고, 외부에는 상태를 바꾸기 위한 함수나 필요한 읽기 기능만 제공한다.

```text
HealthComponent
├─ CurrentHealth
├─ ApplyDamage()
└─ GetCurrentHealth()
```

### 추상화

`UInterface`, 추상 클래스, 함수 API를 이용해 사용하는 쪽에 필요한 역할만 보여줄 수 있다.

```text
IInteractable
└─ Interact()
```

### 상속

`AActor`, `APawn`, `ACharacter`, `UUserWidget` 같은 엔진 클래스를 기반으로 프로젝트에 필요한 타입을 확장한다. 상속 계층이 깊어지거나 선택 기능이 부모에 계속 쌓인다면 Component 구성을 함께 검토할 수 있다.

### 다형성

부모 클래스의 가상 함수나 `UInterface` 메시지를 이용하면 호출하는 쪽이 구체 클래스를 직접 알지 않아도 객체마다 다른 동작을 실행할 수 있다.

```text
InteractionSystem
        ↓ Interact()
Door / NPC / Chest
```

---

<a id="summary"></a>

## 8. 정리

> **객체지향 프로그래밍은 프로그램을 객체 단위로 나누고, 각 객체가 자신의 상태와 책임을 가지며 서로 협력하도록 설계하는 방식이다.**

대표적인 특징은 캡슐화, 추상화, 상속, 다형성이다.

```text
캡슐화
→ 내부 상태와 규칙을 객체가 관리한다.

추상화
→ 중요한 개념을 드러내고 불필요한 세부사항은 감춘다.

상속
→ 자연스러운 부모·자식 관계에서 공통 특성을 물려받아 확장한다.

다형성
→ 공통된 방식으로 요청하고 실제 객체에 따라 다르게 동작한다.
```

이 특징들을 적용하는 목적은 형식적으로 클래스를 나누는 것이 아니라, 각 객체의 책임과 관계를 이해하기 쉽게 만들고 변경에 유연한 구조를 만드는 데 있다.

---

<a id="my-perspective"></a>

## 9. 내가 중요하게 생각하는 객체지향의 특징

저는 객체지향의 4가지 특징 중에서 **다형성이 가장 객체지향다운 특징이라고 생각합니다.**

객체지향은 결국 서로 다른 객체들이 각자의 역할을 가지면서도 공통된 방식으로 협력할 수 있게 설계하는 것이 중요하다고 생각하는데, 다형성이 그 부분을 가장 잘 보여준다고 봅니다.

같은 인터페이스나 부모 타입으로 여러 객체를 다룰 수 있고, 실제 객체에 따라 서로 다른 동작을 수행할 수 있기 때문에 코드의 확장성과 유연성이 좋아집니다. 새로운 객체가 추가되더라도 기존 코드를 크게 수정하지 않고 기능을 확장할 수 있다는 점에서, 저는 다형성을 **객체지향의 꽃**이라고 생각합니다.

---

[목차로 돌아가기](#contents) · [메인 README의 CS 목차로 돌아가기](../../README.md#cs)
