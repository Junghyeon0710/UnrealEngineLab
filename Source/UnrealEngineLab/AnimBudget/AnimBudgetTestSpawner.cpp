// Copyright Epic Games, Inc. All Rights Reserved.

#include "AnimBudgetTestSpawner.h"

#include "Animation/AnimInstance.h"
#include "Components/SceneComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "IAnimationBudgetAllocator.h"
#include "ProfilingDebugging/CsvProfiler.h"
#include "SkeletalMeshComponentBudgeted.h"

DEFINE_LOG_CATEGORY_STATIC(LogAnimBudgetTest, Log, All);

// allocator가 내보내는 NumTicked/AnimQuality CSV 스탯은 WITH_TICK_DEBUG 빌드에서만 컴파일되므로,
// 이 테스트는 같은 값을 PoseTickedThisFrame()으로 직접 세어 자체 카테고리로 내보낸다.
CSV_DEFINE_CATEGORY(AnimBudgetTest, true);

namespace AnimBudgetTest
{
	/**
	 * 월드별 allocator를 반환한다. 없으면 null.
	 * IAnimationBudgetAllocator::Get은 월드가 null이면 assert하고 게임 월드에만 allocator를
	 * 만들어 주므로, 두 경우 모두 여기서 걸러낸다.
	 */
	static IAnimationBudgetAllocator* FindAllocator(UWorld* World)
	{
		IAnimationBudgetAllocator* Allocator = World != nullptr ? IAnimationBudgetAllocator::Get(World) : nullptr;
		if (Allocator == nullptr)
		{
			UE_LOG(LogAnimBudgetTest, Warning, TEXT("No budget allocator: allocators only exist for game worlds (PIE or standalone)."));
		}

		return Allocator;
	}

	/** 월드에서 찾은 첫 번째 스포너. 테스트 레벨에 없으면 null. */
	static AAnimBudgetTestSpawner* FindSpawner(UWorld* World)
	{
		if (World != nullptr)
		{
			for (TActorIterator<AAnimBudgetTestSpawner> It(World); It; ++It)
			{
				return *It;
			}
		}

		UE_LOG(LogAnimBudgetTest, Warning, TEXT("No AAnimBudgetTestSpawner in this world."));
		return nullptr;
	}

	static FAutoConsoleCommandWithWorldAndArgs CmdEnable(
		TEXT("AnimBudgetTest.Enable"),
		TEXT("<0|1> Enable the per-world animation budget allocator. a.Budget.Enabled must also be 1."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (IAnimationBudgetAllocator* Allocator = FindAllocator(World))
			{
				const bool bEnable = Args.Num() > 0 ? (FCString::Atoi(*Args[0]) != 0) : true;
				Allocator->SetEnabled(bEnable);
				UE_LOG(LogAnimBudgetTest, Display, TEXT("Per-world allocator enabled: %d"), bEnable ? 1 : 0);
			}
		}));

	static FAutoConsoleCommandWithWorldAndArgs CmdSpawn(
		TEXT("AnimBudgetTest.Spawn"),
		TEXT("<GridSize> Respawn the test grid at GridSize x GridSize components."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (AAnimBudgetTestSpawner* Spawner = FindSpawner(World))
			{
				Spawner->SpawnGrid(Args.Num() > 0 ? FCString::Atoi(*Args[0]) : Spawner->GridSize);
			}
		}));

	static FAutoConsoleCommandWithWorldAndArgs CmdClear(
		TEXT("AnimBudgetTest.Clear"),
		TEXT("Destroy every component spawned by the test spawner."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (AAnimBudgetTestSpawner* Spawner = FindSpawner(World))
			{
				Spawner->ClearGrid();
			}
		}));

	static FAutoConsoleCommandWithWorldAndArgs CmdReport(
		TEXT("AnimBudgetTest.Report"),
		TEXT("Log the current component and reduced-work counts."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (AAnimBudgetTestSpawner* Spawner = FindSpawner(World))
			{
				Spawner->LogReport();
			}
		}));
}

AAnimBudgetTestSpawner::AAnimBudgetTestSpawner()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	// budgeted 컴포넌트들이 이번 프레임에 틱할 기회를 다 가진 뒤에 표본을 뜬다.
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AAnimBudgetTestSpawner::BeginPlay()
{
	Super::BeginPlay();

	// 격자를 만들기 전에 실행해야 한다. CVar에 따라 등록 시점의 동작이 달라지기 때문.
	for (const FString& Command : StartupConsoleCommands)
	{
		if (!Command.IsEmpty() && GEngine != nullptr)
		{
			UE_LOG(LogAnimBudgetTest, Display, TEXT("Startup command: %s"), *Command);
			GEngine->Exec(GetWorld(), *Command);
		}
	}

	if (bEnableBudgetOnBeginPlay)
	{
		if (IAnimationBudgetAllocator* Allocator = IAnimationBudgetAllocator::Get(GetWorld()))
		{
			Allocator->SetEnabled(true);
		}
	}

	TimeUntilNextReport = ReportIntervalSeconds;

	SpawnGrid(GridSize);
}

