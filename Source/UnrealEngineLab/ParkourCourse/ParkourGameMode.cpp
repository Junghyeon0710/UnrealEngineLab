// 파쿠르 타임어택 게임 규칙 (Docs/UE/ParkourTimeAttack.md).

#include "ParkourCourse/ParkourGameMode.h"

#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "ParkourCourse/ParkourCheckpoint.h"
#include "ParkourCourse/ParkourHUD.h"
#include "TimerManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogParkour, Log, All);

const FString AParkourGameMode::SaveSlotName = TEXT("ParkourCourse");

AParkourGameMode::AParkourGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	HUDClass = AParkourHUD::StaticClass();

	// Game Animation Sample에서 가져온 에셋. 경로는 샘플과 같다 (Scripts/ParkourCourse/gasp_packages.txt).
	CoursePawnClass = TSoftClassPtr<APawn>(FSoftObjectPath(TEXT("/Game/Blueprints/SandboxCharacter_Mover.SandboxCharacter_Mover_C")));
	CourseControllerClass = TSoftClassPtr<APlayerController>(FSoftObjectPath(TEXT("/Game/Blueprints/PC_Sandbox.PC_Sandbox_C")));
}

void AParkourGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);

	// 플레이어가 접속하기 전에 클래스를 바꿔 둔다. 못 찾으면 엔진 기본값으로 뜬다.
	if (UClass* PawnClass = CoursePawnClass.LoadSynchronous())
	{
		DefaultPawnClass = PawnClass;
	}
	else
	{
		UE_LOG(LogParkour, Error, TEXT("Course pawn %s is missing. Run Scripts/ParkourCourse/import_gasp_assets.py."), *CoursePawnClass.ToString());
	}
	if (UClass* ControllerClass = CourseControllerClass.LoadSynchronous())
	{
		PlayerControllerClass = ControllerClass;
	}
}

void AParkourGameMode::BeginPlay()
{
	Super::BeginPlay();

	for (TActorIterator<AParkourCheckpoint> It(GetWorld()); It; ++It)
	{
		Checkpoints.Add(*It);
	}
	Checkpoints.Sort([](const AParkourCheckpoint& A, const AParkourCheckpoint& B) { return A.Order < B.Order; });
	for (int32 Index = 0; Index < Checkpoints.Num(); ++Index)
	{
		if (Checkpoints[Index]->Order != Index)
		{
			UE_LOG(LogParkour, Warning, TEXT("Checkpoint orders should be 0..%d without gaps, found %d at %d."),
				Checkpoints.Num() - 1, Checkpoints[Index]->Order, Index);
		}
	}

	if (const UParkourSaveGame* Save = Cast<UParkourSaveGame>(UGameplayStatics::LoadGameFromSlot(SaveSlotName, 0)))
	{
		BestSeconds = Save->BestSeconds;
	}
	UpdateGateColors();
}

void AParkourGameMode::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	APlayerController* PlayerController = GetWorld()->GetFirstPlayerController();
	const APawn* Pawn = PlayerController ? PlayerController->GetPawn() : nullptr;
	if (Pawn && Pawn->GetActorLocation().Z < FallZ)
	{
		// 기록 중에 떨어진 것만 센다. 출발 전이나 결승 뒤에는 다시 세우기만 한다.
		if (RunState == EParkourRunState::Running)
		{
			++FallCount;
		}
		RespawnPlayer(PlayerController);
	}
}

void AParkourGameMode::NotifyCheckpointReached(AParkourCheckpoint* Checkpoint, APawn* Pawn)
{
	if (!Checkpoint)
	{
		return;
	}

	// 출발 문은 지날 때마다 새 기록을 시작한다.
	if (Checkpoint->Type == EParkourCheckpointType::Start)
	{
		StartRun();
		return;
	}

	// 나머지는 순서대로만 받는다. 건너뛰거나 되돌아간 문은 무시한다.
	if (RunState != EParkourRunState::Running || Checkpoint->Order != LastReachedOrder + 1)
	{
		return;
	}
	LastReachedOrder = Checkpoint->Order;
	UpdateGateColors();
	UE_LOG(LogParkour, Log, TEXT("Checkpoint %d at %.2fs"), LastReachedOrder, GetElapsedSeconds());

	if (Checkpoint->Type == EParkourCheckpointType::Finish)
	{
		FinishRun();
	}
}

