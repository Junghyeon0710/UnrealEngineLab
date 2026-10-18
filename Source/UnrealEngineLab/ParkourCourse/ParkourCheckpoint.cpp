// 파쿠르 타임어택 코스의 체크포인트 (Docs/UE/ParkourTimeAttack.md).

#include "ParkourCourse/ParkourCheckpoint.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "ParkourCourse/ParkourGameMode.h"
#include "UObject/ConstructorHelpers.h"

namespace ParkourCheckpoint
{
	/** 엔진 기본 큐브는 한 변이 100cm다. */
	constexpr float CubeSize = 100.f;
	constexpr float PostThickness = 20.f;
}

AParkourCheckpoint::AParkourCheckpoint()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(SceneRoot);
	Trigger->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Trigger->SetCollisionResponseToAllChannels(ECR_Ignore);
	Trigger->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Trigger->SetGenerateOverlapEvents(true);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UMaterialInterface> ShapeMaterial(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));

	auto MakePart = [this](const TCHAR* Name) {
		UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Part->SetupAttachment(SceneRoot);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetCastShadow(false);
		return Part;
	};
	LeftPost = MakePart(TEXT("LeftPost"));
	RightPost = MakePart(TEXT("RightPost"));
	TopBar = MakePart(TEXT("TopBar"));
	for (UStaticMeshComponent* Part : { LeftPost.Get(), RightPost.Get(), TopBar.Get() })
	{
		Part->SetStaticMesh(Cube.Object);
		Part->SetMaterial(0, ShapeMaterial.Object);
	}

	Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
	Label->SetupAttachment(SceneRoot);
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetVerticalAlignment(EVRTA_TextBottom);
	Label->SetWorldSize(60.f);
	// 텍스트는 +X를 향한다. 문을 향해 달려오는 플레이어(-X 쪽)가 읽을 수 있게 뒤집는다.
	Label->SetRelativeRotation(FRotator(0.f, 180.f, 0.f));
}

void AParkourCheckpoint::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	LayoutGate();
}

void AParkourCheckpoint::LayoutGate()
{
	using namespace ParkourCheckpoint;

	Trigger->SetBoxExtent(GateExtent);
	Trigger->SetRelativeLocation(FVector(0.f, 0.f, GateExtent.Z));

	const float Height = GateExtent.Z * 2.f;
	const FVector PostScale(PostThickness / CubeSize, PostThickness / CubeSize, Height / CubeSize);
	LeftPost->SetRelativeScale3D(PostScale);
	RightPost->SetRelativeScale3D(PostScale);
	LeftPost->SetRelativeLocation(FVector(0.f, -GateExtent.Y, GateExtent.Z));
	RightPost->SetRelativeLocation(FVector(0.f, GateExtent.Y, GateExtent.Z));
	TopBar->SetRelativeScale3D(FVector(PostThickness / CubeSize, (GateExtent.Y * 2.f + PostThickness) / CubeSize, PostThickness / CubeSize));
	TopBar->SetRelativeLocation(FVector(0.f, 0.f, Height));

	FString Text;
	switch (Type)
	{
	case EParkourCheckpointType::Start:  Text = TEXT("START"); break;
	case EParkourCheckpointType::Finish: Text = TEXT("FINISH"); break;
	default:                             Text = FString::Printf(TEXT("CHECKPOINT %d"), Order); break;
	}
	Label->SetText(FText::FromString(Text));
	Label->SetRelativeLocation(FVector(0.f, 0.f, Height + PostThickness));
	Label->SetTextRenderColor(GetGateColor(false).ToFColor(true));
}

void AParkourCheckpoint::BeginPlay()
{
	Super::BeginPlay();

	GateMaterial = UMaterialInstanceDynamic::Create(LeftPost->GetMaterial(0), this);
	for (UStaticMeshComponent* Part : { LeftPost.Get(), RightPost.Get(), TopBar.Get() })
	{
		Part->SetMaterial(0, GateMaterial);
	}
	SetReached(false);

	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AParkourCheckpoint::HandleBeginOverlap);
}

FTransform AParkourCheckpoint::GetRespawnTransform() const
{
	// 문 바로 뒤(+X로 1.5m)에 캡슐 반 높이만큼 띄워서 세운다.
	const FVector Location = GetActorTransform().TransformPosition(FVector(150.f, 0.f, 100.f));
	return FTransform(FRotator(0.f, GetActorRotation().Yaw, 0.f), Location);
}

FLinearColor AParkourCheckpoint::GetGateColor(bool bReached) const
{
	if (bReached)
	{
		return FLinearColor(0.15f, 0.8f, 0.25f);
	}
	switch (Type)
	{
	case EParkourCheckpointType::Start:  return FLinearColor(0.1f, 0.45f, 1.f);
	case EParkourCheckpointType::Finish: return FLinearColor(1.f, 0.3f, 0.1f);
	default:                             return FLinearColor(1.f, 0.75f, 0.1f);
	}
}

void AParkourCheckpoint::SetReached(bool bReached)
{
	const FLinearColor Color = GetGateColor(bReached);
	if (GateMaterial)
	{
		GateMaterial->SetVectorParameterValue(TEXT("Color"), Color);
	}
	Label->SetTextRenderColor(Color.ToFColor(true));
}

void AParkourCheckpoint::HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	APawn* Pawn = Cast<APawn>(OtherActor);
	if (!Pawn || !Pawn->IsPlayerControlled())
	{
		return;
	}
	if (AParkourGameMode* GameMode = GetWorld()->GetAuthGameMode<AParkourGameMode>())
	{
		GameMode->NotifyCheckpointReached(this, Pawn);
	}
}
