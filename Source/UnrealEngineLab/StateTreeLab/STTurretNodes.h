// StateTree 학습용 샘플 노드 - Global Task / Condition / Task.

#pragma once

#include "CoreMinimal.h"
#include "StateTreeConditionBase.h"
#include "StateTreeTaskBase.h"
#include "STTurretNodes.generated.h"

class AActor;

// ---------------------------------------------------------------------------
// Global Task - 사격 대상을 찾아 트리 전체에 노출한다.
// ---------------------------------------------------------------------------

USTRUCT()
struct FSTFindTargetTaskInstanceData
{
	GENERATED_BODY()

	/** 찾아낸 대상. 다른 노드들이 여기에 바인딩해서 가져다 쓴다. */
	UPROPERTY(EditAnywhere, Category = "Output")
	TObjectPtr<AActor> Target = nullptr;
};

/**
 * 플레이어 폰을 찾아 Target 으로 내보낸다.
 *
 * 에셋 디테일의 Global Tasks 에 넣으면 트리가 살아 있는 동안 계속 실행된다.
 * 같은 자리에 Evaluator 도 넣을 수 있지만, Epic 은 Global Task 쪽으로 정리하는 중이다.
 *
 * 절대 Succeeded 를 돌려주면 안 된다. 활성 상태의 Task 가 하나라도 끝나면
 * StateTree 는 전환을 시도하고, 글로벌 Task 가 끝나면 트리 전체가 끝난다.
 */
USTRUCT(meta = (DisplayName = "Find Player Target", Category = "Turret"))
struct FSTFindTargetTask : public FStateTreeTaskCommonBase
{
	GENERATED_BODY()

	using FInstanceDataType = FSTFindTargetTaskInstanceData;

	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
	virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const override;
};

// ---------------------------------------------------------------------------
// Condition - 대상이 사거리 안에 있는지 본다.
// ---------------------------------------------------------------------------

USTRUCT()
struct FSTTargetInRangeConditionInstanceData
{
	GENERATED_BODY()

	/** 이름과 타입이 스키마의 Context 와 맞으면 에디터가 알아서 연결해 준다. */
	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AActor> Actor = nullptr;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<AActor> Target = nullptr;

	UPROPERTY(EditAnywhere, Category = "Parameter", meta = (ClampMin = "0.0"))
	float Range = 1500.f;
};

/**
 * Actor 와 Target 사이 거리가 Range 이하인지 검사한다.
 *
 * Enter Condition 으로 쓰면 "이 상태에 들어갈 수 있는가"를,
 * Transition 조건으로 쓰면 "이 상태에서 나가야 하는가"를 판단한다.
 * 같은 노드가 두 자리 모두에 들어간다.
 */
USTRUCT(meta = (DisplayName = "Target In Range", Category = "Turret"))
struct FSTTargetInRangeCondition : public FStateTreeConditionCommonBase
{
	GENERATED_BODY()

	using FInstanceDataType = FSTTargetInRangeConditionInstanceData;

	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual bool TestCondition(FStateTreeExecutionContext& Context) const override;

	/** 조건을 뒤집는다. "사거리 밖으로 벗어났는가"를 물을 때 쓴다. */
	UPROPERTY(EditAnywhere, Category = "Condition")
	bool bInvert = false;
};

// ---------------------------------------------------------------------------
// Task - 조준
// ---------------------------------------------------------------------------

USTRUCT()
struct FSTAimAtTargetTaskInstanceData
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AActor> Actor = nullptr;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<AActor> Target = nullptr;

	UPROPERTY(EditAnywhere, Category = "Parameter", meta = (ClampMin = "1.0"))
	float DegreesPerSecond = 120.f;

	/** 남은 각도가 이 값 이하가 되면 조준 완료로 본다. */
	UPROPERTY(EditAnywhere, Category = "Parameter", meta = (ClampMin = "0.1"))
	float AngleTolerance = 5.f;
};

/**
 * 터렛 머리를 Target 쪽으로 돌린다. 조준이 끝나면 Succeeded 를 반환한다.
 *
 * Task 구조체 자체에는 실행 중 바뀌는 값을 두지 않는다.
 * 모든 콜백이 const 인 이유이고, 상태는 전부 InstanceData 에 들어간다.
 */
USTRUCT(meta = (DisplayName = "Aim At Target", Category = "Turret"))
struct FSTAimAtTargetTask : public FStateTreeTaskCommonBase
{
	GENERATED_BODY()

	using FInstanceDataType = FSTAimAtTargetTaskInstanceData;

	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
	virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const override;
};

// ---------------------------------------------------------------------------
// Task - 발사
// ---------------------------------------------------------------------------

USTRUCT()
struct FSTFireTaskInstanceData
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AActor> Actor = nullptr;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<AActor> Target = nullptr;

	UPROPERTY(EditAnywhere, Category = "Parameter", meta = (ClampMin = "1"))
	int32 ShotCount = 3;

	UPROPERTY(EditAnywhere, Category = "Parameter", meta = (ClampMin = "0.0"))
	float Interval = 0.25f;

	// 여기부터는 실행 중에만 쓰는 값이라 에디터에 노출하지 않는다.
	int32 ShotsFired = 0;
	float TimeSinceLastShot = 0.f;
};

/**
 * Interval 간격으로 ShotCount 발을 쏘고 Succeeded 로 끝난다.
 *
 * 상태가 다시 선택될 때마다 EnterState 에서 카운터를 0 으로 되돌린다.
 * 이 초기화를 빼먹으면 두 번째 사격부터 바로 끝나 버린다.
 */
USTRUCT(meta = (DisplayName = "Fire Burst", Category = "Turret"))
struct FSTFireTask : public FStateTreeTaskCommonBase
{
	GENERATED_BODY()

	using FInstanceDataType = FSTFireTaskInstanceData;

	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
	virtual EStateTreeRunStatus Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const override;
};

// ---------------------------------------------------------------------------
// Task - 과열 해제
// ---------------------------------------------------------------------------

USTRUCT()
struct FSTResetHeatTaskInstanceData
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Context")
	TObjectPtr<AActor> Actor = nullptr;
};

/**
 * 누적 사격 수를 0 으로 되돌린다. EnterState 한 번으로 끝나는 Task 다.
 * Tick 이 필요 없으면 bShouldCallTick 을 꺼서 매 프레임 호출을 막는다.
 */
USTRUCT(meta = (DisplayName = "Reset Heat", Category = "Turret"))
struct FSTResetHeatTask : public FStateTreeTaskCommonBase
{
	GENERATED_BODY()

	using FInstanceDataType = FSTResetHeatTaskInstanceData;

	FSTResetHeatTask();

	virtual const UStruct* GetInstanceDataType() const override { return FInstanceDataType::StaticStruct(); }
	virtual EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const override;
};
