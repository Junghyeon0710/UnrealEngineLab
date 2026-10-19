// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

/** 에디터에서만 쓰는 실험 도구. 런타임 모듈(UnrealEngineLab)과 쿠킹된 게임에는 들어가지 않는다. */
public class UnrealEngineLabEditor : ModuleRules
{
	public UnrealEngineLabEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });

		// MVVM 실험용 위젯 생성 도구 (Docs/UE/MVVM.md)
		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate", "SlateCore", "UMG", "UMGEditor", "UnrealEd", "Kismet", "BlueprintGraph",
			"FieldNotification", "ModelViewViewModel", "ModelViewViewModelBlueprint", "ModelViewViewModelEditor",
			"UnrealEngineLab"
		});
	}
}
