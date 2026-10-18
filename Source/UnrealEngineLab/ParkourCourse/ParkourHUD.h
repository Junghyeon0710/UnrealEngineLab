// 파쿠르 타임어택 HUD (Docs/UE/ParkourTimeAttack.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "ParkourHUD.generated.h"

/**
 * 시간, 체크포인트 진행, 최고 기록, 결승 메시지를 Canvas에 그린다.
 * 위젯 에셋 없이 C++만으로 끝내려고 AHUD를 썼다.
 */
UCLASS()
class UNREALENGINELAB_API AParkourHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

	/** 초를 "분:초.백분의일초" 로 바꾼다. 0 이하는 기록 없음으로 본다. */
	static FString FormatTime(float Seconds);

private:
	void DrawLine(const FString& Text, float X, float Y, float Scale, const FLinearColor& Color, bool bCentered = false);
};
