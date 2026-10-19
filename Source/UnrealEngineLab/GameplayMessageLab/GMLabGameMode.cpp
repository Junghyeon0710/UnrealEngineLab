// GameplayMessage 실험용 게임 모드 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabGameMode.h"

#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "CanvasItem.h"
#include "Camera/CameraActor.h"
#include "DrawDebugHelpers.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameplayMessageLab/GMLabActors.h"
#include "GameplayMessageLab/GMLabFeedWidget.h"
#include "GameplayMessageLab/GMLabMessages.h"
#include "GameplayMessageLab/GMLabStreakProcessor.h"
#include "HAL/PlatformTime.h"
#include "TimerManager.h"

namespace GMLab
{
	// 포탑 번호, 표적 번호. 한 발에 50이라 두 발이면 쓰러진다.
	// 파랑이 0.7초 간격으로 셋을 쓰러뜨려 DOUBLE, TRIPLE이 나오고, 빨강은 두 번 쓰러뜨려 DOUBLE이 나온다.
	const TArray<TPair<int32, int32>> Script = {
		{0, 0}, {0, 0}, {0, 1}, {0, 1}, {0, 2}, {0, 2},
		{1, 3}, {1, 3}, {1, 0}, {1, 0},
		{0, 3}, {1, 1}, {0, 3},
	};
	constexpr float Damage = 50.f;

	// 오른쪽 패널 크기 (위젯 단위). 위는 킬 피드 위젯, 아래는 HUD의 채널별 개수.
	constexpr float PanelMargin = 24.f;
	constexpr float PanelWidth = 440.f;
	constexpr float FeedHeight = 270.f;

	FString Json(const TMap<FGameplayTag, int32>& Counts)
	{
		TArray<FString> Parts;
		for (const TPair<FGameplayTag, int32>& Pair : Counts)
		{
			Parts.Add(FString::Printf(TEXT("\"%s\": %d"), *Pair.Key.ToString(), Pair.Value));
		}
		Parts.Sort();
		return TEXT("{") + FString::Join(Parts, TEXT(", ")) + TEXT("}");
	}
}

AGMLabGameMode::AGMLabGameMode()
{
	DefaultPawnClass = nullptr;
	HUDClass = AGMLabHUD::StaticClass();
	FeedWidgetClass = TSoftClassPtr<UUserWidget>(FSoftObjectPath(TEXT("/Game/GameplayMessageLab/UI/WBP_GMLabFeed.WBP_GMLabFeed_C")));
	StreakProcessor = CreateDefaultSubobject<UGMLabStreakProcessor>(TEXT("StreakProcessor"));
}

