// GameplayMessage 실험의 연속 처치 처리기 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabStreakProcessor.h"

#include "Engine/World.h"
#include "GameplayMessageLab/GMLabMessages.h"

void UGMLabStreakProcessor::BeginPlay()
{
	Super::BeginPlay();
	ListenerHandle = UGameplayMessageSubsystem::Get(this).RegisterListener(TAG_GMLab_Message_Elimination, this, &ThisClass::OnElimination);
}

void UGMLabStreakProcessor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// 핸들로 직접 풀어 준다. 안 풀면 이 컴포넌트가 사라진 뒤에도 목록에 남는다(콜백은 약한 참조라 불리지는 않는다).
	ListenerHandle.Unregister();
	Super::EndPlay(EndPlayReason);
}

void UGMLabStreakProcessor::OnElimination(FGameplayTag Channel, const FGMLabCombatMessage& Message)
{
	if (!Message.Instigator)
	{
		return;
	}
	const double Now = GetWorld()->GetTimeSeconds();
	FChain& Chain = Chains.FindOrAdd(TWeakObjectPtr<AActor>(Message.Instigator.Get()));
	// 첫 처치는 이전 기록이 없으니 시간과 상관없이 1부터 센다.
	Chain.Count = (Chain.Count > 0 && Now - Chain.LastTime <= ChainWindow) ? Chain.Count + 1 : 1;
	Chain.LastTime = Now;

	FGameplayTag Accolade;
	if (Chain.Count == 2)
	{
		Accolade = TAG_GMLab_Message_Accolade_DoubleKill;
	}
	else if (Chain.Count >= 3)
	{
		Accolade = TAG_GMLab_Message_Accolade_TripleKill;
	}
	if (Accolade.IsValid())
	{
		FGMLabCombatMessage AccoladeMessage;
		AccoladeMessage.Verb = Accolade;
		AccoladeMessage.Instigator = Message.Instigator;
		AccoladeMessage.Magnitude = Chain.Count;
		UGameplayMessageSubsystem::Get(this).BroadcastMessage(AccoladeMessage.Verb, AccoladeMessage);
	}
}
