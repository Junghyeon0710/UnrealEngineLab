// MVVM과 비교할 기존 방식 위젯 (Docs/UE/MVVM.md).

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "MVVMLabClassicStatusWidget.generated.h"

class UButton;
class UMVVMLabPlayerModel;

/**
 * UMG 속성 바인딩(디테일 패널의 "바인딩" 버튼)으로 만든 상태 창의 부모 클래스.
 *
 * 위젯이 Model을 직접 들고, 바인딩 함수가 Model을 읽어 값을 만든다.
 * 이 함수들은 값이 바뀌었든 아니든 위젯이 그려질 때마다 불린다.
 */
UCLASS(Abstract)
class UNREALENGINELAB_API UMVVMLabClassicStatusWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintReadWrite, Category = "MVVMLab")
	TObjectPtr<UMVVMLabPlayerModel> Model;

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	float GetHealthPercentBinding() const;

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	FText GetHealthTextBinding() const;

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	FText GetAmmoTextBinding() const;

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	ESlateVisibility GetLowHealthVisibilityBinding() const;

	/** 위 바인딩 함수들이 불린 횟수. */
	static int64 BindingCallCount;

protected:
	virtual void NativeConstruct() override;

	UFUNCTION()
	void HandleHealClicked();

	UPROPERTY(meta = (BindWidgetOptional))
	TObjectPtr<UButton> HealButton;
};
