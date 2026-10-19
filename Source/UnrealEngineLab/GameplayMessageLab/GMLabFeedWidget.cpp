// GameplayMessage 실험의 킬 피드 위젯 부모 클래스 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabFeedWidget.h"

#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "GameplayMessageLab/GMLabActors.h"
#include "GameplayMessageLab/GMLabMessages.h"
#include "TimerManager.h"

int32 UGMLabFeedWidget::FeedLinesAdded = 0;
int32 UGMLabFeedWidget::AccoladesShown = 0;

namespace GMLabFeed
{
	FString NameOf(const AActor* Actor)
	{
		const AGMLabActorBase* LabActor = Cast<AGMLabActorBase>(Actor);
		return LabActor ? LabActor->GetDisplayName() : GetNameSafe(Actor);
	}
}

void UGMLabFeedWidget::AddFeedLine(const FGMLabCombatMessage& Message)
{
	++FeedLinesAdded;
	UTextBlock* Line = NewObject<UTextBlock>(this);
	Line->SetText(FText::FromString(FString::Printf(TEXT("%s  ->  %s"), *GMLabFeed::NameOf(Message.Instigator), *GMLabFeed::NameOf(Message.Target))));
	FSlateFontInfo Font = Line->GetFont();
	Font.Size = 18;
	Line->SetFont(Font);
	FeedBox->AddChildToVerticalBox(Line);
	while (FeedBox->GetChildrenCount() > 6)
	{
		FeedBox->RemoveChildAt(0);
	}
}

void UGMLabFeedWidget::ShowAccolade(FGameplayTag ActualChannel, const FGMLabCombatMessage& Message)
{
	++AccoladesShown;
	const FString Title = ActualChannel.MatchesTagExact(TAG_GMLab_Message_Accolade_TripleKill) ? TEXT("TRIPLE KILL") : TEXT("DOUBLE KILL");
	AccoladeText->SetText(FText::FromString(FString::Printf(TEXT("%s   %s"), *Title, *GMLabFeed::NameOf(Message.Instigator))));
	AccoladeText->SetVisibility(ESlateVisibility::HitTestInvisible);
	GetWorld()->GetTimerManager().SetTimer(AccoladeTimer, [this]() { AccoladeText->SetVisibility(ESlateVisibility::Hidden); }, 1.5f, false);
}
