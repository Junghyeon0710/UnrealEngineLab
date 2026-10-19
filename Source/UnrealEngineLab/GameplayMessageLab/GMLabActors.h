// GameplayMessage 실험의 표적과 포탑 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GMLabActors.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class UTextRenderComponent;

/** 큐브 하나와 머리 위 이름표. 표적과 포탑이 같이 쓴다. */
UCLASS(Abstract)
class UNREALENGINELAB_API AGMLabActorBase : public AActor
{
	GENERATED_BODY()

public:
	AGMLabActorBase();

	virtual void Setup(const FString& InDisplayName, const FLinearColor& InColor);

	UFUNCTION(BlueprintPure, Category = "GMLab")
	FString GetDisplayName() const { return DisplayName; }

protected:
	void SetColor(const FLinearColor& InColor);
	void SetLabel(const FString& InText);

	UPROPERTY(VisibleAnywhere, Category = "GMLab")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, Category = "GMLab")
	TObjectPtr<UTextRenderComponent> Label;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> Material;

	FString DisplayName;
	FLinearColor BaseColor = FLinearColor::White;
};

/** 포탑. 아무 일도 안 한다. 메시지의 Instigator로만 쓴다. */
UCLASS()
class UNREALENGINELAB_API AGMLabTurret : public AGMLabActorBase
{
	GENERATED_BODY()
};

/**
 * 표적. 맞으면 Lab.Message.Damage, 쓰러지면 Lab.Message.Elimination을 보낸다.
 * 누가 그 메시지를 듣는지는 모른다. 킬 피드도, 칭호 처리기도, 카운터도 이 클래스에 없다.
 */
UCLASS()
class UNREALENGINELAB_API AGMLabTarget : public AGMLabActorBase
{
	GENERATED_BODY()

public:
	/** 데미지를 받는다. 체력이 0이 되면 쓰러지고 잠시 뒤 다시 선다. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	void ApplyHit(AActor* Shooter, float Damage);

	UFUNCTION(BlueprintPure, Category = "GMLab")
	bool IsAlive() const { return Health > 0.f; }

	/** 맞은 표시. 표적이 부르는 게 아니라 Damage 메시지를 들은 쪽이 부른다. */
	void Flash();

	virtual void Setup(const FString& InDisplayName, const FLinearColor& InColor) override;

private:
	void Respawn();
	void UpdateLabel();

	float Health = 100.f;
	FTimerHandle RespawnTimer;
	FTimerHandle FlashTimer;
};
