# Unreal MCP 툴셋 전체 목록

[연결·구조·사용 예제 본문](UnrealMCP.md)

2026-10-23 UE 5.8.3 실행 세션의 실제 `describe_toolset` 응답에서 생성했다. 53개 툴셋, 836개 도구다. 목록 조회는 전체 완료했으며, 모든 도구를 실행 검증한 것은 아니다. 이름을 클릭하면 원본 스키마를 볼 수 있다. `AIWidgetInspector`는 프로젝트 전용 확장이다.

## AgentSkillToolset

식별자: `ToolsetRegistry.AgentSkillToolset` · 4개 도구

스킬의 나열, 읽기, 생성/업데이트에 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/ToolsetRegistry.AgentSkillToolset.json)

도구: `UpdateSkill`, `ListSkills`, `GetSkills`, `CreateSkill`

## AutomationTestToolset

식별자: `AutomationTestToolset.AutomationTestToolset` · 7개 도구

자동화 테스트 검색 및 실행 툴세트입니다.

세션 프론트엔드가 사용하는 것과 동일한 백엔드인 IAutomationControllerManager API를
래핑하며, MCP 클라이언트가 사용 가능한 테스트를 나열하고 실행하여 결과를
얻을 수 있도록 합니다.

일반적인 워크플로:
  1. 세션별로 한 번 DiscoverTests()를 호출하여 워커를 초기화하고 테스트 목록을 로드합니다.
  2. ListTests()로 이름 또는 태그별 테스트를 찾습니다.
  3. 원하는 테스트 이름으로 RunTests()를 실행합니다.
  4. GetTestStatus()/GetTestResults()로 결과를 모니터링하고 얻습니다.
  5. 필요한 경우 StopTests()로 중단합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/AutomationTestToolset.AutomationTestToolset.json)

도구: `StopTests`, `RunTestsByFilter`, `RunTests`, `ListTests`, `GetTestStatus`, `GetTestResults`, `DiscoverTests`

## ConfigSettingsToolset

식별자: `ConfigSettingsToolset.ConfigSettingsToolset` · 8개 도구

환경설정 세팅 섹션을 나열, 검사 및 편집하는 데 사용되는 툴입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/ConfigSettingsToolset.ConfigSettingsToolset.json)

도구: `SetSectionProperties`, `SaveSection`, `ResetSectionToDefaults`, `ListSections`, `ListContainers`, `ListCategories`, `GetSectionSchema`, `GetSectionPropertyValues`

## DataflowAgentToolset

식별자: `DataflowAgent.DataflowAgentToolset` · 22개 도구

데이터플로 에이전트 툴세트로, 데이터플로 그래프 편집 오퍼레이션을 AI 에이전트 툴로 노출합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/DataflowAgent.DataflowAgentToolset.json)

도구: `UpdateNode`, `SetVariable`, `RepositionNode`, `RemoveVariable`, `RemoveNode`, `RemoveCommentBox`, `ListVariables`, `ListNodeTypes`, `ListDataflowTemplatesForAssetClass`, `ListDataflowCompatibleAssetTypes`, `GetNodeTypeSchema`, `GetNodeInfo`, `GetGraphStructure`, `DisconnectNodePins`, `CreateGraph`, `CreateDataflowCompatibleAssetFromTemplate`, `CreateDataflowCompatibleAsset`, `ConnectNodePins`, `AssignDataflowTemplate`, `AddVariable`, `AddNode`, `AddCommentBox`

## GameplayTagsToolset

식별자: `GameplayTagsToolset.GameplayTagsToolset` · 6개 도구

프로젝트의 GameplayTagsManager에서 게임플레이 태그를 읽고 관리하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/GameplayTagsToolset.GameplayTagsToolset.json)

도구: `RenameTag`, `RemoveTag`, `ListTags`, `GetTagInfo`, `FindReferencersByTag`, `AddTag`

## GameFeaturesToolset

식별자: `GameFeaturesToolset.GameFeaturesToolset` · 7개 도구

게임 피처 플러그인을 나열, 활성화 및 비활성화하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/GameFeaturesToolset.GameFeaturesToolset.json)

도구: `RequestDeactivateGameFeature`, `RequestActivateGameFeature`, `ListEnabledGameFeaturePlugins`, `ListDiscoveredGameFeaturePlugins`, `IsGameFeaturePlugin`, `IsGameFeatureActive`, `GetGameFeatureState`

## GameplayCueToolset

식별자: `GASToolsets.GameplayCueToolset` · 8개 도구

게임플레이 큐와 해당 노티파이 에셋을 검사, 실행 및 관리하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/GASToolsets.GameplayCueToolset.json)

도구: `RemoveCueTag`, `ListCues`, `GetCueInfo`, `FindCueTagsWithoutNotifies`, `FindCueNotifyAssets`, `ExecuteCueOnSelectedActor`, `CreateCueNotifyAsset`, `AddCueTag`

## AttributeSetToolset

식별자: `GASToolsets.AttributeSetToolset` · 2개 도구

AttributeSet 클래스와 해당 게임플레이 어트리뷰트를 검색하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/GASToolsets.AttributeSetToolset.json)

도구: `ListAttributes`, `FindAttributeSetClasses`

## AbilitySystemInspectorToolset

식별자: `GASToolsets.AbilitySystemInspectorToolset` · 4개 도구

AbilitySystemComponent의 런타임 스테이트를 검사하는 데 사용되는 툴을 제공합니다.
각 함수는 직접 액터 포인터를 취하며, 액터가 null이거나 AbilitySystemComponent가
없는 경우 스크립트 오류가 발생합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/GASToolsets.AbilitySystemInspectorToolset.json)