void AGMLabGameMode::BeginPlay()
{
	Super::BeginPlay();
	UWorld* World = GetWorld();

	const FLinearColor TurretColors[] = { FLinearColor(0.1f, 0.35f, 1.f), FLinearColor(1.f, 0.15f, 0.1f) };
	const TCHAR* TurretNames[] = { TEXT("Blue Turret"), TEXT("Red Turret") };
	for (int32 Index = 0; Index < 2; ++Index)
	{
		AGMLabTurret* Turret = World->SpawnActor<AGMLabTurret>(FVector(200.f, Index == 0 ? -400.f : 400.f, 50.f), FRotator::ZeroRotator);
		Turret->Setup(TurretNames[Index], TurretColors[Index]);
		Turrets.Add(Turret);
	}
	for (int32 Index = 0; Index < 4; ++Index)
	{
		AGMLabTarget* Target = World->SpawnActor<AGMLabTarget>(FVector(800.f, -390.f + 260.f * Index, 50.f), FRotator::ZeroRotator);
		Target->Setup(FString::Printf(TEXT("Target %d"), Index + 1), FLinearColor(0.55f, 0.55f, 0.55f));
		Targets.Add(Target);
	}

	// 실험용 리스너 둘. 부모 채널을 PartialMatch로 들으면 Damage, Elimination, Accolade.* 가 전부 들어온다.
	UGameplayMessageSubsystem& Messages = UGameplayMessageSubsystem::Get(this);
	FGameplayMessageListenerParams<FGMLabCombatMessage> CountParams;
	CountParams.MatchType = EGameplayMessageMatch::PartialMatch;
	CountParams.SetMessageReceivedCallback(this, &ThisClass::CountMessage);
	CountHandle = Messages.RegisterListener(TAG_GMLab_Message, CountParams);
	FlashHandle = Messages.RegisterListener(TAG_GMLab_Message_Damage, this, &ThisClass::FlashHitTarget);

	APlayerController* PC = World->GetFirstPlayerController();
	for (TActorIterator<ACameraActor> It(World); It; ++It)
	{
		if (It->ActorHasTag(TEXT("GMLabCamera")) && PC)
		{
			PC->SetViewTarget(*It);
		}
	}
	if (UClass* WidgetClass = FeedWidgetClass.LoadSynchronous(); WidgetClass && PC)
	{
		UUserWidget* Feed = CreateWidget<UUserWidget>(PC, WidgetClass);
		Feed->AddToViewport();
		// 오른쪽 위. 그 아래에 HUD가 채널별 개수를 그린다.
		// SetPositionInViewport와 SetDesiredSizeInViewport는 앵커를 (0,0)으로 되돌리므로 앵커는 맨 뒤에 정한다.
		Feed->SetPositionInViewport(FVector2D(-GMLab::PanelMargin, GMLab::PanelMargin), false);
		Feed->SetDesiredSizeInViewport(FVector2D(GMLab::PanelWidth, GMLab::FeedHeight));
		Feed->SetAnchorsInViewport(FAnchors(1.f, 0.f));
		Feed->SetAlignmentInViewport(FVector2D(1.f, 0.f));
	}
	ResetCounters();
}

void AGMLabGameMode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(DemoTimer);
	CountHandle.Unregister();
	FlashHandle.Unregister();
	Super::EndPlay(EndPlayReason);
}

void AGMLabGameMode::StartDemo(float Interval)
{
	DemoStep = 0;
	GetWorldTimerManager().SetTimer(DemoTimer, this, &AGMLabGameMode::StepDemo, Interval, true);
}

void AGMLabGameMode::StepDemo()
{
	if (DemoStep >= GMLab::Script.Num())
	{
		GetWorldTimerManager().ClearTimer(DemoTimer);
		return;
	}
	const TPair<int32, int32> Shot = GMLab::Script[DemoStep++];
	AGMLabTurret* Turret = Turrets[Shot.Key];
	AGMLabTarget* Target = Targets[Shot.Value];
	if (Target->IsAlive())
	{
		DrawDebugLine(GetWorld(), Turret->GetActorLocation(), Target->GetActorLocation(),
			Shot.Key == 0 ? FColor(40, 120, 255) : FColor(255, 60, 40), false, 0.35f, 0, 6.f);
		Target->ApplyHit(Turret, GMLab::Damage);
	}
}

void AGMLabGameMode::CountMessage(FGameplayTag Channel, const FGMLabCombatMessage& Message)
{
	++ChannelCounts.FindOrAdd(Channel);
}

void AGMLabGameMode::FlashHitTarget(FGameplayTag Channel, const FGMLabCombatMessage& Message)
{
	if (AGMLabTarget* Target = Cast<AGMLabTarget>(Message.Target))
	{
		Target->Flash();
	}
}

void AGMLabGameMode::ResetCounters()
{
	ChannelCounts.Reset();
	UGMLabFeedWidget::FeedLinesAdded = 0;
	UGMLabFeedWidget::AccoladesShown = 0;
}

FString AGMLabGameMode::GetCountersJson() const
{
	return FString::Printf(TEXT("{\"channels\": %s, \"feed_lines\": %d, \"accolades_shown\": %d}"),
		*GMLab::Json(ChannelCounts), UGMLabFeedWidget::FeedLinesAdded, UGMLabFeedWidget::AccoladesShown);
}

