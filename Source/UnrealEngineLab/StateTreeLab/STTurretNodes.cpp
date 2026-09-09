// StateTree 학습용 샘플 노드 - Global Task / Condition / Task.

#include "StateTreeLab/STTurretNodes.h"

#include "StateTreeLab/STTurret.h"

#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "StateTreeExecutionContext.h"

// ---------------------------------------------------------------------------
// Global Task
// ---------------------------------------------------------------------------

EStateTreeRunStatus FSTFindTargetTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	// 첫 상태 선택이 일어나기 전에 값을 채워 둔다.
	// 비워 두면 진입 조건이 첫 프레임에 대상을 못 찾는다.
	FInstanceDataType& InstanceData = Context.GetInstanceData(*this);
	InstanceData.Target = UGameplayStatics::GetPlayerPawn(Context.GetWorld(), 0);

	return EStateTreeRunStatus::Running;
}

EStateTreeRunStatus FSTFindTargetTask::Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const
{
	FInstanceDataType& InstanceData = Context.GetInstanceData(*this);
	InstanceData.Target = UGameplayStatics::GetPlayerPawn(Context.GetWorld(), 0);

	// Running 을 유지해야 트리가 계속 돈다.
	return EStateTreeRunStatus::Running;
}

// ---------------------------------------------------------------------------
// Condition
// ---------------------------------------------------------------------------

bool FSTTargetInRangeCondition::TestCondition(FStateTreeExecutionContext& Context) const
{
	const FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	bool bResult = false;
	if (InstanceData.Actor && InstanceData.Target)
	{
		const float DistanceSquared = FVector::DistSquared(
			InstanceData.Actor->GetActorLocation(),
			InstanceData.Target->GetActorLocation());

		bResult = DistanceSquared <= FMath::Square(InstanceData.Range);
	}

	return bResult ^ bInvert;
}

// ---------------------------------------------------------------------------
// Aim Task
// ---------------------------------------------------------------------------

EStateTreeRunStatus FSTAimAtTargetTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	const FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	// 대상이 없으면 조준할 수 없다. Failed 로 끝내면 상태 선택이 다시 돌아간다.
	if (!Cast<ASTTurret>(InstanceData.Actor) || !InstanceData.Target)
	{
		return EStateTreeRunStatus::Failed;
	}

	return EStateTreeRunStatus::Running;
}

EStateTreeRunStatus FSTAimAtTargetTask::Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const
{
	const FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	ASTTurret* Turret = Cast<ASTTurret>(InstanceData.Actor);
	if (!Turret || !InstanceData.Target)
	{
		return EStateTreeRunStatus::Failed;
	}

	const float RemainingAngle = Turret->RotateHeadTowards(
		InstanceData.Target->GetActorLocation(),
		DeltaTime,
		InstanceData.DegreesPerSecond);

	return RemainingAngle <= InstanceData.AngleTolerance
		? EStateTreeRunStatus::Succeeded
		: EStateTreeRunStatus::Running;
}

// ---------------------------------------------------------------------------
// Fire Task
// ---------------------------------------------------------------------------

EStateTreeRunStatus FSTFireTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	// 상태에 다시 들어올 때마다 초기화한다. 이 두 줄이 없으면 두 번째 사격이 즉시 끝난다.
	InstanceData.ShotsFired = 0;
	InstanceData.TimeSinceLastShot = InstanceData.Interval;

	if (!Cast<ASTTurret>(InstanceData.Actor) || !InstanceData.Target)
	{
		return EStateTreeRunStatus::Failed;
	}

	return EStateTreeRunStatus::Running;
}

EStateTreeRunStatus FSTFireTask::Tick(FStateTreeExecutionContext& Context, const float DeltaTime) const
{
	FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	ASTTurret* Turret = Cast<ASTTurret>(InstanceData.Actor);
	if (!Turret || !InstanceData.Target)
	{
		return EStateTreeRunStatus::Failed;
	}

	InstanceData.TimeSinceLastShot += DeltaTime;
	if (InstanceData.TimeSinceLastShot >= InstanceData.Interval)
	{
		InstanceData.TimeSinceLastShot = 0.f;
		++InstanceData.ShotsFired;

		Turret->Fire(InstanceData.Target->GetActorLocation());
	}

	return InstanceData.ShotsFired >= InstanceData.ShotCount
		? EStateTreeRunStatus::Succeeded
		: EStateTreeRunStatus::Running;
}

// ---------------------------------------------------------------------------
// Reset Heat Task
// ---------------------------------------------------------------------------

FSTResetHeatTask::FSTResetHeatTask()
{
	bShouldCallTick = false;
}

EStateTreeRunStatus FSTResetHeatTask::EnterState(FStateTreeExecutionContext& Context, const FStateTreeTransitionResult& Transition) const
{
	const FInstanceDataType& InstanceData = Context.GetInstanceData(*this);

	if (ASTTurret* Turret = Cast<ASTTurret>(InstanceData.Actor))
	{
		Turret->ResetHeat();
	}

	// 이 Task 는 할 일이 끝났지만, 같은 상태의 Delay Task 가 끝날 때까지 상태를 유지해야 한다.
	// Succeeded 를 돌려주면 상태가 즉시 완료되어 버린다.
	return EStateTreeRunStatus::Running;
}
