// Copyright Epic Games, Inc. All Rights Reserved.

#include "AnimBudgetTestSpawner.h"

#include "Animation/AnimInstance.h"
#include "Components/SceneComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "IAnimationBudgetAllocator.h"
#include "ProfilingDebugging/CsvProfiler.h"
#include "SkeletalMeshComponentBudgeted.h"

DEFINE_LOG_CATEGORY_STATIC(LogAnimBudgetTest, Log, All);

// The allocator's own NumTicked/AnimQuality CSV stats are compiled out unless WITH_TICK_DEBUG
// is set, so this test measures the same thing from PoseTickedThisFrame() instead.
CSV_DEFINE_CATEGORY(AnimBudgetTest, true);

namespace AnimBudgetTest
{
	/**
	 * The per-world allocator, or null. IAnimationBudgetAllocator::Get asserts on a null world and
	 * only creates allocators for game worlds, so both cases are filtered here.
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

	/** The first spawner in the world, or null if the test level has none. */
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
	// Sample after the budgeted components have had their chance to tick this frame.
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AAnimBudgetTestSpawner::BeginPlay()
{
	Super::BeginPlay();

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

	// PoseTickedThisFrame() is GFrameCounter == LastPoseTickFrame, so this counts the components
	// whose pose really evaluated this frame rather than what the allocator intended.
	int32 NumPoseTicked = 0;
	for (const USkeletalMeshComponentBudgeted* Component : SpawnedComponents)
	{
		if (Component != nullptr && Component->PoseTickedThisFrame())
		{
			++NumPoseTicked;
		}
	}

	const int32 NumComponents = SpawnedComponents.Num();
	const float AnimQuality = NumComponents > 0 ? (float)NumPoseTicked / (float)NumComponents : 0.0f;

	CSV_CUSTOM_STAT(AnimBudgetTest, NumComponents, NumComponents, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, NumPoseTicked, NumPoseTicked, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, NumReducedWork, NumReducedWorkComponents, ECsvCustomStatOp::Set);
	CSV_CUSTOM_STAT(AnimBudgetTest, AnimQuality, AnimQuality, ECsvCustomStatOp::Set);

	PoseTickAccumulator += NumPoseTicked;
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

	// Centre the grid on the actor so the player viewpoint sees roughly half of it at a time.
	const float HalfExtent = (GridSize - 1) * GridSpacing * 0.5f;

	// Destroyed components keep their name until they are collected, so a respawn needs fresh names.
	++SpawnGeneration;

	SpawnedComponents.Reserve(GridSize * GridSize);

	for (int32 Y = 0; Y < GridSize; ++Y)
	{
		for (int32 X = 0; X < GridSize; ++X)
		{
			const FName ComponentName = *FString::Printf(TEXT("BudgetedMesh_%d_%d_%d"), SpawnGeneration, X, Y);
			USkeletalMeshComponentBudgeted* Component = NewObject<USkeletalMeshComponentBudgeted>(this, ComponentName);

			// Both of these are read when the component registers with the allocator, so they have to
			// be set before RegisterComponent().
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

			// Registering the component also runs its BeginPlay, which is where it registers itself
			// with the allocator.
			Component->RegisterComponent();

			SpawnedComponents.Add(Component);
		}
	}

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
	NumReducedWorkComponents = 0;
	PoseTickAccumulator = 0;
	FramesSinceReport = 0;
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

	UE_LOG(LogAnimBudgetTest, Display,
		TEXT("components=%d avgPoseTicked=%.1f animQuality=%.3f reducedWork=%d frames=%d a.Budget.Enabled=%d worldEnabled=%d -> budgeting %s"),
		NumComponents,
		AvgPoseTicked,
		AvgQuality,
		NumReducedWorkComponents,
		FramesSinceReport,
		bCVarEnabled ? 1 : 0,
		bWorldEnabled ? 1 : 0,
		(bCVarEnabled && bWorldEnabled) ? TEXT("ACTIVE") : TEXT("INACTIVE"));

	PoseTickAccumulator = 0;
	FramesSinceReport = 0;
}

void AAnimBudgetTestSpawner::HandleReduceWork(USkeletalMeshComponentBudgeted* InComponent, bool bReduce)
{
	if (InComponent == nullptr)
	{
		return;
	}

	// A real game would swap to a cheaper anim blueprint or disable cloth here. Forcing the cheapest
	// LOD is enough to make the reduced-work path observable in this test.
	const int32 NumLODs = InComponent->GetNumLODs();
	InComponent->SetForcedLOD(bReduce ? FMath::Max(1, NumLODs) : 0);

	NumReducedWorkComponents += bReduce ? 1 : -1;
}