FString AGMLabGameMode::RunOrderTest()
{
	UGameplayMessageSubsystem& Messages = UGameplayMessageSubsystem::Get(this);
	TArray<FString> Log;
	auto Note = [&Log](const TCHAR* What) { Log.Add(FString::Printf(TEXT("\"frame %llu  %s\""), GFrameCounter, What)); };

	FGameplayMessageListenerHandle A = Messages.RegisterListener<FGMLabCombatMessage>(TAG_GMLab_Message_Test,
		[&Note](FGameplayTag, const FGMLabCombatMessage&) { Note(TEXT("listener A (Lab.Message.Test, Exact)")); });
	FGameplayMessageListenerHandle B = Messages.RegisterListener<FGMLabCombatMessage>(TAG_GMLab_Message_Test,
		[&Note](FGameplayTag, const FGMLabCombatMessage&) { Note(TEXT("listener B (Lab.Message.Test, Exact)")); });
	FGameplayMessageListenerHandle ParentPartial = Messages.RegisterListener<FGMLabCombatMessage>(TAG_GMLab_Message,
		[&Note](FGameplayTag, const FGMLabCombatMessage&) { Note(TEXT("listener C (Lab.Message, Partial)")); }, EGameplayMessageMatch::PartialMatch);
	FGameplayMessageListenerHandle ParentExact = Messages.RegisterListener<FGMLabCombatMessage>(TAG_GMLab_Message,
		[&Note](FGameplayTag, const FGMLabCombatMessage&) { Note(TEXT("listener D (Lab.Message, Exact)")); });

	FGMLabCombatMessage Message;
	Message.Verb = TAG_GMLab_Message_Test;
	Note(TEXT("before BroadcastMessage"));
	Messages.BroadcastMessage(TAG_GMLab_Message_Test, Message);
	Note(TEXT("after BroadcastMessage"));

	A.Unregister();
	B.Unregister();
	ParentPartial.Unregister();
	ParentExact.Unregister();
	return TEXT("[") + FString::Join(Log, TEXT(", ")) + TEXT("]");
}

FString AGMLabGameMode::RunMismatchTest()
{
	const int32 FeedBefore = UGMLabFeedWidget::FeedLinesAdded;
	const int32 CountBefore = ChannelCounts.FindRef(TAG_GMLab_Message_Elimination);
	FGMLabOtherMessage Wrong;
	Wrong.Value = 42;
	UGameplayMessageSubsystem::Get(this).BroadcastMessage(TAG_GMLab_Message_Elimination, Wrong);
	return FString::Printf(TEXT("{\"feed_before\": %d, \"feed_after\": %d, \"count_before\": %d, \"count_after\": %d}"),
		FeedBefore, UGMLabFeedWidget::FeedLinesAdded, CountBefore, ChannelCounts.FindRef(TAG_GMLab_Message_Elimination));
}

