// GameplayMessage 실험용 게임 모드 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/GameplayMessageSubsystem.h"
#include "GameFramework/HUD.h"
#include "GMLabGameMode.generated.h"

class AGMLabTarget;
class AGMLabTurret;
class UGMLabStreakProcessor;
class UUserWidget;
struct FGMLabCombatMessage;

/**
 * 포탑 둘, 표적 넷, 킬 피드 위젯 하나를 띄운다.
 *
 * 메시지를 보내는 건 표적(Damage, Elimination)과 연속 처치 처리기(Accolade)뿐이다.
 * 이 게임 모드는 포탑이 표적을 쏘게 시키고, 실험용으로 메시지를 두 군데서 듣는다.
 *   Lab.Message (PartialMatch)    채널별 개수를 센다
 *   Lab.Message.Damage            맞은 표적을 번쩍이게 한다
 */
UCLASS()
class UNREALENGINELAB_API AGMLabGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AGMLabGameMode();

	/** 정해진 순서로 포탑이 표적을 쏜다. Interval마다 한 발. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	void StartDemo(float Interval = 0.35f);

	UFUNCTION(BlueprintCallable, Category = "GMLab")
	void ResetCounters();

	/** 채널별 메시지 수, 피드 줄 수, 칭호 수를 JSON으로. */
	UFUNCTION(BlueprintPure, Category = "GMLab")
	FString GetCountersJson() const;

	/** 보내기 전후와 리스너 안에서 로그를 남겨 호출 순서와 프레임을 본다. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	FString RunOrderTest();

	/** Elimination 채널에 다른 구조체를 보내 본다. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	FString RunMismatchTest();

	/** 메시지 Broadcasts번을 리스너 Listeners개에게 보내는 시간과, 같은 일을 멀티캐스트 델리게이트로 한 시간. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	FString RunBenchmark(int32 Broadcasts, int32 Listeners);

	const TMap<FGameplayTag, int32>& GetChannelCounts() const { return ChannelCounts; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditAnywhere, Category = "GMLab")
	TSoftClassPtr<UUserWidget> FeedWidgetClass;

	UPROPERTY(VisibleAnywhere, Category = "GMLab")
	TObjectPtr<UGMLabStreakProcessor> StreakProcessor;

private:
	void StepDemo();
	void CountMessage(FGameplayTag Channel, const FGMLabCombatMessage& Message);
	void FlashHitTarget(FGameplayTag Channel, const FGMLabCombatMessage& Message);

	UPROPERTY(Transient)
	TArray<TObjectPtr<AGMLabTurret>> Turrets;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AGMLabTarget>> Targets;

	TMap<FGameplayTag, int32> ChannelCounts;
	FGameplayMessageListenerHandle CountHandle;
	FGameplayMessageListenerHandle FlashHandle;
	FTimerHandle DemoTimer;
	int32 DemoStep = 0;
};

/** 채널별 개수를 Canvas로 그린다. */
UCLASS()
class UNREALENGINELAB_API AGMLabHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
