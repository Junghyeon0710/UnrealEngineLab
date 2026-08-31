// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "TestUserWidget.generated.h"

class UTextBlock;

/**
 * WBP_Test 의 C++ 베이스 클래스.
 *
 * 디자이너에 있는 TitleText 텍스트 블록을 BindWidget 으로 받아오고,
 * DisplayText 값을 그 텍스트 블록에 흘려보낸다.
 */
UCLASS()
class UNREALENGINELAB_API UTestUserWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** DisplayText 를 바꾸고 화면에 바로 반영한다. */
	UFUNCTION(BlueprintCallable, Category = "Test")
	void SetDisplayText(const FText& InText);

	UFUNCTION(BlueprintPure, Category = "Test")
	const FText& GetDisplayText() const { return DisplayText; }

protected:
	//~ Begin UUserWidget interface
	virtual void NativePreConstruct() override;
	virtual void NativeConstruct() override;
	//~ End UUserWidget interface

	/**
	 * 디자이너의 위젯 이름과 이 프로퍼티 이름이 똑같아야 바인딩된다.
	 * 이름이 어긋나면 위젯 블루프린트 컴파일 단계에서 에러로 잡힌다.
	 */
	UPROPERTY(BlueprintReadOnly, meta = (BindWidget))
	TObjectPtr<UTextBlock> TitleText;

	/** 텍스트 블록에 표시할 값. 디테일 패널에서 바꾸면 디자이너 프리뷰에도 바로 보인다. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Test")
	FText DisplayText;

private:
	/** DisplayText 를 TitleText 에 적용한다. */
	void ApplyDisplayText();
};
