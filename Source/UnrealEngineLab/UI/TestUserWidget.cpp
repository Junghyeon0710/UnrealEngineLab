// Copyright Epic Games, Inc. All Rights Reserved.

#include "UI/TestUserWidget.h"

#include "Components/TextBlock.h"

void UTestUserWidget::SetDisplayText(const FText& InText)
{
	DisplayText = InText;
	ApplyDisplayText();
}

void UTestUserWidget::NativePreConstruct()
{
	Super::NativePreConstruct();

	// 디자이너 프리뷰에서도 DisplayText 가 보이도록 여기서 한 번 적용한다.
	ApplyDisplayText();
}

void UTestUserWidget::NativeConstruct()
{
	Super::NativeConstruct();

	ApplyDisplayText();
}

void UTestUserWidget::ApplyDisplayText()
{
	// BindWidget 은 컴파일 타임에 보장되지만, 위젯 트리가 아직 없는 CDO 등에서는 널일 수 있다.
	if (!TitleText)
	{
		return;
	}

	// DisplayText 를 아직 채우지 않았다면 디자이너에서 넣어둔 문구를 그대로 둔다.
	// 이 가드가 없으면 PreConstruct 가 원래 텍스트를 빈 값으로 덮어쓴다.
	if (DisplayText.IsEmpty())
	{
		return;
	}

	TitleText->SetText(DisplayText);
}