도구: `GetGrantedAbilities`, `GetAttributeValues`, `GetActiveTags`, `GetActiveEffects`

## DataRegistryTools

식별자: `DataRegistryToolset.DataRegistryTools` · 7개 도구

데이터 레지스트리를 쿼리하고 검사하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/DataRegistryToolset.DataRegistryTools.json)

도구: `ListRuntimeSources`, `ListRegistries`, `ListItems`, `ListDataSources`, `GetSchema`, `GetRegistryInfo`, `GetItems`

## EditorAppToolset

식별자: `EditorToolset.EditorAppToolset` · 21개 도구

언리얼 에디터 스테이트를 쿼리하고 수정하는 데 사용되는 툴입니다. 콘솔 변수,
에셋 이미징, 액터 및 에셋 선택, 뷰포트 카메라, 콘텐츠 브라우저 탐색, 에디터에서 플레이 세션 제어
등을 지원합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/EditorToolset.EditorAppToolset.json)

도구: `WorldPosToScreenCoords`, `StopPIE`, `StartPIE`, `SetContentBrowserPath`, `SetCameraTransform`, `SelectAssets`, `SelectActors`, `SearchCVars`, `ScreenCoordsToWorld`, `OpenEditorForAsset`, `IsPIERunning`, `GetVisibleActors`, `GetSelectedAssets`, `GetSelectedActors`, `GetOpenAssets`, `GetContentBrowserPath`, `GetCameraTransform`, `FocusOnActors`, `CaptureViewport`, `CaptureEditorImage`, `CaptureAssetImage`

## LogsToolset

식별자: `EditorToolset.LogsToolset` · 4개 도구

언리얼 엔진 출력 로그를 읽고 로그 카테고리의 상세도를
제어하는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/EditorToolset.LogsToolset.json)

도구: `SetVerbosity`, `GetVerbosity`, `GetLogEntries`, `GetLogCategories`

## NiagaraToolset_Info

식별자: `NiagaraToolsets.NiagaraToolset_Info` · 1개 도구

일반적인 나이아가라 정보 및 가이드를 위한 나이아가라 툴세트입니다.

제공:
- 열거형 값 조회
- 일반적인 사용 정보

나이아가라 타입에 대한 컨텍스트가 필요한 경우 이 함수를 호출하세요.

[원본 입력·반환 스키마](Evidence/UnrealMCP/NiagaraToolsets.NiagaraToolset_Info.json)

도구: `UEnum_Info`

## NiagaraToolset_Component

식별자: `NiagaraToolsets.NiagaraToolset_Component` · 4개 도구

나이아가라 컴포넌트 오퍼레이션을 위한 나이아가라 툴세트입니다.

다음으로 작업할 경우 이 툴세트를 사용하세요.
- 액터의 나이아가라 컴포넌트
- 런타임 나이아가라 시스템 조작
- 컴포넌트 인스턴스에서 사용자 변수 오버라이드
- 레벨 또는 블루프린트 내 FX 관련 오퍼레이션

이는 런타임 나이아가라 오퍼레이션을 위한 주요 툴세트입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/NiagaraToolsets.NiagaraToolset_Component.json)

도구: `SetVariable`, `SetSystem`, `GetVariable`, `GetUserVariables`

## NiagaraToolset_Blueprint

식별자: `NiagaraToolsets.NiagaraToolset_Blueprint` · 2개 도구

나이아가라 및 블루프린트 통합을 위한 나이아가라 툴세트입니다.

나이아가라 시스템을 감싸는 블루프린트 래퍼를 생성하는 데 사용할 수 있는 유틸리티를 제공하며,
나이아가라 이펙트를 재사용 가능한 블루프린트 액터로 노출하기 쉽게 만들어줍니다.

나이아가라 시스템에서 블루프린트 기반 FX 액터를 생성해야 하는 경우 이 툴세트를 사용하세요.

[원본 입력·반환 스키마](Evidence/UnrealMCP/NiagaraToolsets.NiagaraToolset_Blueprint.json)

도구: `ConstructNiagaraBPWrapperFromSystem`, `ConstructNiagaraBPWrapperFromComponent`

## NiagaraToolset_System

식별자: `NiagaraToolsets.NiagaraToolset_System` · 46개 도구

나이아가라 시스템 오퍼레이션을 위한 나이아가라 툴세트입니다.

다음을 포함하여 나이아가라 시스템 편집에 대한 포괄적인 액세스를 제공합니다.
- 시스템, 이미터, 모듈 생성과 수정
- 구조 이해를 위한 스키마 검색
- 현재 환경설정을 보기 위한 토폴로지 및 요약 검사
- 프로퍼티 읽기 및 쓰기를 위한 데이터 액세스
- GetSystemDependencies를 통한 종속성 롤업
- GetDynamicInputChain을 통한 다이내믹 입력 체인 탐색

이는 에디터에서 나이아가라 시스템으로 작업하기 위한 주요 툴세트입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/NiagaraToolsets.NiagaraToolset_System.json)