void AParkourGameMode::StartRun()
{
	GetWorldTimerManager().ClearTimer(ReturnToStartTimer);
	RunState = EParkourRunState::Running;
	RunStartTime = GetWorld()->GetTimeSeconds();
	LastReachedOrder = 0;
	FallCount = 0;
	bNewBest = false;
	UpdateGateColors();
	UE_LOG(LogParkour, Log, TEXT("Run started"));
}

void AParkourGameMode::FinishRun()
{
	LastRunSeconds = static_cast<float>(GetWorld()->GetTimeSeconds() - RunStartTime);
	RunState = EParkourRunState::Finished;

	bNewBest = BestSeconds <= 0.f || LastRunSeconds < BestSeconds;
	if (bNewBest)
	{
		BestSeconds = LastRunSeconds;
		UParkourSaveGame* Save = Cast<UParkourSaveGame>(UGameplayStatics::CreateSaveGameObject(UParkourSaveGame::StaticClass()));
		Save->BestSeconds = BestSeconds;
		UGameplayStatics::SaveGameToSlot(Save, SaveSlotName, 0);
	}
	UE_LOG(LogParkour, Log, TEXT("Finished in %.2fs (best %.2fs, falls %d)"), LastRunSeconds, BestSeconds, FallCount);

	GetWorldTimerManager().SetTimer(ReturnToStartTimer, this, &AParkourGameMode::ReturnToStart, ReturnToStartDelay, false);
}

void AParkourGameMode::ReturnToStart()
{
	RunState = EParkourRunState::Ready;
	LastReachedOrder = INDEX_NONE;
	UpdateGateColors();
	RespawnPlayer(GetWorld()->GetFirstPlayerController());
}

void AParkourGameMode::RespawnPlayer(APlayerController* PlayerController)
{
	if (!PlayerController)
	{
		return;
	}

	FTransform SpawnTransform = FTransform::Identity;
	if (const AParkourCheckpoint* Last = FindCheckpoint(LastReachedOrder))
	{
		SpawnTransform = Last->GetRespawnTransform();
	}
	else if (const AActor* PlayerStart = FindPlayerStart(PlayerController))
	{
		SpawnTransform = PlayerStart->GetActorTransform();
	}

	// Mover 캐릭터는 위치를 자기 시뮬레이션 상태로 들고 있어서, 옮기는 대신 새로 만든다.
	if (APawn* OldPawn = PlayerController->GetPawn())
	{
		PlayerController->UnPossess();
		OldPawn->Destroy();
	}
	RestartPlayerAtTransform(PlayerController, SpawnTransform);
}

float AParkourGameMode::GetElapsedSeconds() const
{
	switch (RunState)
	{
	case EParkourRunState::Running:  return static_cast<float>(GetWorld()->GetTimeSeconds() - RunStartTime);
	case EParkourRunState::Finished: return LastRunSeconds;
	default:                         return 0.f;
	}
}

void AParkourGameMode::GetProgress(int32& OutReached, int32& OutTotal) const
{
	OutTotal = FMath::Max(Checkpoints.Num() - 1, 0);
	OutReached = FMath::Clamp(LastReachedOrder, 0, OutTotal);
}

AParkourCheckpoint* AParkourGameMode::FindCheckpoint(int32 Order) const
{
	for (AParkourCheckpoint* Checkpoint : Checkpoints)
	{
		if (Checkpoint && Checkpoint->Order == Order)
		{
			return Checkpoint;
		}
	}
	return nullptr;
}

void AParkourGameMode::UpdateGateColors()
{
	for (AParkourCheckpoint* Checkpoint : Checkpoints)
	{
		if (Checkpoint)
		{
			Checkpoint->SetReached(LastReachedOrder != INDEX_NONE && Checkpoint->Order <= LastReachedOrder);
		}
	}
}
