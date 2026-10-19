// GameplayMessage 실험의 킬 피드 위젯 부모 클래스 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameplayTagContainer.h"
#include "GMLabFeedWidget.generated.h"

class UTextBlock;
class UVerticalBox;
struct FGMLabCombatMessage;

/**
 * 킬 피드와 칭호 표시. 메시지를 듣는 건 이 클래스가 아니라 위젯 블루프린트(WBP_GMLabFeed) 그래프의
 * "Listen for Gameplay Messages" 노드다. 노드가 메시지를 받으면 아래 함수를 부른다.
 */
UCLASS(Abstract)
class UNREALENGINELAB_API UGMLabFeedWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Elimination 메시지 하나를 피드 한 줄로. 최근 6줄만 남긴다. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	void AddFeedLine(const FGMLabCombatMessage& Message);

	/** Accolade 메시지를 큰 글씨로 잠깐 띄운다. ActualChannel로 어떤 칭호인지 안다. */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	void ShowAccolade(FGameplayTag ActualChannel, const FGMLabCombatMessage& Message);

	static int32 FeedLinesAdded;
	static int32 AccoladesShown;

protected:
	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UVerticalBox> FeedBox;

	UPROPERTY(meta = (BindWidget))
	TObjectPtr<UTextBlock> AccoladeText;

private:
	FTimerHandle AccoladeTimer;
};