도구: `SetSystemData`, `SetStackInputData`, `SetRendererData`, `SetModuleEnabled`, `SetEmitterData`, `RemoveUserVariables`, `RemoveSetParameterEntry`, `RemoveRenderer`, `RemoveModule`, `RemoveEmitter`, `GetUserVariables`, `GetSystemSummary`, `GetSystemSchema`, `GetSystemDependencies`, `GetSystemData`, `GetSystemCompileState`, `GetStackIssues`, `GetStackInputTopology`, `GetStackInputSchema`, `GetStackInputData`, `GetScriptStackTopology`, `GetScriptStackInputValues`, `GetRendererSchema`, `GetRendererData`, `GetModuleTopology`, `GetModuleSchemaFromAsset`, `GetModuleSchema`, `GetModuleInputValues`, `GetEmitterTopology`, `GetEmitterSummary`, `GetEmitterSchema`, `GetEmitterInputValues`, `GetEmitterData`, `GetDynamicInputSchemaFromAsset`, `GetDynamicInputSchema`, `GetDynamicInputChain`, `GetDataInterfaceSchema`, `GetAvailableDynamicInputs`, `CreateNiagaraSystem`, `ApplyStackIssueFix`, `AddUserVariables`, `AddSetParametersModule`, `AddSetParameterEntry`, `AddRenderer`, `AddModule`, `AddEmitter`

## NiagaraToolset_Assets

식별자: `NiagaraToolsets.NiagaraToolset_Assets` · 3개 도구

나이아가라 스크립트 에셋을 검색하는 데 사용되는 나이아가라 툴세트입니다.

제공:
- GetAssetDiscoveryInfo: 프로젝트에 환경설정된 에셋 검색 그룹
- FindNiagaraScripts: 사용 용도, 비저빌리티, 이름, 모듈 사용 비트마스크로 필터링된 에셋 레지스트리 검색
- GetNiagaraScriptDigest: 단일 스크립트에 대한 디코딩된 에셋 레지스트리 태그

모든 함수는 LoadObject 없이 에셋 레지스트리에서 데이터를 읽습니다. 검색된 모듈을 스택에 드롭하려면
NiagaraToolset_System.AddModule과 쌍으로 연결하세요.

참고: FAssetData의 JSON 시리얼라이제이션에는 TagsAndValues 맵이 포함되지 않으므로
(UPROPERTY가 아님), FindNiagaraScripts의 결과 행에서 디코딩된 메타데이터를
원하는 호출자는 GetNiagaraScriptDigest를 거치는 라운드트립을 수행해야 합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/NiagaraToolsets.NiagaraToolset_Assets.json)

도구: `GetNiagaraScriptDigest`, `GetAssetDiscoveryInfo`, `FindNiagaraScripts`

## PCGToolset

식별자: `PCGToolset.PCGToolset` · 30개 도구

PCG 그래프를 빌드 및 수정하는 데 사용되는 툴세트입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/PCGToolset.PCGToolset.json)

도구: `UpdateNode`, `UpdateCommentBox`, `SpawnGraphInstance`, `SetNodeComment`, `SetGraphParams`, `SetGraphInstanceParams`, `SetGraphDescription`, `ResetGraphInstanceParams`, `RepositionNode`, `RemoveNode`, `RemoveGraphParams`, `RemoveCommentBox`, `ListNativeNodes`, `ListGraphInstances`, `ListAvailableSubgraphs`, `GetNodeInfo`, `GetNodeDataView`, `GetNativeNodeSchema`, `GetGraphStructure`, `GetGraphSchema`, `GetGraphInstanceParams`, `GetGraphDescription`, `ExecuteGraphInstance`, `DrawSpline`, `DisconnectNodePins`, `CreateGraph`, `ConnectNodePins`, `AddSubgraphNode`, `AddNode`, `AddCommentBox`

## PCGSpatialToolset

식별자: `PCGToolset.PCGSpatialToolset` · 1개 도구

PCGSpatial Toolset

[원본 입력·반환 스키마](Evidence/UnrealMCP/PCGToolset.PCGSpatialToolset.json)

도구: `RunPCGInstantGraph`

## PhysicsAssetToolset

식별자: `PhysicsToolsets.PhysicsAssetToolset` · 17개 도구

피직스 에셋을 생성하고 관리하는 데 사용되는 툴을 제공합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/PhysicsToolsets.PhysicsAssetToolset.json)

도구: `SetSphere`, `SetConstraintLimits`, `SetCapsule`, `SetBox`, `SetBodyPhysicsMode`, `SetBodyMassScale`, `RemoveShape`, `RemoveConstraint`, `RemoveBody`, `GetConstraints`, `GetBodyShapes`, `GetBodyPhysicsMode`, `GetBodyNames`, `GetBodyMassScale`, `CreateFromMesh`, `AddConstraint`, `AddBody`

## PluginToolset

식별자: `PluginToolset.PluginToolset` · 17개 도구

언리얼 플러그인을 생성, 편집, 활성화 및 쿼리하는 데 사용되는 툴입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/PluginToolset.PluginToolset.json)

도구: `ValidateNewPluginNameAndLocation`, `UpdatePluginDescriptor`, `SetPluginEnabled`, `RemovePluginDependency`, `ListEnabledPlugins`, `ListDiscoveredPlugins`, `IsPluginModificationAllowed`, `IsPluginCreationAllowed`, `IsEnabled`, `GetPluginTemplateDescriptions`, `GetPluginInfo`, `GetPluginForAsset`, `GetPluginDescriptor`, `GetPluginDependents`, `GetPluginDependencies`, `CreatePlugin`, `AddPluginDependency`

## SlateInspectorToolset

식별자: `SlateInspectorToolset.SlateInspectorToolset` · 14개 도구

플레이라이트 스타일의 슬레이트 UI 자동화 툴세트입니다.

