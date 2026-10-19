// MVVM 실험 위젯을 만드는 에디터 도구 (Docs/UE/MVVM.md).

#include "MVVMLab/MVVMLabEditorLibrary.h"

#include "Bindings/MVVMConversionLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Editor.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "MVVMBlueprintFunctionReference.h"
#include "MVVMBlueprintPin.h"
#include "MVVMBlueprintView.h"
#include "MVVMBlueprintViewEvent.h"
#include "MVVMBlueprintViewModelContext.h"
#include "MVVMEditorSubsystem.h"
#include "MVVMPropertyPath.h"
#include "Types/MVVMBindingMode.h"
#include "Types/MVVMFieldVariant.h"
#include "WidgetBlueprint.h"

namespace MVVMLabEditor
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

	void AddRow(UVerticalBox* Rows, UWidget* Widget, float Bottom)
	{
		UVerticalBoxSlot* Slot = Rows->AddChildToVerticalBox(Widget);
		Slot->SetPadding(FMargin(0.f, 0.f, 0.f, Bottom));
	}

	UMVVMBlueprintView* GetView(UWidgetBlueprint* WidgetBlueprint)
	{
		return GEditor->GetEditorSubsystem<UMVVMEditorSubsystem>()->RequestView(WidgetBlueprint);
	}

	/** ViewModel 필드(속성 또는 FieldNotify 함수)를 가리키는 경로. */
	bool MakeViewModelPath(UWidgetBlueprint* WidgetBlueprint, FName ViewModelName, FName Field, FMVVMBlueprintPropertyPath& OutPath, FString& OutError)
	{
		const FMVVMBlueprintViewModelContext* Context = GetView(WidgetBlueprint)->FindViewModel(ViewModelName);
		if (!Context || !Context->GetViewModelClass())
		{
			OutError = FString::Printf(TEXT("ViewModel %s not found"), *ViewModelName.ToString());
			return false;
		}
		const UClass* Class = Context->GetViewModelClass();
		OutPath.ResetPropertyPath();
		OutPath.SetViewModelId(Context->GetViewModelId());
		if (const FProperty* Property = Class->FindPropertyByName(Field))
		{
			OutPath.SetPropertyPath(WidgetBlueprint, UE::MVVM::FMVVMConstFieldVariant(Property));
		}
		else if (const UFunction* Function = Class->FindFunctionByName(Field))
		{
			OutPath.SetPropertyPath(WidgetBlueprint, UE::MVVM::FMVVMConstFieldVariant(Function));
		}
		else
		{
			OutError = FString::Printf(TEXT("%s has no field %s"), *Class->GetName(), *Field.ToString());
			return false;
		}
		return true;
	}

	/** 위젯 속성 또는 이벤트를 가리키는 경로. 바인딩에 쓰는 위젯은 변수로 표시한다. */
	bool MakeWidgetPath(UWidgetBlueprint* WidgetBlueprint, FName WidgetName, FName Member, FMVVMBlueprintPropertyPath& OutPath, FString& OutError)
	{
		UWidget* Widget = WidgetBlueprint->WidgetTree->FindWidget(WidgetName);
		if (!Widget)
		{
			OutError = FString::Printf(TEXT("Widget %s not found"), *WidgetName.ToString());
			return false;
		}
		const FProperty* Property = Widget->GetClass()->FindPropertyByName(Member);
		if (!Property)
		{
			OutError = FString::Printf(TEXT("%s has no property %s"), *Widget->GetClass()->GetName(), *Member.ToString());
			return false;
		}
		Widget->bIsVariable = true;
		OutPath.ResetPropertyPath();
		OutPath.SetWidgetName(WidgetName);
		OutPath.SetPropertyPath(WidgetBlueprint, UE::MVVM::FMVVMConstFieldVariant(Property));
		return true;
	}
}