void AAnimBudgetTestSpawner::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	ClearGrid();

	Super::EndPlay(EndPlayReason);
}

void AAnimBudgetTestSpawner::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bSignificanceFlagsPending)
	{
		bSignificanceFlagsPending = false;

		// 이 시점이면 지연 등록이 끝나 컴포넌트가 allocator를 물고 있다.
		// bAutoCalculateSignificance가 켜져 있으면 significance 값은 컴포넌트가 계속 자동 계산하므로
		// 여기서 넘기는 1.0은 무시되고 플래그만 반영된다.
		for (USkeletalMeshComponentBudgeted* Component : SpawnedComponents)
		{
			if (Component != nullptr)
			{
				Component->SetComponentSignificance(1.0f, false, bTickEvenIfNotRendered, true, false);
			}
		}
	}

	// PoseTickedThisFrame()은 GFrameCounter == LastPoseTickFrame 이므로, allocator가 의도한 값이
	// 아니라 이번 프레임에 실제로 포즈가 평가된 컴포넌트 수를 센다.
	// 엔진의 NumInterpolated / AverageTickRate CSV 스탯도 WITH_TICK_DEBUG 전용이라,
	// 같은 값을 컴포넌트의 public 접근자로 직접 센다.
	int32 NumPoseTicked = 0;
	int32 NumInterpolating = 0;
	int32 TickRateSum = 0;
	for (int32 Index = 0; Index < SpawnedComponents.Num(); ++Index)
	{
		const USkeletalMeshComponentBudgeted* Component = SpawnedComponents[Index];
		if (Component == nullptr)
		{
			continue;
		}

		if (Component->PoseTickedThisFrame())
		{
			++NumPoseTicked;
			++PerComponentPoseTicks[Index];
		}

		if (Component->IsUsingExternalInterpolation())
		{
			++NumInterpolating;
		}

		TickRateSum += FMath::Max<int32>(1, Component->GetExternalTickRate());
	}

	const int32 NumComponents = SpawnedComponents.Num();
	const float AnimQuality = NumComponents > 0 ? (float)NumPoseTicked / (float)NumComponents : 0.0f;

	CSV_CUSTOM_STAT(AnimBudgetTest, NumComponents, NumComponents, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, NumPoseTicked, NumPoseTicked, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, NumReducedWork, NumReducedWorkComponents, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, AnimQuality, AnimQuality, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, NumInterpolating, NumInterpolating, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, AvgTickRate, NumComponents > 0 ? (float)TickRateSum / (float)NumComponents : 0.0f, ECsvCustomStatOp::Set);

	PoseTickAccumulator += NumPoseTicked;
	InterpolatingAccumulator += NumInterpolating;
	TickRateAccumulator += TickRateSum;
	++FramesSinceReport;

	if (ReportIntervalSeconds <= 0.0f)
	{
		return;
	}

	TimeUntilNextReport -= DeltaSeconds;
	if (TimeUntilNextReport <= 0.0f)
	{
		TimeUntilNextReport = ReportIntervalSeconds;
		LogReport();
	}
}