언리얼 에디터 UI를 프로그래밍 방식으로 제어하는 데 사용되는
스냅샷, 스크린샷, 인터랙션 툴을 노출합니다.  ModelContextProtocol 플러그인이
이를 자동으로 탐지할 수 있도록 UToolsetRegistry를 통해 등록됩니다.

얕은 루트 관찰자(뎁스 0)가 최상위 창을 지속적으로
트래킹합니다.  특정 창 또는 패널로 작업하기 전에 Observe()를 호출하여
깊은 위젯 커버리지를 확보하고, 작업이 끝나면 Unobserve()를
호출하세요.  관찰자는 약 100ms마다 서브트리를 순회하여 새로 나타난 위젯에 레퍼런스를 할당하고
레퍼런스 캐시를 최신 상태로 유지합니다.

입력 시뮬레이션은 AutomationDriver 대신 직접 슬레이트 이벤트 API(ProcessKeyCharEvent,
ProcessMouseButtonDownEvent 등)를 사용합니다. AutomationDriver의
동기식 API는 게임 스레드(MCP 툴 호출이 실행되는 위치)에서 호출될 때
데드록을 유발하기 때문입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/SlateInspectorToolset.SlateInspectorToolset.json)

도구: `Windows`, `WaitFor`, `Unobserve`, `Type`, `Snapshot`, `SelectOption`, `Screenshot`, `PressKey`, `Observe`, `ListObservers`, `Hover`, `FillForm`, `Drag`, `Click`

## SemanticSearchToolset

식별자: `SemanticSearchToolset.SemanticSearchToolset` · 2개 도구

SemanticSearch 플러그인의 하이브리드 벡터 + BM25 에셋 검색 기능을 AI 툴세트 레지스트리에
노출하는 툴세트입니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/SemanticSearchToolset.SemanticSearchToolset.json)

도구: `Search`, `FindSimilar`

## WorldConditionTools

식별자: `WorldConditionsToolset.WorldConditionTools` · 2개 도구

월드 조건(FWorldConditionQueryDefinition, FWorldConditionBase) 구조체를 검사합니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/WorldConditionsToolset.WorldConditionTools.json)

도구: `GetQueryDescription`, `GetConditionDescription`

## AIWidgetInspectorToolset

식별자: `AIWidgetInspector.AIWidgetInspectorToolset` · 6개 도구

Lets an AI assistant read and change the widget the user has selected in the editor.

Unreal's ModelContextProtocol plugin exposes these functions as MCP tools, so an AI CLI calls
them directly instead of returning JSON for the plugin to interpret. It sees each result and can
correct itself. No server of our own: the engine already ships one.

These functions are the whitelist. Arguments go through the same parser and validator as the
response-JSON path, so neither route can drift into accepting what the other rejects.

The comment above each function is what the model reads when choosing a tool. English on
purpose — it is the one language every assistant handles well, whatever the user is typing.

[원본 입력·반환 스키마](Evidence/UnrealMCP/AIWidgetInspector.AIWidgetInspectorToolset.json)

도구: `SaveWidgetAsset`, `RevertPreview`, `PreviewWidgetChange`, `ListWidgetTree`, `GetSelectedWidget`, `ApplyWidgetChangeToAsset`

## UMGToolSet

식별자: `UMGToolSet.UMGToolSet` · 23개 도구

AI 기반 위젯 생성 및 트리 조작을 위한 UMG 위젯 툴세트입니다.

중요 워크플로 - 이 툴세트에서 반환하는 모든 위젯 및 슬롯은 다음 절차를 따라야 합니다.
  1. 정확한 프로퍼티 이름을 검색하기 위해 ObjectTools.list_properties(widget)를 호출합니다.
  2. 확인된 정확한 이름을 사용하여 ObjectTools.get_properties(widget, [...])를 호출합니다.
  3. 방금 확인한 정확한 이름으로 ObjectTools.set_properties(widget, {...})를 호출합니다.
프로퍼티 이름은 위젯 클래스마다 고유하므로 유추할 수 없습니다. 반드시 list_properties를 확인해야 합니다.
단계 1을 건너뛰면 set_properties가 경고 없이 실패하거나 잘못된 프로퍼티를 설정하게 됩니다.

UObject 포인터를 반환합니다. ToolsetRegistry가 이를 자동으로 {"refPath": "..."} 포맷으로 시리얼라이즈합니다.
반환된 Widget, Slot 및 Parent 포인터는 ObjectTools에 직접 전달하거나 해당 툴세트로 다시 반환할 수 있습니다.

[원본 입력·반환 스키마](Evidence/UnrealMCP/UMGToolSet.UMGToolSet.json)

도구: `WrapWidgets`, `ToggleWidgetAsVariable`, `SetNamedSlotContent`, `ReplaceWidgetWithTemplate`, `ReplaceWidgetWithNamedSlot`, `ReplaceWidgetWithChild`, `RenameWidget`, `RemoveWidget`, `RemoveUIComponent`, `MoveWidget`, `MoveUIComponent`, `ListWidgetClasses`, `ListWidgetBlueprints`, `GetWidgetTreeDepth`, `GetWidgets`, `GetWidgetDescription`, `GetWidgetClassInfo`, `GetNamedSlots`, `CreateWidgetBlueprint`, `CompileWidgetBlueprint`, `BindToEventProperty`, `AddWidget`, `AddUIComponent`

## StateTreeTools

식별자: `state_tree_toolset.toolsets.state_tree.StateTreeTools` · 9개 도구

Inspect StateTree (ST) assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/state_tree_toolset.toolsets.state_tree.StateTreeTools.json)

