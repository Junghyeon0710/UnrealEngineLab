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
 * Spawns a grid of budgeted skeletal meshes so the Animation Budget Allocator can be measured
 * against a known, repeatable load.
 *
 * The allocator only runs when BOTH of these are true:
 *   - the CVar a.Budget.Enabled is 1 (global)
 *   - the per-world allocator is enabled (bEnableBudgetOnBeginPlay here, or AnimBudgetTest.Enable 1)
 *
 * Console commands registered by this actor:
 *   AnimBudgetTest.Enable <0|1>     Toggle the per-world allocator.
 *   AnimBudgetTest.Spawn <GridSize> Respawn the grid at the given size.
 *   AnimBudgetTest.Clear            Destroy all spawned components.
 *   AnimBudgetTest.Report           Log component / reduced-work counts.
 */
UCLASS()
class UNREALENGINELAB_API AAnimBudgetTestSpawner : public AActor
{
	GENERATED_BODY()

public:
	AAnimBudgetTestSpawner();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	/** Rebuild the grid. Destroys any components spawned by a previous call. */
	void SpawnGrid(int32 InGridSize);

	/** Destroy every component spawned by this actor. */
	void ClearGrid();

	/** Log the current component / reduced-work counts. */
	void LogReport() const;

	/** Skeletal mesh used for every grid slot. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	TObjectPtr<USkeletalMesh> TestMesh;

	/** Animation blueprint run on every spawned component. Leave null to spawn meshes with no anim work. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	TSubclassOf<UAnimInstance> TestAnimInstance;

	/** Components are spawned in a GridSize x GridSize square, so the total is GridSize squared. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "1", ClampMax = "100"))
	int32 GridSize = 20;

	/** Distance between grid slots, in cm. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "1.0"))
	float GridSpacing = 150.0f;

	/** Enable the per-world allocator on BeginPlay. a.Budget.Enabled must also be 1 for it to take effect. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bEnableBudgetOnBeginPlay = true;

	/** Let each component derive its own significance from the distance to the player viewpoint. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bAutoCalculateSignificance = true;

	/**
	 * Bind OnReduceWork on every component. The allocator only reduces work on components with a bound
	 * delegate, so leaving this off keeps the test to tick-rate throttling and interpolation only.
	 */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test")
	bool bBindReduceWork = true;

	/** Seconds between automatic reports. 0 disables periodic logging. */
	UPROPERTY(EditAnywhere, Category = "Anim Budget Test", meta = (ClampMin = "0.0"))
	float ReportIntervalSeconds = 0.0f;

private:
	/** Called by the allocator when a component should do more or less work. */
	void HandleReduceWork(USkeletalMeshComponentBudgeted* InComponent, bool bReduce);

	/** Components spawned by SpawnGrid. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<USkeletalMeshComponentBudgeted>> SpawnedComponents;

	/** How many components the allocator currently has in reduced work. */
	int32 NumReducedWorkComponents = 0;

	/** Countdown to the next periodic report. */
	float TimeUntilNextReport = 0.0f;

	/** Bumped on every SpawnGrid so component names stay unique across respawns. */
	int32 SpawnGeneration = 0;
};