FString UMVVMLabEditorLibrary::BuildStatusWidgetTree(UWidgetBlueprint* WidgetBlueprint, const FString& Title, bool bCompact)
{
	using namespace MVVMLabEditor;
	if (!WidgetBlueprint || !WidgetBlueprint->WidgetTree)
	{
		return TEXT("No widget blueprint");
	}
	WidgetBlueprint->Modify();
	UWidgetTree* Tree = WidgetBlueprint->WidgetTree;
	Tree->Modify();
	Tree->RootWidget = nullptr;

	UBorder* Panel = Tree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Panel"));
	Panel->SetBrushColor(FLinearColor(0.02f, 0.03f, 0.05f, 0.82f));
	Panel->SetPadding(FMargin(20.f, 16.f));
	Tree->RootWidget = Panel;

	UVerticalBox* Rows = Tree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Rows"));
	Panel->SetContent(Rows);

	AddRow(Rows, MakeText(Tree, TEXT("TitleText"), Title, 16, FLinearColor(0.55f, 0.75f, 1.f)), 10.f);

	USizeBox* BarBox = Tree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("HealthBarBox"));
	BarBox->SetHeightOverride(bCompact ? 18.f : 22.f);
	UProgressBar* Bar = Tree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("HealthBar"));
	Bar->SetPercent(1.f);
	Bar->SetFillColorAndOpacity(FLinearColor(0.2f, 0.85f, 0.35f));
	BarBox->SetContent(Bar);
	AddRow(Rows, BarBox, 6.f);

	AddRow(Rows, MakeText(Tree, TEXT("HealthText"), TEXT("HP  - / -"), 18, FLinearColor::White), 4.f);
	if (!bCompact)
	{
		AddRow(Rows, MakeText(Tree, TEXT("AmmoText"), TEXT("AMMO  - / -"), 18, FLinearColor::White), 4.f);
		UTextBlock* Low = MakeText(Tree, TEXT("LowHealthText"), TEXT("LOW HEALTH"), 18, FLinearColor(1.f, 0.25f, 0.2f));
		AddRow(Rows, Low, 10.f);

		UButton* Button = Tree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("HealButton"));
		Button->SetContent(MakeText(Tree, TEXT("HealButtonText"), TEXT("HEAL +25"), 16, FLinearColor(0.05f, 0.05f, 0.05f)));
		AddRow(Rows, Button, 0.f);
		Button->bIsVariable = true;
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WidgetBlueprint);
	return FString();
}

FString UMVVMLabEditorLibrary::AddGlobalViewModel(UWidgetBlueprint* WidgetBlueprint, UClass* ViewModelClass, FName ViewModelName, FName GlobalIdentifier)
{
	using namespace MVVMLabEditor;
	if (!WidgetBlueprint || !ViewModelClass)
	{
		return TEXT("Missing widget blueprint or viewmodel class");
	}
	UMVVMEditorSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMVVMEditorSubsystem>();
	UMVVMBlueprintView* View = Subsystem->RequestView(WidgetBlueprint);
	const FGuid Id = Subsystem->AddViewModel(WidgetBlueprint, ViewModelClass);
	FMVVMBlueprintViewModelContext* Context = View->FindViewModel(Id);
	if (!Context)
	{
		return TEXT("AddViewModel failed");
	}
	FText Error;
	if (Context->GetViewModelName() != ViewModelName && !Subsystem->RenameViewModel(WidgetBlueprint, Context->GetViewModelName(), ViewModelName, Error))
	{
		return Error.ToString();
	}
	Context = View->FindViewModel(Id);
	Context->CreationType = EMVVMBlueprintViewModelContextCreationType::GlobalViewModelCollection;
	Context->GlobalViewModelIdentifier = GlobalIdentifier;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(WidgetBlueprint);
	return FString();
}

FString UMVVMLabEditorLibrary::AddViewModelBinding(UWidgetBlueprint* WidgetBlueprint, FName ViewModelName, FName SourceField, FName WidgetName, FName WidgetProperty)
{
	using namespace MVVMLabEditor;
	FString Error;
	FMVVMBlueprintPropertyPath Source;
	FMVVMBlueprintPropertyPath Destination;
	if (!MakeViewModelPath(WidgetBlueprint, ViewModelName, SourceField, Source, Error)
		|| !MakeWidgetPath(WidgetBlueprint, WidgetName, WidgetProperty, Destination, Error))
	{
		return Error;
	}
	UMVVMEditorSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMVVMEditorSubsystem>();
	FMVVMBlueprintViewBinding& Binding = Subsystem->AddBinding(WidgetBlueprint);
	Subsystem->SetSourcePathForBinding(WidgetBlueprint, Binding, Source);
	Subsystem->SetDestinationPathForBinding(WidgetBlueprint, Binding, Destination, false);
	Subsystem->SetBindingTypeForBinding(WidgetBlueprint, Binding, EMVVMBindingMode::OneWayToDestination);
	return FString();
}