도구: `get_node_description`, `get_evaluators`, `get_global_tasks`, `get_transitions`, `get_enter_conditions`, `get_tasks`, `get_children`, `get_root_states`, `get_editor_data`

## ActorTools

식별자: `editor_toolset.toolsets.actor.ActorTools` · 17개 도구

Provides tools for inspecting and modifying actors, including
    their transforms, labels, parent-child relationships, and components.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.actor.ActorTools.json)

도구: `remove_component`, `add_component`, `get_components`, `get_actor_bounds`, `set_parent_component`, `get_parent_component`, `get_component_actor`, `get_root_component`, `look_at`, `set_actor_transform`, `get_actor_transform`, `remove_tag`, `add_tag`, `has_tag`, `get_tags`, `set_label`, `get_label`

## AssetTools

식별자: `editor_toolset.toolsets.asset.AssetTools` · 21개 도구

Provides tools for interacting with assets in the Unreal project and files on disk.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.asset.AssetTools.json)

도구: `write_file`, `read_file`, `get_plugin_content_paths`, `get_dependencies`, `get_referencers`, `is_checked_out`, `can_edit_asset`, `is_dirty`, `save_assets`, `load_asset`, `update_metadata_tags`, `get_metadata_tags`, `get_asset_class`, `get_asset_tags`, `find_assets`, `delete`, `move`, `duplicate`, `exists`, `list_folders`, `create_folder`

## BlueprintTools

식별자: `editor_toolset.toolsets.blueprint.BlueprintTools` · 53개 도구

Provides tools for working with Blueprints.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.blueprint.BlueprintTools.json)

도구: `read_graph_dsl`, `write_graph_dsl`, `get_graph_dsl_docs`, `list_event_dispatchers`, `add_event_dispatcher`, `remove_variable`, `set_variable_category`, `get_variable_category`, `set_variable_replication`, `get_variable_replication`, `set_variable_instance_editable`, `list_variables`, `add_object_variable`, `add_struct_variable`, `add_variable`, `set_parent`, `get_parent`, `get_pin_value`, `set_pin_value`, `break_pins`, `connect_pins`, `arrange_nodes`, `set_node_position`, `retarget_node_class`, `remove_node_pin`, `add_node_pin`, `delete_node`, `create_node`, `add_component_bound_event`, `list_component_events`, `find_node_categories`, `get_node_type_pins`, `find_node_types`, `get_connected_subgraph`, `find_nodes`, `list_compatible_event_functions`, `set_create_event_function`, `get_create_event_function`, `get_node_infos`, `add_object_function_param`, `add_struct_function_param`, `remove_function_param`, `add_function_param`, `remove_function_graph`, `add_event`, `add_function_graph`, `list_events`, `list_functions`, `get_graph`, `list_graphs`, `get_default_object`, `compile_blueprint`, `create`

## CurveTableTools

식별자: `editor_toolset.toolsets.curve_table.CurveTableTools` · 9개 도구

Provides tools for creating and editing CurveTable assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.curve_table.CurveTableTools.json)

도구: `get_keys`, `set_keys`, `add_key`, `rename_row`, `remove_row`, `add_row`, `list_rows`, `create`, `import_file`

## DataAssetTools

식별자: `editor_toolset.toolsets.data_asset.DataAssetTools` · 1개 도구

Provides tools for working with Data Assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.data_asset.DataAssetTools.json)

도구: `create`

## DataTableTools

식별자: `editor_toolset.toolsets.data_table.DataTableTools` · 10개 도구

Provides tools for creating and editing DataTable assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.data_table.DataTableTools.json)

도구: `set_rows`, `get_rows`, `rename_rows`, `remove_rows`, `add_rows`, `list_rows`, `get_schema`, `create`, `import_file`, `search_row_structs`

## MaterialTools

식별자: `editor_toolset.toolsets.material.MaterialTools` · 22개 도구

Provides tools for creating and editing Material and MaterialFunction assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.material.MaterialTools.json)

도구: `get_referencing_materials`, `recompile`, `delete_unused_expressions`, `disconnect_from_output`, `connect_to_output`, `get_property_input`, `get_expression_inputs`, `disconnect_expressions`, `connect_expressions`, `get_expression_output_names`, `get_expression_input_names`, `delete_parameter_group`, `rename_parameter_group`, `list_parameter_groups`, `layout_expressions`, `get_expressions`, `delete_expression`, `add_expression`, `list_expression_classes`, `create_parameter_collection`, `create_function`, `create_material`

## MaterialInstanceTools

식별자: `editor_toolset.toolsets.material_instance.MaterialInstanceTools` · 13개 도구

Provides tools for creating and modifying MaterialInstanceConstant assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.material_instance.MaterialInstanceTools.json)

도구: `set_parameter_override`, `clear_parameters`, `set_parent`, `set_static_switch_parameter`, `get_static_switch_parameter`, `set_texture_parameter`, `get_texture_parameter`, `set_vector_parameter`, `get_vector_parameter`, `set_scalar_parameter`, `get_scalar_parameter`, `list_parameters`, `create`

## ObjectTools

식별자: `editor_toolset.toolsets.object.ObjectTools` · 6개 도구

Provides tools for inspecting and modifying the properties of
    Unreal Objects and Unreal Classes, including those in Blueprints.
    Also use this toolset to discover available classes and subclasses.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.object.ObjectTools.json)

도구: `reset_properties`, `set_properties`, `get_properties`, `list_properties`, `get_class`, `search_subclasses`

## PrimitiveTools

식별자: `editor_toolset.toolsets.primitive.PrimitiveTools` · 4개 도구

