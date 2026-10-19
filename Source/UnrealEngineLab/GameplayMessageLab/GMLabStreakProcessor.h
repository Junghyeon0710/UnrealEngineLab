// GameplayMessage 실험의 연속 처치 처리기 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/GameplayMessageSubsystem.h"
#include "GMLabStreakProcessor.generated.h"

struct FGMLabCombatMessage;

/**
 * Lyra ShooterCore의 ElimChainProcessor와 같은 역할.
 * Elimination 메시지를 듣고, 같은 포탑이 짧은 시간에 연달아 쓰러뜨리면 Accolade 메시지를 다시 보낸다.
 * 메시지를 듣고 새 메시지를 만드는 "처리기"라서, 표적도 UI도 이 클래스를 모른다.
 */
UCLASS(ClassGroup = GMLab, meta = (BlueprintSpawnableComponent))
class UNREALENGINELAB_API UGMLabStreakProcessor : public UActorComponent
{
	GENERATED_BODY()

public:
	/** 이 시간 안에 다음 처치가 나와야 연속으로 센다. */
	UPROPERTY(EditAnywhere, Category = "GMLab")
	float ChainWindow = 2.0f;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	void OnElimination(FGameplayTag Channel, const FGMLabCombatMessage& Message);

	struct FChain
	{
		double LastTime = 0.0;
		int32 Count = 0;
	};
	TMap<TWeakObjectPtr<AActor>, FChain> Chains;
	FGameplayMessageListenerHandle ListenerHandle;
};