FString UMVVMLabEditorLibrary::AddViewModelVisibilityBinding(UWidgetBlueprint* WidgetBlueprint, FName ViewModelName, FName SourceField, FName WidgetName)
{
	using namespace MVVMLabEditor;
	FString Error;
	FMVVMBlueprintPropertyPath Source;
	FMVVMBlueprintPropertyPath Destination;
	if (!MakeViewModelPath(WidgetBlueprint, ViewModelName, SourceField, Source, Error)
		|| !MakeWidgetPath(WidgetBlueprint, WidgetName, TEXT("Visibility"), Destination, Error))
	{
		return Error;
	}
	const UFunction* Conversion = UMVVMConversionLibrary::StaticClass()->FindFunctionByName(TEXT("Conv_BoolToSlateVisibility"));
	if (!Conversion)
	{
		return TEXT("Conv_BoolToSlateVisibility not found");
	}
	UMVVMEditorSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMVVMEditorSubsystem>();
	FMVVMBlueprintViewBinding& Binding = Subsystem->AddBinding(WidgetBlueprint);
	Subsystem->SetDestinationPathForBinding(WidgetBlueprint, Binding, Destination, false);
	Subsystem->SetBindingTypeForBinding(WidgetBlueprint, Binding, EMVVMBindingMode::OneWayToDestination);
	Subsystem->SetSourceToDestinationConversionFunction(WidgetBlueprint, Binding, FMVVMBlueprintFunctionReference(WidgetBlueprint, Conversion));
	const FName PinNames[] = { TEXT("bIsVisible") };
	Subsystem->SetPathForConversionFunctionArgument(WidgetBlueprint, Binding, FMVVMBlueprintPinId(MakeArrayView(PinNames)), Source, true);
	return FString();
}

FString UMVVMLabEditorLibrary::AddViewModelEvent(UWidgetBlueprint* WidgetBlueprint, FName WidgetName, FName WidgetEvent, FName ViewModelName, FName ViewModelFunction)
{
	using namespace MVVMLabEditor;
	FString Error;
	FMVVMBlueprintPropertyPath EventPath;
	FMVVMBlueprintPropertyPath Destination;
	if (!MakeWidgetPath(WidgetBlueprint, WidgetName, WidgetEvent, EventPath, Error)
		|| !MakeViewModelPath(WidgetBlueprint, ViewModelName, ViewModelFunction, Destination, Error))
	{
		return Error;
	}
	UMVVMEditorSubsystem* Subsystem = GEditor->GetEditorSubsystem<UMVVMEditorSubsystem>();
	UMVVMBlueprintViewEvent* Event = Subsystem->AddEvent(WidgetBlueprint);
	if (!Event)
	{
		return TEXT("AddEvent failed");
	}
	Subsystem->SetEventPath(Event, EventPath, false);
	Subsystem->SetEventDestinationPath(Event, Destination);
	return FString();
}

FString UMVVMLabEditorLibrary::AddClassicFunctionBinding(UWidgetBlueprint* WidgetBlueprint, FName WidgetName, FName WidgetProperty, FName FunctionName)
{
	if (!WidgetBlueprint || !WidgetBlueprint->WidgetTree->FindWidget(WidgetName))
	{
		return FString::Printf(TEXT("Widget %s not found"), *WidgetName.ToString());
	}
	UFunction* Function = WidgetBlueprint->ParentClass ? WidgetBlueprint->ParentClass->FindFunctionByName(FunctionName) : nullptr;
	if (!Function)
	{
		return FString::Printf(TEXT("Function %s not found on the parent class"), *FunctionName.ToString());
	}
	FDelegateEditorBinding Binding;
	Binding.ObjectName = WidgetName.ToString();
	Binding.PropertyName = WidgetProperty;
	Binding.FunctionName = Function->GetFName();
	Binding.Kind = EBindingKind::Function;
	TArray<FFieldVariant> Chain;
	Chain.Add(FFieldVariant(Function));
	Binding.SourcePath = FEditorPropertyPath(Chain);
	WidgetBlueprint->Modify();
	WidgetBlueprint->Bindings.Remove(Binding);
	WidgetBlueprint->Bindings.Add(Binding);
	FBlueprintEditorUtils::MarkBlueprintAsModified(WidgetBlueprint);
	return FString();
}

FString UMVVMLabEditorLibrary::CompileWidgetBlueprint(UWidgetBlueprint* WidgetBlueprint)
{
	if (!WidgetBlueprint)
	{
		return TEXT("No widget blueprint");
	}
	FCompilerResultsLog Results;
	Results.SetSourcePath(WidgetBlueprint->GetPathName());
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
