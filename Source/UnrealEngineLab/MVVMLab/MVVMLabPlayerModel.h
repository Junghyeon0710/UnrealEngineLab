// MVVM 실험의 Model (Docs/UE/MVVM.md).

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "MVVMLabPlayerModel.generated.h"

class UMVVMLabPlayerModel;

DECLARE_MULTICAST_DELEGATE_OneParam(FOnMVVMLabModelChanged, const UMVVMLabPlayerModel*);

/**
 * 게임 쪽 데이터. 체력과 탄약만 들고 있고, UI가 있는지 모른다.
 * 값이 바뀌면 OnChanged 하나만 쏜다. 누가 듣는지는 신경 쓰지 않는다.
 */
UCLASS(BlueprintType)
class UNREALENGINELAB_API UMVVMLabPlayerModel : public UObject
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void ApplyDamage(int32 Amount);

	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void Heal(int32 Amount);

	/** 탄약이 있으면 하나 쓰고 true. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	bool Fire();

	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void Reload();

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	int32 GetHealth() const { return Health; }

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	int32 GetMaxHealth() const { return MaxHealth; }

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	int32 GetAmmo() const { return Ammo; }

	UFUNCTION(BlueprintPure, Category = "MVVMLab")
	int32 GetMaxAmmo() const { return MaxAmmo; }

	/** 값이 실제로 바뀐 횟수. */
	int32 GetChangeCount() const { return ChangeCount; }

	FOnMVVMLabModelChanged OnChanged;

private:
	void NotifyChanged();

	UPROPERTY()
	int32 Health = 100;

	UPROPERTY()
	int32 MaxHealth = 100;

	UPROPERTY()
	int32 Ammo = 30;

	UPROPERTY()
	int32 MaxAmmo = 30;

	int32 ChangeCount = 0;
};