Provides tools for adding primitive geometry components to actors.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.primitive.PrimitiveTools.json)

도구: `add_cone`, `add_cylinder`, `add_sphere`, `add_cube`

## SceneTools

식별자: `editor_toolset.toolsets.scene.SceneTools` · 20개 도구

Provides tools for working with the currently loaded level, including
    loading levels, placing and removing actors, controlling the level camera,
    and organizing actors in the outliner.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.scene.SceneTools.json)

도구: `save_actor`, `is_checked_out`, `can_edit`, `commit_level_instance`, `edit_level_instance`, `create_level_instance`, `merge_actors`, `trace_world`, `delete_folder`, `rename_folder`, `set_actor_folder`, `get_actors_in_folder`, `get_folders`, `remove_from_scene`, `add_to_scene_from_asset`, `add_to_scene_from_class`, `find_actors`, `get_collision_channels`, `get_current_level`, `load_level`

## SkeletalMeshTools

식별자: `editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools` · 22개 도구

Provides tools for inspecting and modifying skeletal mesh assets, including
    the mesh/materials, bone hierarchies, and sockets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.skeletal_mesh.SkeletalMeshTools.json)

도구: `rename_socket`, `remove_socket`, `set_socket_transform`, `get_socket_transform`, `get_socket_bone`, `get_socket_names`, `add_socket`, `get_morph_target_names`, `assign_physics_asset`, `get_physics_asset`, `set_material`, `get_material`, `get_material_slots`, `get_bone_children`, `get_bone_parent`, `get_bone_names`, `get_skeleton`, `get_bounds`, `get_section_count`, `get_vertex_count`, `get_lod_count`, `import_file`

## StaticMeshTools

식별자: `editor_toolset.toolsets.static_mesh.StaticMeshTools` · 16개 도구

Provides tools for inspecting and modifying static mesh assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.static_mesh.StaticMeshTools.json)

도구: `set_nanite_enabled`, `is_nanite_enabled`, `remove_collisions`, `generate_convex_collisions`, `remove_lods`, `generate_lods`, `set_lod_thresholds`, `get_lod_thresholds`, `set_material`, `get_material`, `get_material_slots`, `get_bounds`, `get_vertex_count`, `get_triangle_count`, `get_lod_count`, `import_file`

## StringTableTools

식별자: `editor_toolset.toolsets.string_table.StringTableTools` · 8개 도구

Provides tools for creating and editing StringTable assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.string_table.StringTableTools.json)

도구: `remove_entry`, `set_entry`, `get_entry`, `list_keys`, `get_namespace`, `get_table_id`, `create`, `import_file`

## ProgrammaticToolset

식별자: `editor_toolset.toolsets.programmatic.ProgrammaticToolset` · 2개 도구

Batches calls to other registered tools through a small sandboxed Python
    script that glues them together with custom logic. The script's purpose is
    tool orchestration, not general Python execution.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.programmatic.ProgrammaticToolset.json)

도구: `execute_tool_script`, `get_execution_environment`

## TextureTools

식별자: `editor_toolset.toolsets.texture.TextureTools` · 2개 도구

Provides tools for working with Texture assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/editor_toolset.toolsets.texture.TextureTools.json)

도구: `get_size`, `import_file`

## ConversationTools

식별자: `conversation_toolset.toolsets.conversation.ConversationTools` · 7개 도구

Inspect Conversation Graph (UConversationDatabase) dialogue assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/conversation_toolset.toolsets.conversation.ConversationTools.json)

도구: `get_sub_nodes`, `get_node_connections`, `get_node_by_guid`, `get_node_guids`, `get_all_nodes`, `list_speakers`, `list_entry_points`

## ControlRigTools

식별자: `animation_toolset.toolsets.controlrig.ControlRigTools` · 44개 도구

Tools for creating and editing Control Rig assets, including hierarchy
    management, graph operations, and node/pin manipulation.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.controlrig.ControlRigTools.json)

도구: `remove_variable`, `change_variable_type`, `get_variable`, `list_variables`, `add_variable`, `get_connected_pins`, `disconnect_pins`, `connect_pins`, `set_pin_value`, `get_pin_value`, `list_pins`, `add_variable_node`, `add_event_node`, `set_node_position`, `get_node_position`, `delete_node`, `list_nodes`, `create_node`, `add_interaction_graph`, `add_backward_solve_graph`, `add_event_graph`, `get_interaction_graph`, `get_backward_solve_graph`, `get_event_graph`, `get_forward_solve_graph`, `add_graph`, `list_graphs`, `get_graph`, `get_children`, `get_parent`, `set_local_transform`, `get_local_transform`, `set_global_transform`, `get_global_transform`, `add_control`, `add_null`, `add_bone`, `add_element`, `get_all_controls`, `get_all_nulls`, `get_all_bones`, `get_elements`, `import_bones_from_asset`, `create`

## SequencerTools

식별자: `animation_toolset.toolsets.sequencer.SequencerTools` · 140개 도구

Core tools for creating and editing Level Sequences in Sequencer. Use
    whenever working with Sequencer - covers sequence lifecycle (create, open,
    close), playback control (play, pause, scrub, speed, loop), sequence
    properties (display rate, frame ranges, marked frames, tick resolution),
    actor bindings (add actors, spawnables, cameras, find and manage bindings),
    tracks (add, find, remove any track type), sections (range, easing, blend
    type, completion mode), selection state, folder organization, sub-sequence
    navigation, event tracks, track filters, and sequence locking. For
    keyframing use SequencerKeyframingTools. For Control Rig use
    SequencerControlRigTools. For outliner inspection use
    SequencerOutlinerTools.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.sequencer.SequencerTools.json)

