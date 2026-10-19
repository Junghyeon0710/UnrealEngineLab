// MVVM과 비교할 기존 방식 위젯 (Docs/UE/MVVM.md).

#include "MVVMLab/MVVMLabClassicStatusWidget.h"

#include "Components/Button.h"
#include "MVVMLab/MVVMLabPlayerModel.h"

int64 UMVVMLabClassicStatusWidget::BindingCallCount = 0;

float UMVVMLabClassicStatusWidget::GetHealthPercentBinding() const
{
	++BindingCallCount;
	return Model ? static_cast<float>(Model->GetHealth()) / FMath::Max(1, Model->GetMaxHealth()) : 0.f;
}

FText UMVVMLabClassicStatusWidget::GetHealthTextBinding() const
{
	++BindingCallCount;
	return Model ? FText::FromString(FString::Printf(TEXT("HP  %d / %d"), Model->GetHealth(), Model->GetMaxHealth())) : FText::GetEmpty();
}

FText UMVVMLabClassicStatusWidget::GetAmmoTextBinding() const
{
	++BindingCallCount;
	return Model ? FText::FromString(FString::Printf(TEXT("AMMO  %d / %d"), Model->GetAmmo(), Model->GetMaxAmmo())) : FText::GetEmpty();
}

ESlateVisibility UMVVMLabClassicStatusWidget::GetLowHealthVisibilityBinding() const
{
	++BindingCallCount;
	const bool bLow = Model && Model->GetHealth() < FMath::CeilToInt(Model->GetMaxHealth() * 0.3f);
	return bLow ? ESlateVisibility::Visible : ESlateVisibility::Collapsed;
}

void UMVVMLabClassicStatusWidget::NativeConstruct()
{
	Super::NativeConstruct();
	if (HealButton)
	{
		HealButton->OnClicked.AddUniqueDynamic(this, &UMVVMLabClassicStatusWidget::HandleHealClicked);
	}
}

void UMVVMLabClassicStatusWidget::HandleHealClicked()
{
	if (Model)
	{
		Model->Heal(25);
	}
}
