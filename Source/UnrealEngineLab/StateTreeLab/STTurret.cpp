// StateTree 학습용 샘플.

#include "StateTreeLab/STTurret.h"

#include "Components/StateTreeComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/StaticMesh.h"
#include "StateTreeEvents.h"

UE_DEFINE_GAMEPLAY_TAG(TAG_StateTree_Turret_Overheat, "StateTree.Turret.Overheat");

namespace
{
	/** 총구를 머리 중심에서 앞으로 얼마나 뺄지. */
	constexpr float MuzzleForwardOffset = 60.f;
	/** 실린더 베이스(높이 100, 원점 중심) 위에 머리가 얹히는 높이. */
	constexpr float HeadHeight = 65.f;
}

ASTTurret::ASTTurret()
{
	PrimaryActorTick.bCanEverTick = false;

	BaseMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BaseMesh"));
	SetRootComponent(BaseMesh);
	BaseMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	HeadMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HeadMesh"));
	HeadMesh->SetupAttachment(BaseMesh);
	HeadMesh->SetRelativeLocation(FVector(0.f, 0.f, HeadHeight));
	HeadMesh->SetRelativeScale3D(FVector(1.2f, 0.5f, 0.5f));
	HeadMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	// 엔진 기본 도형이라 별도 에셋 준비 없이 바로 보인다.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (CylinderMesh.Succeeded())
	{
		BaseMesh->SetStaticMesh(CylinderMesh.Object);
	}

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (CubeMesh.Succeeded())
	{
		HeadMesh->SetStaticMesh(CubeMesh.Object);
	}

	StateTreeComponent = CreateDefaultSubobject<UStateTreeComponent>(TEXT("StateTreeComponent"));
}

FVector ASTTurret::GetMuzzleLocation() const
{
	return HeadMesh->GetComponentLocation() + HeadMesh->GetForwardVector() * MuzzleForwardOffset;
}

float ASTTurret::RotateHeadTowards(const FVector& TargetLocation, float DeltaSeconds, float DegreesPerSecond)
{
	const FVector ToTarget = TargetLocation - HeadMesh->GetComponentLocation();
	if (ToTarget.IsNearlyZero())
	{
		return 0.f;
	}

	// Yaw 만 돌린다. 조준 각도도 Yaw 기준으로만 비교한다.
	const float DesiredYaw = ToTarget.Rotation().Yaw;
	const float CurrentYaw = HeadMesh->GetComponentRotation().Yaw;
	const float RemainingBefore = FMath::FindDeltaAngleDegrees(CurrentYaw, DesiredYaw);

	const float MaxStep = DegreesPerSecond * DeltaSeconds;
	const float Step = FMath::Clamp(RemainingBefore, -MaxStep, MaxStep);

	FRotator NewRotation = HeadMesh->GetComponentRotation();
	NewRotation.Yaw = CurrentYaw + Step;
	HeadMesh->SetWorldRotation(NewRotation);

	return FMath::Abs(RemainingBefore - Step);
}

void ASTTurret::Fire(const FVector& TargetLocation)
{
	const FVector Muzzle = GetMuzzleLocation();

	DrawDebugLine(GetWorld(), Muzzle, TargetLocation, FColor::Orange, false, 0.35f, 0, 3.f);
	DrawDebugPoint(GetWorld(), Muzzle, 14.f, FColor::Yellow, false, 0.35f);

	++ShotsFiredSinceReset;

	// 과열 판단은 액터가 하지만, 그래서 어떤 상태로 갈지는 StateTree 가 정한다.
	if (ShotsFiredSinceReset >= ShotsUntilOverheat)
	{
		SendTurretEvent(TAG_StateTree_Turret_Overheat);
	}
}

void ASTTurret::SendTurretEvent(FGameplayTag EventTag)
{
	if (StateTreeComponent && EventTag.IsValid())
	{
		StateTreeComponent->SendStateTreeEvent(FStateTreeEvent(EventTag));
	}
}

void ASTTurret::ResetHeat()
{
	ShotsFiredSinceReset = 0;
}
