// MVVM 실험용 게임 모드 (Docs/UE/MVVM.md).

#include "MVVMLab/MVVMLabGameMode.h"

#include "Blueprint/UserWidget.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "MVVMGameSubsystem.h"
#include "MVVMLab/MVVMLabClassicStatusWidget.h"
#include "MVVMLab/MVVMLabPlayerModel.h"
#include "MVVMLab/MVVMLabStatusViewModel.h"
#include "TimerManager.h"
#include "Types/MVVMViewModelCollection.h"

const FName AMVVMLabGameMode::StatusViewModelName(TEXT("PlayerStatus"));

AMVVMLabGameMode::AMVVMLabGameMode()
{
	DefaultPawnClass = nullptr;
	HUDClass = AMVVMLabHUD::StaticClass();
	MVVMWidgetClass = TSoftClassPtr<UUserWidget>(FSoftObjectPath(TEXT("/Game/MVVMLab/UI/WBP_StatusMVVM.WBP_StatusMVVM_C")));
	MiniWidgetClass = TSoftClassPtr<UUserWidget>(FSoftObjectPath(TEXT("/Game/MVVMLab/UI/WBP_StatusMini.WBP_StatusMini_C")));
	ClassicWidgetClass = TSoftClassPtr<UUserWidget>(FSoftObjectPath(TEXT("/Game/MVVMLab/UI/WBP_StatusClassic.WBP_StatusClassic_C")));
}

void AMVVMLabGameMode::BeginPlay()
{
	Super::BeginPlay();

	// 1. Model: 게임 데이터.
	Model = NewObject<UMVVMLabPlayerModel>(this);

	// 2. ViewModel: Model을 구독하고, Global Viewmodel Collection에 이름으로 올려 둔다.
	ViewModel = NewObject<UMVVMLabStatusViewModel>(this);
	ViewModel->SetModel(Model);
	if (UMVVMGameSubsystem* MVVM = GetGameInstance()->GetSubsystem<UMVVMGameSubsystem>())
	{
		FMVVMViewModelContext Context;
		Context.ContextClass = UMVVMLabStatusViewModel::StaticClass();
		Context.ContextName = StatusViewModelName;
		MVVM->GetViewModelCollection()->AddViewModelInstance(Context, ViewModel);
	}

	// 3. View: MVVM 위젯은 ViewModel을 스스로 찾아온다. 기존 방식 위젯에는 Model을 직접 넣는다.
	ShowWidget(MVVMWidgetClass, FVector2D(40.f, 40.f), FVector2D(380.f, 290.f));
	ShowWidget(MiniWidgetClass, FVector2D(40.f, 360.f), FVector2D(380.f, 130.f));
	if (UMVVMLabClassicStatusWidget* Classic = Cast<UMVVMLabClassicStatusWidget>(
		ShowWidget(ClassicWidgetClass, FVector2D(470.f, 40.f), FVector2D(380.f, 290.f))))
	{
		Classic->Model = Model;
	}

	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		PC->SetShowMouseCursor(true);
		PC->SetInputMode(FInputModeGameAndUI());
	}
	ResetCounters();
}

void AMVVMLabGameMode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	GetWorldTimerManager().ClearTimer(DemoTimer);
	if (UGameInstance* GI = GetGameInstance())
	{
		if (UMVVMGameSubsystem* MVVM = GI->GetSubsystem<UMVVMGameSubsystem>())
		{
			MVVM->GetViewModelCollection()->RemoveAllViewModelInstance(ViewModel);
		}
	}
	Super::EndPlay(EndPlayReason);
}

UUserWidget* AMVVMLabGameMode::ShowWidget(const TSoftClassPtr<UUserWidget>& WidgetClass, FVector2D Position, FVector2D Size)
{
	UClass* Class = WidgetClass.LoadSynchronous();
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!Class || !PC)
	{
		return nullptr;
	}
	UUserWidget* Widget = CreateWidget<UUserWidget>(PC, Class);
	Widget->AddToViewport();
	Widget->SetAlignmentInViewport(FVector2D::ZeroVector);
	Widget->SetPositionInViewport(Position, false);
	Widget->SetDesiredSizeInViewport(Size);
	return Widget;
}