도구: `paste_folders`, `copy_folders`, `paste_sections`, `copy_sections`, `paste_tracks`, `copy_tracks`, `paste_bindings`, `copy_bindings`, `remove_binding_tag`, `untag_binding`, `tag_binding`, `get_binding_tags`, `get_all_binding_tags`, `find_bindings_by_tag`, `find_binding_by_tag`, `get_section_post_roll_frames`, `set_section_post_roll_frames`, `get_section_pre_roll_frames`, `set_section_pre_roll_frames`, `set_section_animation`, `set_byte_track_enum`, `set_property_name_and_path`, `get_section_to_key`, `get_binding_id`, `get_child_possessables`, `bake_transform`, `set_sequence_locked`, `is_sequence_locked`, `set_track_filter_active`, `is_track_filter_active`, `get_track_filter_names`, `fix_actor_references`, `rebind_component`, `remove_invalid_bindings`, `remove_all_bindings`, `remove_actors_from_binding`, `replace_binding_with_actors`, `add_actors_to_binding`, `add_event_repeater_section`, `add_event_trigger_section`, `get_sequence_lock_state`, `get_sub_sequence_hierarchy`, `focus_parent_sequence`, `focus_sub_sequence`, `get_folder_contents`, `add_binding_to_folder`, `add_track_to_folder`, `remove_root_folder`, `get_root_folders`, `add_root_folder`, `add_actors_by_name`, `set_selection_range`, `get_selection_range`, `play_to`, `is_camera_cut_locked`, `select_folders`, `set_camera_lock`, `force_evaluate`, `empty_selection`, `select_bindings`, `select_sections`, `select_tracks`, `get_selected_folders`, `get_selected_bindings`, `get_selected_sections`, `get_selected_tracks`, `get_section_properties`, `get_section_completion_mode`, `set_section_completion_mode`, `get_section_blend_type`, `set_section_blend_type`, `get_section_ease_out`, `get_section_ease_in`, `set_section_ease_out`, `set_section_ease_in`, `set_camera_cut_binding`, `set_section_end_bounded`, `set_section_start_bounded`, `has_section_end_frame`, `has_section_start_frame`, `get_section_range`, `set_section_range`, `remove_section`, `get_sections`, `add_section`, `set_track_display_name`, `get_track_display_name`, `remove_track_from_sequence`, `remove_track`, `find_tracks_by_type`, `get_tracks_on_sequence`, `get_tracks_on_binding`, `add_track_to_sequence`, `add_track_to_binding`, `get_bound_objects`, `remove_binding`, `set_binding_name`, `get_binding_name`, `find_binding_by_name`, `get_bindings`, `create_camera`, `add_spawnable_from_class`, `add_spawnable_from_instance`, `add_actors`, `set_playback_range_locked`, `is_playback_range_locked`, `set_clock_source`, `get_clock_source`, `set_evaluation_type`, `get_evaluation_type`, `set_tick_resolution`, `get_tick_resolution`, `find_marked_frame_by_label`, `delete_all_marked_frames`, `delete_marked_frame`, `get_marked_frames`, `add_marked_frame`, `get_work_range`, `set_work_range`, `get_view_range`, `set_view_range`, `set_playback_range`, `get_playback_range`, `set_display_rate`, `get_display_rate`, `get_loop_mode`, `set_loop_mode`, `get_playback_speed`, `set_playback_speed`, `get_playhead_frame`, `set_playhead_frame`, `is_playing`, `pause`, `play`, `refresh_sequence`, `close_sequence`, `open_sequence`, `get_focused_sequence`, `get_current_sequence`, `create_level_sequence`

## SequencerKeyframingTools

식별자: `animation_toolset.toolsets.keyframing.SequencerKeyframingTools` · 22개 도구

Tools for keyframing and animating properties on the Sequencer
    timeline. Use when adding, querying, or removing keyframes on channels,
    setting default values, evaluating channels at specific times, working
    with the Curve Editor, or managing channel selection. Covers float, bool,
    integer, and string key types with configurable interpolation.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.keyframing.SequencerKeyframingTools.json)

도구: `get_keys_by_index`, `bake_channel_keys`, `is_curve_shown`, `show_curve`, `curve_editor_empty_selection`, `curve_editor_select_keys`, `get_curve_editor_selected_keys`, `get_selected_key_channels`, `is_curve_editor_open`, `close_curve_editor`, `open_curve_editor`, `select_channels`, `get_selected_channels`, `get_default_value`, `set_default_value`, `remove_key_at_frame`, `get_keys`, `add_key_string`, `add_key_integer`, `add_key_bool`, `add_key_float`, `get_channel_names`

## SequencerControlRigTools

식별자: `animation_toolset.toolsets.controlrig_sequencer.SequencerControlRigTools` · 72개 도구

Tools for animating with Control Rig inside Sequencer. Use when adding
    Control Rig tracks to bindings, getting or setting control values (bool,
    float, int, position, rotator, scale, euler transform, transform), keying
    controls, baking animation to Control Rig, managing layered rigs and
    priority, masking controls per section, space switching (world, parent,
    control, bone), tweening and blending between keys, snapping controls to
    actors, mirroring poses, zeroing transforms, or managing animation layers
    (add, delete, duplicate, reorder, merge, collapse).

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.controlrig_sequencer.SequencerControlRigTools.json)

