// GameplayMessage 실험 위젯을 만드는 에디터 도구 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabEditorLibrary.h"

#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "EdGraphSchema_K2.h"
#include "GameFramework/AsyncAction_ListenForGameplayMessage.h"
#include "K2Node_AsyncAction.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_ExecutionSequence.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "WidgetBlueprint.h"

namespace GMLabEditor
{
	UTextBlock* MakeText(UWidgetTree* Tree, FName Name, const FString& Text, int32 Size, const FLinearColor& Color)
	{
		UTextBlock* Block = Tree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), Name);
		Block->SetText(FText::FromString(Text));
		FSlateFontInfo Font = Block->GetFont();
		Font.Size = Size;
		Block->SetFont(Font);
		Block->SetColorAndOpacity(FSlateColor(Color));
		return Block;
	}

	/** Event Construct 뒤 Sequence 노드의 비어 있는 then 핀. Sequence가 없으면 만든다. */
	UEdGraphPin* FreeSequencePin(UEdGraph* Graph, UK2Node_Event* Construct)
	{
		UEdGraphPin* ConstructThen = Construct->FindPin(UEdGraphSchema_K2::PN_Then);
		UK2Node_ExecutionSequence* Sequence = ConstructThen->LinkedTo.Num() > 0
			? Cast<UK2Node_ExecutionSequence>(ConstructThen->LinkedTo[0]->GetOwningNode()) : nullptr;
		if (!Sequence)
		{
			Sequence = NewObject<UK2Node_ExecutionSequence>(Graph);
			Sequence->CreateNewGuid();
			Sequence->PostPlacedNewNode();
			Sequence->AllocateDefaultPins();
			Sequence->NodePosX = Construct->NodePosX + 260;
			Sequence->NodePosY = Construct->NodePosY;
			Graph->AddNode(Sequence, false, false);
			ConstructThen->MakeLinkTo(Sequence->GetExecPin());
		}
		for (int32 Attempt = 0; Attempt < 2; ++Attempt)
		{
			for (UEdGraphPin* Pin : Sequence->Pins)
			{
				if (Pin->Direction == EGPD_Output && Pin->LinkedTo.Num() == 0)
				{
					return Pin;
				}
			}
			Sequence->AddInputPin();
		}
		return nullptr;
	}
}

FString UGMLabEditorLibrary::BuildFeedWidgetTree(UWidgetBlueprint* WidgetBlueprint)
{
	using namespace GMLabEditor;
	if (!WidgetBlueprint || !WidgetBlueprint->WidgetTree)
	{
		return TEXT("No widget blueprint");
	}
	WidgetBlueprint->Modify();
	UWidgetTree* Tree = WidgetBlueprint->WidgetTree;
	Tree->Modify();

	UBorder* Panel = Tree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Panel"));
	Panel->SetBrushColor(FLinearColor(0.02f, 0.03f, 0.05f, 0.8f));
	Panel->SetPadding(FMargin(18.f, 14.f));
	Tree->RootWidget = Panel;

	UVerticalBox* Rows = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Rows"));
	Panel->SetContent(Rows);
	Rows->AddChildToVerticalBox(MakeText(Tree, TEXT("TitleText"), TEXT("ELIMINATION FEED"), 16, FLinearColor(0.55f, 0.75f, 1.f)))
		->SetPadding(FMargin(0.f, 0.f, 0.f, 8.f));

	UVerticalBox* Feed = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("FeedBox"));
	Feed->bIsVariable = true;
	Rows->AddChildToVerticalBox(Feed)->SetPadding(FMargin(0.f, 0.f, 0.f, 10.f));

	UTextBlock* Accolade = MakeText(Tree, TEXT("AccoladeText"), TEXT("DOUBLE KILL"), 26, FLinearColor(1.f, 0.8f, 0.2f));
	Accolade->SetVisibility(ESlateVisibility::Hidden);
	Accolade->bIsVariable = true;
	Rows->AddChildToVerticalBox(Accolade);

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WidgetBlueprint);
	return FString();
}

