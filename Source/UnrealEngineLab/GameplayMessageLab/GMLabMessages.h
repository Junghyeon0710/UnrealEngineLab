// GameplayMessage 실험의 채널과 메시지 구조체 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "NativeGameplayTags.h"
#include "GMLabMessages.generated.h"

// 채널은 게임플레이 태그다. 부모 태그(Lab.Message)를 PartialMatch로 구독하면 아래 채널을 전부 받는다.
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Damage);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Elimination);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Accolade);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Accolade_DoubleKill);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Accolade_TripleKill);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Message_Test);
UE_DECLARE_GAMEPLAY_TAG_EXTERN(TAG_GMLab_Bench);

/**
 * 전투 메시지. Lyra의 FLyraVerbMessage를 줄인 모양이다.
 * 보내는 쪽과 받는 쪽이 서로 아는 건 채널 태그와 이 구조체뿐이다.
 */
USTRUCT(BlueprintType)
struct FGMLabCombatMessage
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "GMLab")
	FGameplayTag Verb;

	UPROPERTY(BlueprintReadWrite, Category = "GMLab")
	TObjectPtr<AActor> Instigator = nullptr;

	UPROPERTY(BlueprintReadWrite, Category = "GMLab")
	TObjectPtr<AActor> Target = nullptr;

	/** 데미지 양, 또는 연속 처치 수 */
	UPROPERTY(BlueprintReadWrite, Category = "GMLab")
	float Magnitude = 0.f;
};

/** 구조체 타입이 다를 때 어떻게 되는지 보려고 만든 다른 메시지. */
USTRUCT(BlueprintType)
struct FGMLabOtherMessage
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadWrite, Category = "GMLab")
	int32 Value = 0;
};
