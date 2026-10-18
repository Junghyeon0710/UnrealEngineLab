// 파쿠르 타임어택 HUD (Docs/UE/ParkourTimeAttack.md).

#include "ParkourCourse/ParkourHUD.h"

#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "ParkourCourse/ParkourGameMode.h"

FString AParkourHUD::FormatTime(float Seconds)
{
	if (Seconds <= 0.f)
	{
		return TEXT("--:--.--");
	}
	const int32 Hundredths = FMath::FloorToInt(Seconds * 100.f);
	return FString::Printf(TEXT("%02d:%02d.%02d"), Hundredths / 6000, (Hundredths / 100) % 60, Hundredths % 100);
}

void AParkourHUD::DrawLine(const FString& Text, float X, float Y, float Scale, const FLinearColor& Color, bool bCentered)
{
	FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(Text), GEngine->GetLargeFont(), Color);
	Item.Scale = FVector2D(Scale, Scale);
	Item.EnableShadow(FLinearColor(0.f, 0.f, 0.f, 0.8f), FVector2D(2.f, 2.f));
	Item.bCentreX = bCentered;
	Canvas->DrawItem(Item);
}

void AParkourHUD::DrawHUD()
{
	Super::DrawHUD();

	const AParkourGameMode* GameMode = GetWorld()->GetAuthGameMode<AParkourGameMode>();
	if (!GameMode || !Canvas)
	{
		return;
	}

	// 1080p 기준으로 잡고 화면 높이에 맞춰 키운다.
	const float UI = Canvas->ClipY / 1080.f;
	const float Left = 48.f * UI;
	float Y = 40.f * UI;

	const EParkourRunState State = GameMode->GetRunState();
	const FLinearColor TimeColor = State == EParkourRunState::Finished ? FLinearColor(0.3f, 1.f, 0.4f) : FLinearColor::White;
	DrawLine(TEXT("TIME  ") + FormatTime(GameMode->GetElapsedSeconds()), Left, Y, 2.8f * UI, TimeColor);
	Y += 84.f * UI;

	int32 Reached = 0;
	int32 Total = 0;
	GameMode->GetProgress(Reached, Total);
	DrawLine(FString::Printf(TEXT("CHECKPOINT  %d / %d"), Reached, Total), Left, Y, 1.8f * UI, FLinearColor(1.f, 0.85f, 0.3f));
	Y += 54.f * UI;
	DrawLine(TEXT("BEST  ") + FormatTime(GameMode->GetBestSeconds()), Left, Y, 1.8f * UI, FLinearColor(0.7f, 0.85f, 1.f));
	Y += 54.f * UI;
	if (GameMode->GetFallCount() > 0)
	{
		DrawLine(FString::Printf(TEXT("FALLS  %d"), GameMode->GetFallCount()), Left, Y, 1.8f * UI, FLinearColor(1.f, 0.5f, 0.4f));
	}

	const float CenterX = Canvas->ClipX * 0.5f;
	if (State == EParkourRunState::Ready)
	{
		DrawLine(TEXT("Run through the START gate"), CenterX, Canvas->ClipY * 0.72f, 2.f * UI, FLinearColor::White, true);
	}
	else if (State == EParkourRunState::Finished)
	{
		DrawLine(TEXT("FINISH  ") + FormatTime(GameMode->GetElapsedSeconds()), CenterX, Canvas->ClipY * 0.2f, 3.2f * UI,
			FLinearColor(0.3f, 1.f, 0.4f), true);
		if (GameMode->IsNewBest())
		{
			DrawLine(TEXT("NEW BEST!"), CenterX, Canvas->ClipY * 0.2f + 100.f * UI, 2.2f * UI, FLinearColor(1.f, 0.85f, 0.3f), true);
		}
	}
}