FString UGMLabEditorLibrary::AddMessageListenerNode(UWidgetBlueprint* WidgetBlueprint, FGameplayTag Channel, UScriptStruct* PayloadType,
	bool bPartialMatch, FName HandlerFunction, bool bPassChannel, int32 NodePosY)
{
	using namespace GMLabEditor;
	if (!WidgetBlueprint || !PayloadType || !Channel.IsValid())
	{
		return TEXT("Missing widget blueprint, payload type or channel");
	}
	UFunction* Handler = WidgetBlueprint->ParentClass ? WidgetBlueprint->ParentClass->FindFunctionByName(HandlerFunction) : nullptr;
	UClass* NodeClass = FindObject<UClass>(nullptr, TEXT("/Script/GameplayMessageNodes.K2Node_AsyncAction_ListenForGameplayMessages"));
	UFunction* Factory = UAsyncAction_ListenForGameplayMessage::StaticClass()->FindFunctionByName(TEXT("ListenForGameplayMessages"));
	if (!Handler || !NodeClass || !Factory)
	{
		return TEXT("Handler, node class or factory function not found");
	}
	UEdGraph* Graph = FBlueprintEditorUtils::FindEventGraph(WidgetBlueprint);
	UK2Node_Event* Construct = FBlueprintEditorUtils::FindOverrideForFunction(WidgetBlueprint, UUserWidget::StaticClass(), TEXT("Construct"));
	if (!Construct)
	{
		int32 PosY = 0;
		Construct = FKismetEditorUtilities::AddDefaultEventNode(WidgetBlueprint, Graph, TEXT("Construct"), UUserWidget::StaticClass(), PosY);
	}
	Construct->NodePosX = -300;
	Construct->NodePosY = 220;
	// 기본으로 놓인 노드라 "비활성 상태" 말풍선이 붙어 있다. 실행 줄을 이으니 켜고 말풍선을 지운다.
	Construct->SetEnabledState(ENodeEnabledState::Enabled, false);
	Construct->NodeComment.Empty();
	Construct->bCommentBubbleVisible = false;

	// 새 위젯 블루프린트에 비활성으로 놓이는 PreConstruct, Tick은 쓰지 않으니 지운다.
	TArray<UEdGraphNode*> Ghosts;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		if (Node != Construct && Node->IsAutomaticallyPlacedGhostNode())
		{
			Ghosts.Add(Node);
		}
	}
	for (UEdGraphNode* Node : Ghosts)
	{
		FBlueprintEditorUtils::RemoveNode(WidgetBlueprint, Node, true);
	}

	// Listen for Gameplay Messages
	UK2Node_AsyncAction* Listen = NewObject<UK2Node_AsyncAction>(Graph, NodeClass);
	Listen->InitializeProxyFromFunction(Factory);
	Listen->CreateNewGuid();
	Listen->PostPlacedNewNode();
	Listen->AllocateDefaultPins();
	Listen->NodePosX = 240;
	Listen->NodePosY = NodePosY;
	Graph->AddNode(Listen, false, false);

	UEdGraphPin* ChannelPin = Listen->FindPin(TEXT("Channel"));
	UEdGraphPin* TypePin = Listen->FindPin(TEXT("PayloadType"));
	UEdGraphPin* MatchPin = Listen->FindPin(TEXT("MatchType"));
	if (!ChannelPin || !TypePin || !MatchPin)
	{
		return TEXT("Listen node pins not found");
	}
	ChannelPin->DefaultValue = FString::Printf(TEXT("(TagName=\"%s\")"), *Channel.ToString());
	TypePin->DefaultObject = PayloadType;
	Listen->PinDefaultValueChanged(TypePin);
	MatchPin->DefaultValue = bPartialMatch ? TEXT("PartialMatch") : TEXT("ExactMatch");

	if (UEdGraphPin* Then = FreeSequencePin(Graph, Construct))
	{
		Then->MakeLinkTo(Listen->GetExecPin());
	}

	// 메시지가 오면 부를 함수
	UK2Node_CallFunction* Call = NewObject<UK2Node_CallFunction>(Graph);
	Call->SetFromFunction(Handler);
	Call->CreateNewGuid();
	Call->PostPlacedNewNode();
	Call->AllocateDefaultPins();
	Call->NodePosX = 720;
	Call->NodePosY = NodePosY + 60;
	Graph->AddNode(Call, false, false);

	UEdGraphPin* Received = Listen->FindPin(TEXT("OnMessageReceived"));
	UEdGraphPin* Payload = Listen->FindPin(TEXT("Payload"));
	UEdGraphPin* MessageArg = Call->FindPin(TEXT("Message"));
	if (!Received || !Payload || !MessageArg)
	{
		return TEXT("OnMessageReceived, Payload or Message pin not found");
	}
	Received->MakeLinkTo(Call->GetExecPin());
	Payload->MakeLinkTo(MessageArg);
	if (bPassChannel)
	{
		UEdGraphPin* ActualChannel = Listen->FindPin(TEXT("ActualChannel"));
		UEdGraphPin* ChannelArg = Call->FindPin(TEXT("ActualChannel"));
		if (!ActualChannel || !ChannelArg)
		{
			return TEXT("ActualChannel pins not found");
		}
		ActualChannel->MakeLinkTo(ChannelArg);
	}
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WidgetBlueprint);
	return FString();
}

FString UGMLabEditorLibrary::CompileBlueprint(UWidgetBlueprint* WidgetBlueprint)
{
	if (!WidgetBlueprint)
	{
		return TEXT("No widget blueprint");
	}
	FCompilerResultsLog Results;
	FKismetEditorUtilities::CompileBlueprint(WidgetBlueprint, EBlueprintCompileOptions::None, &Results);
	FString Out;
	for (const TSharedRef<FTokenizedMessage>& Message : Results.Messages)
	{
		if (Message->GetSeverity() <= EMessageSeverity::Warning)
		{
			Out += Message->ToText().ToString() + TEXT("\n");
		}
	}
	if (WidgetBlueprint->Status == BS_Error && Out.IsEmpty())
	{
		Out = TEXT("Compile failed");
	}
	return Out;
}
