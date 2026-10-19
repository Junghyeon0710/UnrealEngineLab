// MVVM 실험 위젯을 만드는 에디터 도구 (Docs/UE/MVVM.md).

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "MVVMLabEditorLibrary.generated.h"

class UWidgetBlueprint;

/**
 * 위젯 블루프린트의 위젯 트리와 바인딩을 코드로 만든다. 에디터 Python에서 부른다.
 *
 * 디자이너에서 손으로 하는 일과 같은 것을 한다. 위젯을 배치하고, Viewmodels 패널에 ViewModel을 추가하고,
 * View Bindings 패널에 줄을 추가한다. MVVM 에디터 서브시스템의 경로 지정 함수가 C++에만 열려 있어서
 * Python에서 바로 부를 수 없기 때문에 여기서 감쌌다. 실패하면 이유를 문자열로 돌려준다(성공은 빈 문자열).
 */
UCLASS()
class UMVVMLabEditorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * 위젯 트리를 새로 만든다.
	 *   Panel(Border) > Rows(VerticalBox) > TitleText, HealthBarBox(SizeBox) > HealthBar, HealthText,
	 *   AmmoText, LowHealthText, HealButton > HealButtonText
	 * bCompact면 TitleText, HealthBar, HealthText만 둔다.
	 */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString BuildStatusWidgetTree(UWidgetBlueprint* WidgetBlueprint, const FString& Title, bool bCompact);

	/** Viewmodels 패널에 ViewModel을 추가한다. 생성 방식은 Global Viewmodel Collection. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString AddGlobalViewModel(UWidgetBlueprint* WidgetBlueprint, UClass* ViewModelClass, FName ViewModelName, FName GlobalIdentifier);

	/** View Bindings에 ViewModel 필드 -> 위젯 속성 한 줄(One Way To Widget)을 추가한다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString AddViewModelBinding(UWidgetBlueprint* WidgetBlueprint, FName ViewModelName, FName SourceField, FName WidgetName, FName WidgetProperty);

	/** bool 필드를 Visibility에 바인딩한다. 변환 함수는 MVVM 플러그인의 To Visibility (Boolean). */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString AddViewModelVisibilityBinding(UWidgetBlueprint* WidgetBlueprint, FName ViewModelName, FName SourceField, FName WidgetName);

	/** View Bindings에 이벤트 한 줄을 추가한다. 위젯 이벤트(예: Button.OnClicked)가 오면 ViewModel 함수를 부른다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString AddViewModelEvent(UWidgetBlueprint* WidgetBlueprint, FName WidgetName, FName WidgetEvent, FName ViewModelName, FName ViewModelFunction);

	/** 기존 UMG 속성 바인딩. 위젯 속성(예: Text)을 위젯 클래스의 함수에 묶는다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString AddClassicFunctionBinding(UWidgetBlueprint* WidgetBlueprint, FName WidgetName, FName WidgetProperty, FName FunctionName);

	/** 컴파일하고 에러/경고를 돌려준다. */
	UFUNCTION(BlueprintCallable, Category = "MVVMLab")
	static FString CompileWidgetBlueprint(UWidgetBlueprint* WidgetBlueprint);
};
