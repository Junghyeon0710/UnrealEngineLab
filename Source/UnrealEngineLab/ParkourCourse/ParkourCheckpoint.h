// 파쿠르 타임어택 코스의 체크포인트 (Docs/UE/ParkourTimeAttack.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ParkourCheckpoint.generated.h"

class UBoxComponent;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class UTextRenderComponent;

UENUM(BlueprintType)
enum class EParkourCheckpointType : uint8
{
	Start,
	Checkpoint,
	Finish
};

/**
 * 플레이어가 지나가면 게임 모드에 알리는 문.
 *
 * 순서 판단은 게임 모드가 한다. 이 액터는 통과 판정 상자와,
 * 위치를 보여 주는 기둥·상단 바·번호 글자만 가진다.
 */
UCLASS()
class UNREALENGINELAB_API AParkourCheckpoint : public AActor
{
	GENERATED_BODY()

public:
	AParkourCheckpoint();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;

	/** 다시 시작할 위치. 문 바로 뒤, 문이 바라보는 방향. */
	FTransform GetRespawnTransform() const;

	/** 통과했는지에 따라 문 색을 바꾼다. */
	void SetReached(bool bReached);

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Parkour")
	EParkourCheckpointType Type = EParkourCheckpointType::Checkpoint;

	/** 출발은 0, 결승이 가장 큰 번호. 이 순서대로 지나가야 기록이 이어진다. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Parkour", meta = (ClampMin = "0"))
	int32 Order = 1;

	/** 통과 판정 상자의 반 크기(cm). X가 두께, Y가 문 폭, Z가 높이. */
	UPROPERTY(EditAnywhere, Category = "Parkour")
	FVector GateExtent = FVector(40.f, 250.f, 200.f);

protected:
	UFUNCTION()
	void HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	FLinearColor GetGateColor(bool bReached) const;
	void LayoutGate();

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<UBoxComponent> Trigger;

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<UStaticMeshComponent> LeftPost;

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<UStaticMeshComponent> RightPost;

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<UStaticMeshComponent> TopBar;

	UPROPERTY(VisibleAnywhere, Category = "Parkour")
	TObjectPtr<UTextRenderComponent> Label;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> GateMaterial;
};