void AMVVMLabGameMode::StartDemo(float Interval)
{
	DemoStep = 0;
	GetWorldTimerManager().SetTimer(DemoTimer, this, &AMVVMLabGameMode::StepDemo, Interval, true);
}

void AMVVMLabGameMode::StopDemo()
{
	GetWorldTimerManager().ClearTimer(DemoTimer);
}

void AMVVMLabGameMode::StepDemo()
{
	// 데미지 4번으로 체력이 30% 밑으로 내려가게 하고, 사이사이 사격한다.
	static const TCHAR* Script[] = {
		TEXT("Fire"), TEXT("Fire"), TEXT("Damage"), TEXT("Fire"), TEXT("Damage"), TEXT("Fire"),
		TEXT("Damage"), TEXT("Fire"), TEXT("Damage"), TEXT("Fire"), TEXT("Fire"), TEXT("Reload")
	};
	const FString Action = Script[DemoStep % UE_ARRAY_COUNT(Script)];
	if (Action == TEXT("Damage"))
	{
		Model->ApplyDamage(18);
	}
	else if (Action == TEXT("Fire"))
	{
		Model->Fire();
	}
	else
	{
		Model->Reload();
	}
	++DemoStep;
	if (DemoStep >= UE_ARRAY_COUNT(Script))
	{
		StopDemo();
	}
}

void AMVVMLabGameMode::RequestHealThroughViewModel()
{
	if (ViewModel)
	{
		ViewModel->RequestHeal();
	}
}

void AMVVMLabGameMode::ResetCounters()
{
	UMVVMLabStatusViewModel::GetterCallCount = 0;
	UMVVMLabClassicStatusWidget::BindingCallCount = 0;
	FramesDrawn = 0;
	ModelChangesAtReset = Model ? Model->GetChangeCount() : 0;
}

int32 AMVVMLabGameMode::GetModelChanges() const
{
	return Model ? Model->GetChangeCount() - ModelChangesAtReset : 0;
}

FString AMVVMLabGameMode::GetCountersJson() const
{
	return FString::Printf(TEXT("{\"frames\": %lld, \"model_changes\": %d, \"classic_binding_calls\": %lld, \"mvvm_getter_calls\": %lld, ")
		TEXT("\"health\": %d, \"ammo\": %d}"),
		FramesDrawn, GetModelChanges(), UMVVMLabClassicStatusWidget::BindingCallCount, UMVVMLabStatusViewModel::GetterCallCount,
		Model ? Model->GetHealth() : -1, Model ? Model->GetAmmo() : -1);
}

void AMVVMLabHUD::DrawHUD()
{
	Super::DrawHUD();
	AMVVMLabGameMode* GameMode = GetWorld()->GetAuthGameMode<AMVVMLabGameMode>();
	if (!GameMode || !Canvas)
	{
		return;
	}
	GameMode->CountFrame();

	const float Scale = Canvas->ClipY / 870.f;
	// 기존 방식 위젯 아래, View B 오른쪽에 그린다.
	const FVector2D Origin(470.f * Scale, 365.f * Scale);
	const TArray<FString> Lines = {
		FString::Printf(TEXT("Frames drawn             %lld"), GameMode->GetFramesDrawn()),
		FString::Printf(TEXT("Model changes            %d"), GameMode->GetModelChanges()),
		FString::Printf(TEXT("Classic binding calls    %lld"), UMVVMLabClassicStatusWidget::BindingCallCount),
		FString::Printf(TEXT("MVVM getter calls        %lld"), UMVVMLabStatusViewModel::GetterCallCount),
	};
	for (int32 Index = 0; Index < Lines.Num(); ++Index)
	{
		FCanvasTextItem Item(Origin + FVector2D(0.f, Index * 30.f * Scale), FText::FromString(Lines[Index]), GEngine->GetLargeFont(),
			Index >= 2 ? FLinearColor(1.f, 0.85f, 0.3f) : FLinearColor::White);
		Item.Scale = FVector2D(1.1f * Scale);
		Item.EnableShadow(FLinearColor::Black);
		Canvas->DrawItem(Item);
	}
}
