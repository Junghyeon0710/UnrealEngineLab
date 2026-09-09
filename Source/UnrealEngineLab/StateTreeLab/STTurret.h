// StateTree 학습용 샘플.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "NativeGameplayTags.h"
#include "STTurret.generated.h"

class UStateTreeComponent;
class UStaticMeshComponent;

/** 과열되어 잠시 멈춰야 할 때 터렛이 자기 자신에게 보내는 이벤트. */
UNREALENGINELAB_API UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_StateTree_Turret_Overheat);

/**
 * StateTree 학습용 터렛.
 *
 * 상태 판단과 전환은 전부 StateTree 에셋이 맡는다.
 * 이 액터는 "몸"만 제공한다 - 머리를 돌리고, 총을 쏘고, 과열 횟수를 센다.
 * 어떤 순서로 그것들을 하는지는 이 클래스가 모른다.
 */
UCLASS()
class UNREALENGINELAB_API ASTTurret : public AActor
{
	GENERATED_BODY()

public:
	ASTTurret();

	/**
	 * 머리를 목표 쪽으로 DeltaSeconds 만큼 회전시키고, 회전 후 남은 각도(도)를 돌려준다.
	 * Task 가 이 반환값을 보고 조준 완료를 판단한다.
	 */
	UFUNCTION(BlueprintCallable, Category = "Turret")
	float RotateHeadTowards(const FVector& TargetLocation, float DeltaSeconds, float DegreesPerSecond);

	/** 총구에서 목표까지 디버그 라인을 그린다. 과열 카운트도 여기서 올라간다. */
	UFUNCTION(BlueprintCallable, Category = "Turret")
	void Fire(const FVector& TargetLocation);

	/** 총구 위치. Task 가 조준/발사 기준점으로 쓴다. */
	UFUNCTION(BlueprintPure, Category = "Turret")
	FVector GetMuzzleLocation() const;

	/** StateTree 로 이벤트를 보낸다. 과열 알림에 사용한다. */
	UFUNCTION(BlueprintCallable, Category = "Turret")
	void SendTurretEvent(FGameplayTag EventTag);

	/** 과열 상태에서 빠져나올 때 호출한다. */
	UFUNCTION(BlueprintCallable, Category = "Turret")
	void ResetHeat();

	/** 이 횟수만큼 쏘면 과열 이벤트를 보낸다. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Turret", meta = (ClampMin = "1"))
	int32 ShotsUntilOverheat = 9;

protected:
	UPROPERTY(VisibleAnywhere, Category = "Turret")
	TObjectPtr<UStaticMeshComponent> BaseMesh;

	/** 실제로 회전하는 부분. 조준 상태를 눈으로 확인하는 용도다. */
	UPROPERTY(VisibleAnywhere, Category = "Turret")
	TObjectPtr<UStaticMeshComponent> HeadMesh;

	UPROPERTY(VisibleAnywhere, Category = "Turret")
	TObjectPtr<UStateTreeComponent> StateTreeComponent;

private:
	int32 ShotsFiredSinceReset = 0;
};
