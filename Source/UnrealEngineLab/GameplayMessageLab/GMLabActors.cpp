// GameplayMessage 실험의 표적과 포탑 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabActors.h"

#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/GameplayMessageSubsystem.h"
#include "GameplayMessageLab/GMLabMessages.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

AGMLabActorBase::AGMLabActorBase()
{
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Mesh->SetStaticMesh(Cube.Object);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
	Label->SetupAttachment(Mesh);
}

void AGMLabActorBase::Setup(const FString& InDisplayName, const FLinearColor& InColor)
{
	DisplayName = InDisplayName;
	BaseColor = InColor;
	Material = Mesh->CreateDynamicMaterialInstance(0, LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")));
	SetColor(InColor);
	// 글자 아래쪽을 큐브 위에 맞추고, 위에서 내려다보는 카메라 쪽으로 기울인다.
	Label->SetRelativeLocation(FVector(0.f, 0.f, 90.f));
	Label->SetRelativeRotation(FRotator(50.f, 180.f, 0.f));
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetVerticalAlignment(EVRTA_TextBottom);
	Label->SetWorldSize(36.f);
	SetLabel(InDisplayName);
}

void AGMLabActorBase::SetColor(const FLinearColor& InColor)
{
	if (Material)
	{
		Material->SetVectorParameterValue(TEXT("Color"), InColor);
	}
}

void AGMLabActorBase::SetLabel(const FString& InText)
{
	Label->SetText(FText::FromString(InText));
}

void AGMLabTarget::Setup(const FString& InDisplayName, const FLinearColor& InColor)
{
	Super::Setup(InDisplayName, InColor);
	UpdateLabel();
}

void AGMLabTarget::ApplyHit(AActor* Shooter, float Damage)
{
	if (!IsAlive())
	{
		return;
	}
	Health = FMath::Max(0.f, Health - Damage);
	UpdateLabel();

	UGameplayMessageSubsystem& Messages = UGameplayMessageSubsystem::Get(this);
	FGMLabCombatMessage Message;
	Message.Verb = TAG_GMLab_Message_Damage;
	Message.Instigator = Shooter;
	Message.Target = this;
	Message.Magnitude = Damage;
	Messages.BroadcastMessage(Message.Verb, Message);

	if (!IsAlive())
	{
		Message.Verb = TAG_GMLab_Message_Elimination;
		Messages.BroadcastMessage(Message.Verb, Message);

		SetActorHiddenInGame(true);
		GetWorldTimerManager().SetTimer(RespawnTimer, this, &AGMLabTarget::Respawn, 1.2f, false);
	}
}

void AGMLabTarget::Flash()
{
	SetColor(FLinearColor(1.f, 0.9f, 0.9f));
	GetWorldTimerManager().SetTimer(FlashTimer, [this]() { SetColor(BaseColor); }, 0.3f, false);
}

void AGMLabTarget::Respawn()
{
	Health = 100.f;
	SetActorHiddenInGame(false);
	SetColor(BaseColor);
	UpdateLabel();
}

void AGMLabTarget::UpdateLabel()
{
	SetLabel(FString::Printf(TEXT("%s\n%d"), *DisplayName, FMath::RoundToInt(Health)));
}