void AAnimBudgetTestSpawner::SpawnGrid(int32 InGridSize)
{
	ClearGrid();

	GridSize = FMath::Clamp(InGridSize, 1, 100);

	if (TestMesh == nullptr)
	{
		UE_LOG(LogAnimBudgetTest, Warning, TEXT("TestMesh is not set, nothing to spawn."));
		return;
	}

	// 플레이어 시점에서 격자의 절반 정도가 한 번에 보이도록 액터를 중심으로 배치한다.
	const float HalfExtent = (GridSize - 1) * GridSpacing * 0.5f;

	// 파괴한 컴포넌트는 GC 전까지 이름을 물고 있으므로, 재생성 때는 새 이름이 필요하다.
	++SpawnGeneration;

	SpawnedComponents.Reserve(GridSize * GridSize);

	for (int32 Y = 0; Y < GridSize; ++Y)
	{
		for (int32 X = 0; X < GridSize; ++X)
		{
			const FName ComponentName = *FString::Printf(TEXT("BudgetedMesh_%d_%d_%d"), SpawnGeneration, X, Y);
			USkeletalMeshComponentBudgeted* Component = NewObject<USkeletalMeshComponentBudgeted>(this, ComponentName);

			// 아래 두 값은 컴포넌트가 allocator에 등록될 때 읽히므로 RegisterComponent() 전에 설정해야 한다.
			Component->SetAutoCalculateSignificance(bAutoCalculateSignificance);
			if (bBindReduceWork)
			{
				Component->OnReduceWork().BindUObject(this, &AAnimBudgetTestSpawner::HandleReduceWork);
			}

			Component->SetupAttachment(RootComponent);
			Component->SetRelativeLocation(FVector(X * GridSpacing - HalfExtent, Y * GridSpacing - HalfExtent, 0.0f));
			Component->SetSkeletalMeshAsset(TestMesh);

			if (TestAnimInstance != nullptr)
			{
				Component->SetAnimationMode(EAnimationMode::AnimationBlueprint);
				Component->SetAnimInstanceClass(TestAnimInstance);
			}

			// RegisterComponent가 컴포넌트의 BeginPlay도 돌리고, 거기서 allocator에 자기를 등록한다.
			Component->RegisterComponent();

			SpawnedComponents.Add(Component);
		}
	}

	PerComponentPoseTicks.SetNumZeroed(SpawnedComponents.Num());

	// 여기서 바로 SetComponentSignificance를 부르면 안 된다. 월드 BeginPlay 중에는 컴포넌트가
	// 아직 지연 등록 상태라 호출이 경고만 남기고 버려진다. 첫 Tick까지 미룬다.
	bSignificanceFlagsPending = true;

	UE_LOG(LogAnimBudgetTest, Display, TEXT("Spawned %d budgeted components (%dx%d)."), SpawnedComponents.Num(), GridSize, GridSize);
}

void AAnimBudgetTestSpawner::ClearGrid()
{
	for (USkeletalMeshComponentBudgeted* Component : SpawnedComponents)
	{
		if (Component != nullptr)
		{
			Component->OnReduceWork().Unbind();
			Component->DestroyComponent();
		}
	}

	SpawnedComponents.Reset();
	PerComponentPoseTicks.Reset();
	bSignificanceFlagsPending = false;
	NumReducedWorkComponents = 0;
	PoseTickAccumulator = 0;
	FramesSinceReport = 0;
}

bool AAnimBudgetTestSpawner::GetPlayerViewLocation(FVector& OutViewLocation) const
{
	const UWorld* LocalWorld = GetWorld();
	if (LocalWorld == nullptr)
	{
		return false;
	}

	for (FConstPlayerControllerIterator It = LocalWorld->GetPlayerControllerIterator(); It; ++It)
	{
		if (const APlayerController* PlayerController = It->Get())
		{
			FRotator ViewRotation = FRotator::ZeroRotator;
			PlayerController->GetPlayerViewPoint(OutViewLocation, ViewRotation);
			return true;
		}
	}

	return false;
}

