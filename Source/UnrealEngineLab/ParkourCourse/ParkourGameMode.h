// 파쿠르 타임어택 게임 규칙 (Docs/UE/ParkourTimeAttack.md).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/SaveGame.h"
#include "ParkourGameMode.generated.h"

class AParkourCheckpoint;

/** 최고 기록 저장용. 슬롯 이름은 AParkourGameMode::SaveSlotName. */
UCLASS()
class UNREALENGINELAB_API UParkourSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	/** 0이면 기록 없음. */
	UPROPERTY()
	float BestSeconds = 0.f;
};

UENUM(BlueprintType)
enum class EParkourRunState : uint8
{
	/** 출발 문을 아직 지나지 않음. */
	Ready,
	/** 타이머가 도는 중. */
	Running,
	/** 결승 문을 지남. 잠시 뒤 출발 지점으로 돌아간다. */
	Finished
};

/**
 * 파쿠르 타임어택 게임 모드.
 *
 * 캐릭터는 Game Animation Sample의 SandboxCharacter_Mover를 그대로 쓴다.
 * 이동은 Motion Matching, 장애물 넘기는 Motion Warping, 경사 발 디딤은 Control Rig가 맡고,
 * 이 클래스는 기록만 잰다 - 출발 문에서 타이머를 켜고, 체크포인트를 순서대로 지났는지 보고,
 * 떨어지면 마지막 체크포인트에서 다시 세우고, 결승 문에서 최고 기록을 저장한다.
 */
UCLASS()
class UNREALENGINELAB_API AParkourGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AParkourGameMode();

	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** AParkourCheckpoint가 플레이어 캡슐과 겹칠 때 부른다. */
	void NotifyCheckpointReached(AParkourCheckpoint* Checkpoint, APawn* Pawn);

	/** 마지막으로 지난 체크포인트(없으면 PlayerStart)에서 플레이어 캐릭터를 다시 만든다. */
	UFUNCTION(BlueprintCallable, Category = "Parkour")
	void RespawnPlayer(APlayerController* PlayerController);

	UFUNCTION(BlueprintPure, Category = "Parkour")
	EParkourRunState GetRunState() const { return RunState; }

	/** 달리는 중이면 지금까지, 끝났으면 이번 기록. */
	UFUNCTION(BlueprintPure, Category = "Parkour")
	float GetElapsedSeconds() const;

	UFUNCTION(BlueprintPure, Category = "Parkour")
	float GetBestSeconds() const { return BestSeconds; }

	UFUNCTION(BlueprintPure, Category = "Parkour")
	bool IsNewBest() const { return bNewBest; }

	/** 지난 체크포인트 수(출발 제외)와 전체 수(결승 포함). */
	UFUNCTION(BlueprintPure, Category = "Parkour")
	void GetProgress(int32& OutReached, int32& OutTotal) const;

	UFUNCTION(BlueprintPure, Category = "Parkour")
	int32 GetFallCount() const { return FallCount; }

	/** 플레이어 캐릭터. Game Animation Sample의 Mover 캐릭터. */
	UPROPERTY(EditDefaultsOnly, Category = "Parkour")
	TSoftClassPtr<APawn> CoursePawnClass;

	/** 입력 매핑과 카메라를 거는 샘플 컨트롤러. */
	UPROPERTY(EditDefaultsOnly, Category = "Parkour")
	TSoftClassPtr<APlayerController> CourseControllerClass;

	/** 캐릭터가 이 높이(cm)보다 아래로 떨어지면 다시 세운다. */
	UPROPERTY(EditAnywhere, Category = "Parkour")
	float FallZ = -300.f;

	/** 결승 후 출발 지점으로 돌아가기까지 기다리는 시간(초). */
	UPROPERTY(EditAnywhere, Category = "Parkour")
	float ReturnToStartDelay = 4.f;

	static const FString SaveSlotName;

private:
	void StartRun();
	void FinishRun();
	void ReturnToStart();
	void UpdateGateColors();
	AParkourCheckpoint* FindCheckpoint(int32 Order) const;

	/** Order 순으로 정렬. 0번이 출발, 마지막이 결승. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<AParkourCheckpoint>> Checkpoints;

	EParkourRunState RunState = EParkourRunState::Ready;
	int32 LastReachedOrder = INDEX_NONE;
	double RunStartTime = 0.0;
	float LastRunSeconds = 0.f;
	float BestSeconds = 0.f;
	bool bNewBest = false;
	int32 FallCount = 0;
	FTimerHandle ReturnToStartTimer;
};
