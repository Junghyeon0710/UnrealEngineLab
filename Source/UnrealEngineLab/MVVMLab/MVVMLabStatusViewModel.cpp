// MVVM 실험의 ViewModel (Docs/UE/MVVM.md).

#include "MVVMLab/MVVMLabStatusViewModel.h"

#include "MVVMLab/MVVMLabPlayerModel.h"

int64 UMVVMLabStatusViewModel::GetterCallCount = 0;

namespace MVVMLab
{
	constexpr float LowHealthRatio = 0.3f;
	constexpr int32 HealAmount = 25;
}

void UMVVMLabStatusViewModel::SetModel(UMVVMLabPlayerModel* InModel)
{
	if (UMVVMLabPlayerModel* Old = Model.Get())
	{
		Old->OnChanged.RemoveAll(this);
	}
	Model = InModel;
	if (InModel)
	{
		InModel->OnChanged.AddUObject(this, &UMVVMLabStatusViewModel::HandleModelChanged);
		HandleModelChanged(InModel);
	}
}

void UMVVMLabStatusViewModel::HandleModelChanged(const UMVVMLabPlayerModel* InModel)
{
	// 같은 값이면 SetXxx 안에서 아무것도 알리지 않는다.
	SetMaxHealth(InModel->GetMaxHealth());
	SetHealth(InModel->GetHealth());
	SetMaxAmmo(InModel->GetMaxAmmo());
	SetAmmo(InModel->GetAmmo());
}

void UMVVMLabStatusViewModel::SetHealth(int32 NewHealth)
{
	if (UE_MVVM_SET_PROPERTY_VALUE(Health, NewHealth))
	{
		BroadcastHealthDerived();
	}
}

void UMVVMLabStatusViewModel::SetMaxHealth(int32 NewMaxHealth)
{
	if (UE_MVVM_SET_PROPERTY_VALUE(MaxHealth, FMath::Max(1, NewMaxHealth)))
	{
		BroadcastHealthDerived();
	}
}

void UMVVMLabStatusViewModel::SetAmmo(int32 NewAmmo)
{
	if (UE_MVVM_SET_PROPERTY_VALUE(Ammo, NewAmmo))
	{
		UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetAmmoText);
	}
}

void UMVVMLabStatusViewModel::SetMaxAmmo(int32 NewMaxAmmo)
{
	if (UE_MVVM_SET_PROPERTY_VALUE(MaxAmmo, NewMaxAmmo))
	{
		UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetAmmoText);
	}
}

void UMVVMLabStatusViewModel::BroadcastHealthDerived()
{
	// 함수 필드는 스스로 바뀐 걸 모르니, 재료가 바뀔 때 직접 알려 줘야 한다.
	UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetHealthPercent);
	UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(GetHealthText);
	UE_MVVM_BROADCAST_FIELD_VALUE_CHANGED(IsLowHealth);
}

float UMVVMLabStatusViewModel::GetHealthPercent() const
{
	++GetterCallCount;
	return static_cast<float>(Health) / static_cast<float>(MaxHealth);
}

FText UMVVMLabStatusViewModel::GetHealthText() const
{
	++GetterCallCount;
	return FText::FromString(FString::Printf(TEXT("HP  %d / %d"), Health, MaxHealth));
}

FText UMVVMLabStatusViewModel::GetAmmoText() const
{
	++GetterCallCount;
	return FText::FromString(FString::Printf(TEXT("AMMO  %d / %d"), Ammo, MaxAmmo));
}

bool UMVVMLabStatusViewModel::IsLowHealth() const
{
	++GetterCallCount;
	return Health < FMath::CeilToInt(MaxHealth * MVVMLab::LowHealthRatio);
}

void UMVVMLabStatusViewModel::RequestHeal()
{
	if (UMVVMLabPlayerModel* M = Model.Get())
	{
		M->Heal(MVVMLab::HealAmount);
	}
}