void AAnimBudgetTestSpawner::LogReport()
{
	UWorld* LocalWorld = GetWorld();
	const IAnimationBudgetAllocator* Allocator = LocalWorld != nullptr ? IAnimationBudgetAllocator::Get(LocalWorld) : nullptr;
	const bool bWorldEnabled = Allocator != nullptr && Allocator->GetEnabled();

	static const IConsoleVariable* EnabledCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("a.Budget.Enabled"));
	const bool bCVarEnabled = EnabledCVar != nullptr && EnabledCVar->GetInt() != 0;

	const int32 NumComponents = SpawnedComponents.Num();
	const float AvgPoseTicked = FramesSinceReport > 0 ? (float)PoseTickAccumulator / (float)FramesSinceReport : 0.0f;
	const float AvgQuality = NumComponents > 0 ? AvgPoseTicked / (float)NumComponents : 0.0f;

	// allocator가 "렌더링 중"인지 판단할 때 쓰는 것과 같은 식으로 렌더 상태를 센다
	// (AnimationBudgetAllocator.cpp의 ShouldComponentTick 참고: LastRenderTime > World->TimeSeconds - 1).
	if (LocalWorld != nullptr)
	{
		const float RenderCutoff = LocalWorld->TimeSeconds - 1.0f;
		int32 NumConsideredRendered = 0;
		float MaxLastRenderTime = -FLT_MAX;
		for (const USkeletalMeshComponentBudgeted* Component : SpawnedComponents)
		{
			if (Component != nullptr)
			{
				const float ComponentLastRenderTime = Component->GetLastRenderTime();
				MaxLastRenderTime = FMath::Max(MaxLastRenderTime, ComponentLastRenderTime);
				if (ComponentLastRenderTime > RenderCutoff)
				{
					++NumConsideredRendered;
				}
			}
		}

		UE_LOG(LogAnimBudgetTest, Display,
			TEXT("renderState: consideredRendered=%d/%d worldTime=%.2f cutoff=%.2f maxLastRenderTime=%.2f"),
			NumConsideredRendered, SpawnedComponents.Num(), LocalWorld->TimeSeconds, RenderCutoff, MaxLastRenderTime);
	}

	const float AvgInterpolating = FramesSinceReport > 0 ? (float)InterpolatingAccumulator / (float)FramesSinceReport : 0.0f;
	const float AvgTickRate = (FramesSinceReport > 0 && NumComponents > 0)
		? (float)TickRateAccumulator / ((float)FramesSinceReport * (float)NumComponents)
		: 0.0f;

	UE_LOG(LogAnimBudgetTest, Display,
		TEXT("components=%d avgPoseTicked=%.1f animQuality=%.3f avgInterpolating=%.1f avgTickRate=%.2f reducedWork=%d frames=%d a.Budget.Enabled=%d worldEnabled=%d -> budgeting %s"),
		NumComponents,
		AvgPoseTicked,
		AvgQuality,
		AvgInterpolating,
		AvgTickRate,
		NumReducedWorkComponents,
		FramesSinceReport,
		bCVarEnabled ? 1 : 0,
		bWorldEnabled ? 1 : 0,
		(bCVarEnabled && bWorldEnabled) ? TEXT("ACTIVE") : TEXT("INACTIVE"));

	// significance가 실제로 우선순위를 정하고 있는지 보려면 전체 평균만으로는 부족하다.
	// 컴포넌트를 플레이어 시점까지의 거리순으로 정렬해 균등한 구간으로 나누고, 구간별 틱 비율을 낸다.
	// significance가 동작한다면 가까운 구간일수록 비율이 높아야 한다.
	FVector ViewLocation = FVector::ZeroVector;
	if (FramesSinceReport > 0 && NumComponents >= NumDistanceBuckets && GetPlayerViewLocation(ViewLocation))
	{
		TArray<int32> Indices;
		Indices.Reserve(NumComponents);
		for (int32 Index = 0; Index < NumComponents; ++Index)
		{
			Indices.Add(Index);
		}

		TArray<float> DistancesSqr;
		DistancesSqr.SetNumZeroed(NumComponents);
		for (int32 Index = 0; Index < NumComponents; ++Index)
		{
			if (const USkeletalMeshComponentBudgeted* Component = SpawnedComponents[Index])
			{
				DistancesSqr[Index] = (float)FVector::DistSquared(Component->GetComponentLocation(), ViewLocation);
			}
		}

		Indices.Sort([&DistancesSqr](int32 A, int32 B) { return DistancesSqr[A] < DistancesSqr[B]; });

		FString BucketReport;
		const int32 BucketSize = NumComponents / NumDistanceBuckets;
		for (int32 Bucket = 0; Bucket < NumDistanceBuckets; ++Bucket)
		{
			const int32 Begin = Bucket * BucketSize;
			const int32 End = (Bucket == NumDistanceBuckets - 1) ? NumComponents : Begin + BucketSize;

			int64 BucketTicks = 0;
			for (int32 Slot = Begin; Slot < End; ++Slot)
			{
				BucketTicks += PerComponentPoseTicks[Indices[Slot]];
			}

			const int32 BucketCount = End - Begin;
			const float BucketRatio = (float)BucketTicks / ((float)BucketCount * (float)FramesSinceReport);
			const float NearDistance = FMath::Sqrt(DistancesSqr[Indices[Begin]]);
			const float FarDistance = FMath::Sqrt(DistancesSqr[Indices[End - 1]]);

			BucketReport += FString::Printf(TEXT("  [%.0f-%.0fcm n=%d]=%.3f"), NearDistance, FarDistance, BucketCount, BucketRatio);
		}

		UE_LOG(LogAnimBudgetTest, Display, TEXT("tickRatioByDistance:%s"), *BucketReport);
	}

	PoseTickAccumulator = 0;
	InterpolatingAccumulator = 0;
	TickRateAccumulator = 0;
	FramesSinceReport = 0;
	for (int32& Count : PerComponentPoseTicks)
	{
		Count = 0;
	}
}

void AAnimBudgetTestSpawner::HandleReduceWork(USkeletalMeshComponentBudgeted* InComponent, bool bReduce)
{
	if (InComponent == nullptr)
	{
		return;
	}

	// 실제 게임이라면 여기서 저가 애님 블루프린트로 바꾸거나 클로스를 끈다.
	// 이 테스트에서는 reduced work 경로가 도는지만 보면 되므로 최저 LOD 강제로 충분하다.
	const int32 NumLODs = InComponent->GetNumLODs();
	InComponent->SetForcedLOD(bReduce ? FMath::Max(1, NumLODs) : 0);

	NumReducedWorkComponents += bReduce ? 1 : -1;
}
