// MVVM 실험의 Model (Docs/UE/MVVM.md).

#include "MVVMLab/MVVMLabPlayerModel.h"

void UMVVMLabPlayerModel::ApplyDamage(int32 Amount)
{
	const int32 NewHealth = FMath::Clamp(Health - Amount, 0, MaxHealth);
	if (NewHealth != Health)
	{
		Health = NewHealth;
		NotifyChanged();
	}
}

void UMVVMLabPlayerModel::Heal(int32 Amount)
{
	const int32 NewHealth = FMath::Clamp(Health + Amount, 0, MaxHealth);
	if (NewHealth != Health)
	{
		Health = NewHealth;
		NotifyChanged();
	}
}

bool UMVVMLabPlayerModel::Fire()
{
	if (Ammo <= 0)
	{
		return false;
	}
	--Ammo;
	NotifyChanged();
	return true;
}

void UMVVMLabPlayerModel::Reload()
{
	if (Ammo != MaxAmmo)
	{
		Ammo = MaxAmmo;
		NotifyChanged();
	}
}

void UMVVMLabPlayerModel::NotifyChanged()
{
	++ChangeCount;
	OnChanged.Broadcast(this);
}