도구: `set_anim_mode_local_spaces`, `get_anim_mode_local_spaces`, `set_anim_mode_only_rig_sel`, `get_anim_mode_only_rig_sel`, `set_anim_mode_hide_manips`, `get_anim_mode_hide_manips`, `set_anim_mode_nulls`, `get_anim_mode_nulls`, `set_anim_mode_hierarchy`, `get_anim_mode_hierarchy`, `set_anim_mode_gizmo_scale`, `get_anim_mode_gizmo_scale`, `get_transform`, `set_transform`, `get_controls_info`, `get_control_rigs`, `find_or_create_track`, `import_fbx_to_rig`, `export_fbx_from_rig`, `frame_selection`, `clear_selection`, `select_control`, `get_selected_controls`, `zero_transforms`, `mirror_selected_controls`, `select_mirrored_controls`, `merge_anim_layers`, `reorder_anim_layers`, `duplicate_anim_layer`, `delete_anim_layer`, `add_layer_from_selection`, `get_anim_layers`, `snap_control_rig`, `blend_values_on_selected`, `tween_control_rig`, `bake_space`, `delete_space`, `move_space`, `set_space`, `is_fk_control_rig`, `set_priority_order`, `get_priority_order`, `set_layered_mode`, `is_layered_control_rig`, `hide_all_controls`, `show_all_controls`, `set_controls_mask`, `get_controls_mask`, `collapse_anim_layers`, `load_anim_into_rig`, `bake_to_control_rig`, `key_controls_at_frames`, `key_controls`, `get_actor_transform_at_frame`, `set_world_transform`, `get_world_transform`, `set_euler_transform`, `get_euler_transform`, `set_scale`, `get_scale`, `set_rotator`, `get_rotator`, `set_position`, `get_position`, `set_vector2d`, `get_vector2d`, `set_int`, `get_int`, `set_bool`, `get_bool`, `set_float`, `get_float`

## SequencerOutlinerTools

식별자: `animation_toolset.toolsets.outliner.SequencerOutlinerTools` · 18개 도구

Tools for inspecting and managing the Sequencer outliner tree. Use when
    getting a snapshot of the outliner hierarchy, querying node children,
    managing outliner selection, expanding or collapsing nodes, or toggling
    node states like mute, solo, deactivate, lock, and pin. Also useful for
    test verification of Sequencer UI state.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.outliner.SequencerOutlinerTools.json)

도구: `get_sections_for_nodes`, `get_pinned_nodes`, `set_node_pinned`, `get_locked_nodes`, `set_node_locked`, `get_deactivated_nodes`, `set_node_deactivated`, `get_soloed_nodes`, `get_muted_nodes`, `set_node_solo`, `set_node_muted`, `is_node_expanded`, `set_node_expanded`, `get_node_label`, `set_outliner_selection`, `get_outliner_selection`, `get_outliner_children`, `get_outliner_tree`

## SequencerConditionTools

식별자: `animation_toolset.toolsets.conditions.SequencerConditionTools` · 9개 도구

Tools for managing runtime conditions on Sequencer tracks, sections, and
    track rows. Use when setting up dynamic conditions that control whether
    tracks or sections evaluate at runtime based on platform, gameplay state,
    or custom logic. Supports MovieScenePlatformCondition,
    MovieSceneDirectorBlueprintCondition, and MovieSceneGroupCondition types.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.conditions.SequencerConditionTools.json)

도구: `clear_track_row_condition`, `set_track_row_condition`, `get_track_row_condition`, `clear_track_condition`, `set_track_condition`, `get_track_condition`, `clear_section_condition`, `set_section_condition`, `get_section_condition`

## SequencerCustomBindingTools

식별자: `animation_toolset.toolsets.custom_bindings.SequencerCustomBindingTools` · 8개 도구

Tools for converting and managing custom binding types in Sequencer. Use
    when converting between possessable, spawnable, and custom/replaceable
    bindings, querying what custom binding type a binding uses, accessing
    custom binding objects for property inspection, or changing the actor
    template class on spawnables/replaceables.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.custom_bindings.SequencerCustomBindingTools.json)

도구: `save_default_spawnable_state`, `change_actor_template_class`, `get_custom_bindings_of_type`, `get_custom_binding_objects`, `get_custom_binding_type`, `convert_to_custom_binding`, `convert_to_possessable`, `convert_to_spawnable`

## SequencerImportExportTools

식별자: `animation_toolset.toolsets.import_export.SequencerImportExportTools` · 6개 도구

Tools for importing and exporting animation data to and from Sequencer.
    Use when exporting bindings or Control Rig animation to FBX files,
    importing FBX animation onto bindings or Control Rig tracks, exporting
    animation to AnimSequence assets, or linking AnimSequences for
    auto-updates.

[원본 입력·반환 스키마](Evidence/UnrealMCP/animation_toolset.toolsets.import_export.SequencerImportExportTools.json)

도구: `get_linked_level_sequence`, `get_linked_anim_sequences`, `link_anim_sequence`, `export_anim_sequence`, `import_fbx`, `export_fbx`

## BehaviorTreeTools

식별자: `aimodule_toolset.toolsets.behavior_tree.BehaviorTreeTools` · 7개 도구

Inspect BehaviorTree (BT) assets.

[원본 입력·반환 스키마](Evidence/UnrealMCP/aimodule_toolset.toolsets.behavior_tree.BehaviorTreeTools.json)

도구: `get_subtree`, `get_children`, `get_node_depths`, `get_node_depth`, `list_nodes`, `get_root_decorators`, `get_blackboard`
