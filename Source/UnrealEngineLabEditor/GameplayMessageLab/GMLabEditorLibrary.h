// GameplayMessage 실험 위젯을 만드는 에디터 도구 (Docs/UE/GameplayMessage.md).

#pragma once

#include "CoreMinimal.h"
#include "GameplayTagContainer.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GMLabEditorLibrary.generated.h"

class UWidgetBlueprint;

/**
 * 킬 피드 위젯(WBP_GMLabFeed)의 위젯 트리와 이벤트 그래프를 만든다. 에디터 Python에서 부른다.
 * 그래프에는 블루프린트에서 손으로 놓는 것과 같은 "Listen for Gameplay Messages" 노드를 놓는다.
 * 실패하면 이유를 문자열로 돌려준다(성공은 빈 문자열).
 */
UCLASS()
class UGMLabEditorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Panel(Border) > Rows(VerticalBox) > TitleText, FeedBox(VerticalBox), AccoladeText */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	static FString BuildFeedWidgetTree(UWidgetBlueprint* WidgetBlueprint);

	/**
	 * Event Construct 뒤 Sequence에 Listen for Gameplay Messages 노드를 잇고, 메시지가 오면 부모 클래스의 HandlerFunction을 부르게 한다.
	 * Payload는 HandlerFunction의 Message 인자로, bPassChannel이면 ActualChannel도 같은 이름의 인자로 넘긴다.
	 */
	UFUNCTION(BlueprintCallable, Category = "GMLab")
	static FString AddMessageListenerNode(UWidgetBlueprint* WidgetBlueprint, FGameplayTag Channel, UScriptStruct* PayloadType,
		bool bPartialMatch, FName HandlerFunction, bool bPassChannel, int32 NodePosY);

	UFUNCTION(BlueprintCallable, Category = "GMLab")
	static FString CompileBlueprint(UWidgetBlueprint* WidgetBlueprint);
};
