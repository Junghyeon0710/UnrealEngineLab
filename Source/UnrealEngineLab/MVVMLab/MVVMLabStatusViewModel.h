// MVVM 실험의 ViewModel (Docs/UE/MVVM.md).

#pragma once

#include "CoreMinimal.h"
#include "MVVMViewModelBase.h"
#include "MVVMLabStatusViewModel.generated.h"

class UMVVMLabPlayerModel;

/**
 * 화면에 보여 줄 값만 들고 있는 ViewModel.
 *
 * Model의 변경을 받아 자기 값을 고치고, 바뀐 필드만 FieldNotify로 알린다.
 * 위젯을 모른다. 위젯 쪽 View Binding이 이 필드들을 구독한다.
 */
UCLASS(BlueprintType, DisplayName = "MVVM Lab Status Viewmodel")
class UNREALENGINELAB_API UMVVMLabStatusViewModel : public UMVVMViewModelBase
{
	GENERATED_BODY()

public:
	/** Model을 연결하고 지금 값을 한 번 가져온다. */
	void SetModel(UMVVMLabPlayerModel* InModel);

	int32 GetHealth() const { return Health; }
	void SetHealth(int32 NewHealth);

	int32 GetMaxHealth() const { return MaxHealth; }
	void SetMaxHealth(int32 NewMaxHealth);

	int32 GetAmmo() const { return Ammo; }
	void SetAmmo(int32 NewAmmo);

	int32 GetMaxAmmo() const { return MaxAmmo; }
	void SetMaxAmmo(int32 NewMaxAmmo);

	/** 체력 비율. Health나 MaxHealth가 바뀌면 같이 알린다. */
	UFUNCTION(BlueprintPure, FieldNotify, Category = "MVVMLab")
	float GetHealthPercent() const;

	UFUNCTION(BlueprintPure, FieldNotify, Category = "MVVMLab")
	FText GetHealthText() const;

	UFUNCTION(BlueprintPure, FieldNotify, Category = "MVVMLab")
	FText GetAmmoText() const;

	UFUNCTION(BlueprintPure, FieldNotify, Category = "MVVMLab")
	bool IsLowHealth() const;

	/** 위젯 버튼이 부르는 명령. ViewModel이 Model에 전달한다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	void RequestHeal();

	/** 위 FieldNotify 함수들이 불린 횟수. 바인딩이 실제로 몇 번 돌았는지 보려고 센다. */
	static int64 GetterCallCount;

private:
	void HandleModelChanged(const UMVVMLabPlayerModel* InModel);
	void BroadcastHealthDerived();

	UPROPERTY(BlueprintReadWrite, FieldNotify, Setter, Getter, Category = "MVVMLab", meta = (AllowPrivateAccess))
	int32 Health = 0;

	UPROPERTY(BlueprintReadWrite, FieldNotify, Setter, Getter, Category = "MVVMLab", meta = (AllowPrivateAccess))
	int32 MaxHealth = 1;

	UPROPERTY(BlueprintReadWrite, FieldNotify, Setter, Getter, Category = "MVVMLab", meta = (AllowPrivateAccess))
	int32 Ammo = 0;

	UPROPERTY(BlueprintReadWrite, FieldNotify, Setter, Getter, Category = "MVVMLab", meta = (AllowPrivateAccess))
	int32 MaxAmmo = 0;

	TWeakObjectPtr<UMVVMLabPlayerModel> Model;
};