FString AGMLabGameMode::RunBenchmark(int32 Broadcasts, int32 Listeners)
{
	FGMLabCombatMessage Message;
	Message.Verb = TAG_GMLab_Bench;
	Message.Magnitude = 1.f;

	// 1. GameplayMessage
	UGameplayMessageSubsystem& Messages = UGameplayMessageSubsystem::Get(this);
	int64 MessageReceived = 0;
	TArray<FGameplayMessageListenerHandle> Handles;
	for (int32 Index = 0; Index < Listeners; ++Index)
	{
		Handles.Add(Messages.RegisterListener<FGMLabCombatMessage>(TAG_GMLab_Bench,
			[&MessageReceived](FGameplayTag, const FGMLabCombatMessage& Payload) { MessageReceived += static_cast<int64>(Payload.Magnitude); }));
	}
	const double MessageStart = FPlatformTime::Seconds();
	for (int32 Index = 0; Index < Broadcasts; ++Index)
	{
		Messages.BroadcastMessage(TAG_GMLab_Bench, Message);
	}
	const double MessageSeconds = FPlatformTime::Seconds() - MessageStart;
	for (FGameplayMessageListenerHandle& Handle : Handles)
	{
		Handle.Unregister();
	}

	// 2. 같은 일을 멀티캐스트 델리게이트로. 보내는 쪽이 델리게이트를 들고 있고, 받는 쪽이 거기에 직접 붙는 방식이다.
	TMulticastDelegate<void(const FGMLabCombatMessage&)> Delegate;
	int64 DelegateReceived = 0;
	for (int32 Index = 0; Index < Listeners; ++Index)
	{
		Delegate.AddLambda([&DelegateReceived](const FGMLabCombatMessage& Payload) { DelegateReceived += static_cast<int64>(Payload.Magnitude); });
	}
	const double DelegateStart = FPlatformTime::Seconds();
	for (int32 Index = 0; Index < Broadcasts; ++Index)
	{
		Delegate.Broadcast(Message);
	}
	const double DelegateSeconds = FPlatformTime::Seconds() - DelegateStart;

	return FString::Printf(TEXT("{\"broadcasts\": %d, \"listeners\": %d, \"message_us\": %.4f, \"delegate_us\": %.4f, ")
		TEXT("\"message_received\": %lld, \"delegate_received\": %lld}"),
		Broadcasts, Listeners, MessageSeconds * 1e6 / Broadcasts, DelegateSeconds * 1e6 / Broadcasts, MessageReceived, DelegateReceived);
}

void AGMLabHUD::DrawHUD()
{
	Super::DrawHUD();
	const AGMLabGameMode* GameMode = GetWorld()->GetAuthGameMode<AGMLabGameMode>();
	if (!GameMode || !Canvas)
	{
		return;
	}
	// 킬 피드 위젯 바로 아래, 같은 폭으로 그린다. 위젯 단위를 픽셀로 바꾸는 배율이 Dpi다.
	const float Dpi = UWidgetLayoutLibrary::GetViewportScale(this);
	const float Width = GMLab::PanelWidth * Dpi;
	const float Left = Canvas->ClipX - (GMLab::PanelMargin + GMLab::PanelWidth) * Dpi;
	const float Top = (GMLab::PanelMargin * 2.f + GMLab::FeedHeight) * Dpi;
	const float LineHeight = 34.f * Dpi;
	const float Pad = 18.f * Dpi;

	TArray<FGameplayTag> Channels;
	GameMode->GetChannelCounts().GetKeys(Channels);
	Channels.Sort([](const FGameplayTag& A, const FGameplayTag& B) { return A.ToString() < B.ToString(); });

	FCanvasTileItem Background(FVector2D(Left, Top), FVector2D(Width, Pad * 2.f + LineHeight * (2 + FMath::Max(Channels.Num(), 1))),
		FLinearColor(0.02f, 0.03f, 0.05f, 0.8f));
	Background.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Background);

	UFont* Font = GEngine->GetLargeFont();
	const float TextScale = 1.5f * Dpi;
	auto Draw = [&](const FString& Text, float X, float Y, const FLinearColor& Color, bool bRightAlign)
	{
		float TextWidth = 0.f, TextHeight = 0.f;
		Canvas->TextSize(Font, Text, TextWidth, TextHeight, TextScale, TextScale);
		FCanvasTextItem Item(FVector2D(bRightAlign ? X - TextWidth : X, Y), FText::FromString(Text), Font, Color);
		Item.Scale = FVector2D(TextScale);
		Canvas->DrawItem(Item);
	};
	Draw(TEXT("COUNTER  listens Lab.Message (PartialMatch)"), Left + Pad, Top + Pad, FLinearColor(0.55f, 0.75f, 1.f), false);
	for (int32 Index = 0; Index < Channels.Num(); ++Index)
	{
		const float Y = Top + Pad + LineHeight * (Index + 1.4f);
		Draw(Channels[Index].ToString(), Left + Pad, Y, FLinearColor::White, false);
		Draw(FString::FromInt(GameMode->GetChannelCounts().FindRef(Channels[Index])), Left + Width - Pad, Y, FLinearColor(1.f, 0.8f, 0.2f), true);
	}
}
