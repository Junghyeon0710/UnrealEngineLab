// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Templates/SubclassOf.h"
#include "AnimBudgetTestSpawner.generated.h"

class UAnimInstance;
class USkeletalMesh;
class USkeletalMeshComponentBudgeted;

/**
 * Animation Budget Allocator를 일정하고 재현 가능한 부하로 측정하기 위해
 * budgeted 스켈레탈 메시를 격자로 스폰하는 테스트 액터.
 *
 * allocator는 아래 두 조건이 모두 참일 때만 동작한다:
 *   - 전역 CVar a.Budget.Enabled 가 1
 *   - 월드별 플래그가 켜짐 (여기서는 bEnableBudgetOnBeginPlay, 또는 AnimBudgetTest.Enable 1)
 *
 * 이 액터가 등록하는 콘솔 명령:
 *   AnimBudgetTest.Enable <0|1>     월드별 allocator 토글
 *   AnimBudgetTest.Spawn <GridSize> 격자를 지정 크기로 재생성
 *   AnimBudgetTest.Clear            스폰한 컴포넌트 전부 제거
 *   AnimBudgetTest.Report           컴포넌트 수 / reduced work 수 / 거리대별 틱 비율 로그 출력
 */
UCLASS()
class UNREALENGINELAB_API AAnimBudgetTestSpawner : public AActor
{
	GENERATED_BODY()

public:
	/** LogReport가 컴포넌트를 거리순으로 나눠 담는 구간 수. */
	static constexpr int32 NumDistanceBuckets = 4;

	AAnimBudgetTestSpawner();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	/** 격자를 다시 만든다. 이전에 스폰한 컴포넌트는 모두 파괴된다. */
	void SpawnGrid(int32 InGridSize);

	/** 이 액터가 스폰한 컴포넌트를 전부 파괴한다. */
	void ClearGrid();

	/** 지난 리포트 이후 모인 수치를 로그로 남기고 측정 구간을 초기화한다. */
	void LogReport();

	/** 격자 한 칸마다 사용할 스켈레탈 메시. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	TObjectPtr<USkeletalMesh> TestMesh;

	/** 스폰한 모든 컴포넌트에 적용할 애님 블루프린트. 비워두면 애니메이션 부하 없이 스폰된다. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	TSubclassOf<UAnimInstance> TestAnimInstance;

	/** GridSize x GridSize 정사각형으로 스폰하므로 총 개수는 GridSize의 제곱이다. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "1", ClampMax = "100"))
	int32 GridSize = 20;

	/** 격자 칸 사이 간격 (cm). */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "1.0"))
	float GridSpacing = 150.0f;

	/** BeginPlay에서 월드별 allocator를 켠다. 실제로 동작하려면 a.Budget.Enabled도 1이어야 한다. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bEnableBudgetOnBeginPlay = true;

	/** 각 컴포넌트가 플레이어 시점과의 거리로 significance를 스스로 계산하게 한다. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bAutoCalculateSignificance = true;

	/**
	 * 모든 컴포넌트에 OnReduceWork를 바인드한다. allocator는 델리게이트가 바인드된 컴포넌트에만
	 * reduced work를 적용하므로, 끄면 틱 레이트 스로틀링과 보간까지만 테스트된다.
	 */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bBindReduceWork = true;

	/**
	 * 스폰한 컴포넌트에 bTickEvenIfNotRendered 를 설정한다.
	 *
	 * allocator의 오프스크린 처리(a.Budget.MaxTickedOffsreen)는 이 플래그가 켜진 컴포넌트에만
	 * 적용된다. 꺼져 있으면 렌더되지 않는 컴포넌트는 아예 틱하지 않는다.
	 */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bTickEvenIfNotRendered = false;

	/** 자동 리포트 간격(초). 0이면 주기적 로그를 끈다. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "0.0"))
	float ReportIntervalSeconds = 0.0f;

	/**
	 * BeginPlay에서, 격자를 스폰하기 직전에 실행할 콘솔 명령들.
	 *
	 * PIE로 시나리오를 돌릴 때 콘솔을 직접 치지 않고 레벨에 저장된 값만으로 CVar를 세팅하기 위한 것.
	 * 예: "a.Budget.BudgetMs 0.25", "a.Budget.MaxTickedOffsreen 32"
	 */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	TArray<FString> StartupConsoleCommands;

private:
	/** 컴포넌트의 작업량을 늘리거나 줄여야 할 때 allocator가 호출한다. */
	void HandleReduceWork(USkeletalMeshComponentBudgeted* InComponent, bool bReduce);

	/** 첫 번째 플레이어 시점 위치를 구한다. 플레이어가 없으면 false. */
	bool GetPlayerViewLocation(FVector& OutViewLocation) const;

	/** SpawnGrid가 만든 컴포넌트들. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<USkeletalMeshComponentBudgeted>> SpawnedComponents;

	/** 컴포넌트별 누적 포즈 평가 횟수. SpawnedComponents와 인덱스가 1:1로 대응한다. */
	TArray<int32> PerComponentPoseTicks;

	/** 현재 allocator가 reduced work 상태로 두고 있는 컴포넌트 수. */
	int32 NumReducedWorkComponents = 0;

	/** 지난 리포트 이후 매 프레임의 포즈 평가 컴포넌트 수를 누적한 값. */
	int64 PoseTickAccumulator = 0;

	/** PoseTickAccumulator에 반영된 프레임 수. */
	int32 FramesSinceReport = 0;

	/** 다음 주기 리포트까지 남은 시간. */
	float TimeUntilNextReport = 0.0f;

	/** SpawnGrid마다 증가시켜 재생성 시 컴포넌트 이름이 겹치지 않게 한다. */
	int32 SpawnGeneration = 0;

	/**
	 * significance 플래그를 아직 컴포넌트에 밀어넣지 못했는지 여부.
	 *
	 * 월드 BeginPlay 도중에 스폰하면 컴포넌트가 allocator에 '지연 등록'되고, 그동안
	 * SetComponentSignificance는 경고만 남기고 무시된다. 그래서 첫 Tick으로 미룬다.
	 */
	bool bSignificanceFlagsPending = false;
};
