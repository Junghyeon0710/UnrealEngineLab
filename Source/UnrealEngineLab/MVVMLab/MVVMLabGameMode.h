// MVVM 실험용 게임 모드 (Docs/UE/MVVM.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "MVVMLabGameMode.generated.h"

class UMVVMLabClassicStatusWidget;
class UMVVMLabPlayerModel;
class UMVVMLabStatusViewModel;
class UUserWidget;

/**
 * Model 하나와 ViewModel 하나를 만들고, 같은 Model을 보는 위젯 세 개를 띄운다.
 *
 *   WBP_StatusMVVM     ViewModel을 Global Viewmodel Collection에서 찾아 바인딩
 *   WBP_StatusMini     같은 ViewModel을 보는 두 번째 View
 *   WBP_StatusClassic  UMG 속성 바인딩. Model을 직접 읽는다
 */
UCLASS()
class UNREALENGINELAB_API AMVVMLabGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AMVVMLabGameMode();

	/** Global Viewmodel Collection에 등록할 이름. 위젯 쪽 Global Viewmodel Identifier와 같아야 한다. */
	static const FName StatusViewModelName;

	/** 정해진 순서로 데미지, 사격, 재장전을 Interval마다 하나씩 한다. 회복은 버튼으로. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void StartDemo(float Interval = 0.6f);

	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void StopDemo();

	/** ViewModel의 명령을 직접 부른다. 버튼을 누른 것과 같다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void RequestHealThroughViewModel();

	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void ResetCounters();

	/** 바인딩 호출 횟수, Model 변경 횟수, 그린 프레임 수를 JSON으로. */
	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	FString GetCountersJson() const;

	/** HUD가 그릴 때마다 하나씩 센다. */
	void CountFrame() { ++FramesDrawn; }

	int64 GetFramesDrawn() const { return FramesDrawn; }
	int32 GetModelChanges() const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(EditAnywhere, Category = "MVVMLab")
	TSoftClassPtr<UUserWidget> MVVMWidgetClass;

	UPROPERTY(EditAnywhere, Category = "MVVMLab")
	TSoftClassPtr<UUserWidget> MiniWidgetClass;

	UPROPERTY(EditAnywhere, Category = "MVVMLab")
	TSoftClassPtr<UUserWidget> ClassicWidgetClass;

private:
	void StepDemo();
	UUserWidget* ShowWidget(const TSoftClassPtr<UUserWidget>& WidgetClass, FVector2D Position, FVector2D Size);

	UPROPERTY(Transient)
	TObjectPtr<UMVVMLabPlayerModel> Model;

	UPROPERTY(Transient)
	TObjectPtr<UMVVMLabStatusViewModel> ViewModel;

	FTimerHandle DemoTimer;
	int32 DemoStep = 0;
	int64 FramesDrawn = 0;
	int32 ModelChangesAtReset = 0;
};

/** 위젯과 상관없이 Canvas로 호출 횟수를 그린다. 이 글자는 바인딩을 쓰지 않는다. */
UCLASS()
class UNREALENGINELAB_API AMVVMLabHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;
};
