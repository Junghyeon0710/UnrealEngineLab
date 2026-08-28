# Animation Budget Allocator

UE 5.8 런타임 플러그인 `AnimationBudgetAllocator` 조사 노트.
근거는 모두 엔진 소스(`Engine/Plugins/Runtime/AnimationBudgetAllocator`)에서 직접 확인했다.

- 조사 대상 엔진: `D:\UE_5.8` (UE 5.8)
- 플러그인 버전: 1.0, `EnabledByDefault: false`, 모듈 로딩 페이즈 `PreDefault`
- 관련 문서: [test-plan.md](test-plan.md) — 이 리포에서의 실제 테스트 절차

---

## 1. 무엇을 하는가

스켈레탈 메시 컴포넌트의 **틱 레이트를 매 프레임 동적으로 재분배**해서, 애니메이션에 쓰는
게임 스레드 시간을 지정한 예산(ms) 안에 묶어두는 시스템이다.

메시가 많아지면 프레임 시간이 선형으로 증가하는 대신, 예산을 넘는 순간부터
**중요도(significance)가 낮은 메시부터** 순서대로 품질을 깎는다. 즉 "느려지는" 대신 "덜 정확해진다".

부하가 커질 때 적용되는 단계는 다음 순서다:

| 단계 | 동작 | 관련 파라미터 |
|---|---|---|
| 1. Always tick | 매 프레임 풀 틱. 예산이 넘치면 이 그룹 크기가 줄어든다 | `AlwaysTickFalloffAggression` |
| 2. Interpolation | N프레임마다 평가하고 사이는 포즈 보간 | `InterpolationFalloffAggression`, `InterpolationMaxRate`, `MaxInterpolatedComponents` |
| 3. Throttle | 보간 없이 틱 레이트만 낮춤 (포즈가 계단식으로 끊김) | `MaxTickRate`, `MinQuality` |
| 4. Reduced work | 컴포넌트별 콜백으로 작업량 자체를 줄임 (LOD, 저가 AnimBP 등) | `BudgetFactorBeforeReducedWork`, `ReducedWorkThrottleMax/MinInFrames` |
| 5. Emergency reduced work | `bAlwaysTick`이 아닌 **모든** 컴포넌트에 4단계 강제 적용 | `BudgetPressureBeforeEmergencyReducedWork` |

---

## 2. 사용 전제조건

### 2.1 컴포넌트가 `USkeletalMeshComponentBudgeted` 여야 한다

일반 `USkeletalMeshComponent`는 이 시스템의 대상이 아니다. 플러그인이 제공하는
`USkeletalMeshComponentBudgeted`(`meta=(BlueprintSpawnableComponent)`)로 교체해야 한다.
Blueprint에서도 컴포넌트로 추가할 수 있다.

기본값으로 `bAutoRegisterWithBudgetAllocator = true`라서 `BeginPlay`에서 알아서 등록된다
(데디케이티드 서버에서는 등록하지 않는다).

### 2.2 활성화는 2단계 게이트다 — 가장 흔한 함정

```cpp
// AnimationBudgetAllocator.cpp
const bool bUpdatingThisTick = FAnimationBudgetAllocator::bCachedEnabled && bEnabled;
```

- `bCachedEnabled` <- 전역 CVar `a.Budget.Enabled`
- `bEnabled` <- **월드별 플래그, 기본값 `false`**

즉 **콘솔에 `a.Budget.Enabled 1`만 쳐서는 아무 일도 일어나지 않는다.**
월드별 플래그는 CVar로 켤 수 없고 다음 둘 중 하나로만 켠다:

- Blueprint: `Enable Animation Budget` 노드 (`UAnimationBudgetBlueprintLibrary::EnableAnimationBudget`)
- C++: `IAnimationBudgetAllocator::Get(World)->SetEnabled(true)`

이 리포에는 편의를 위해 콘솔 명령 `AnimBudgetTest.Enable 1`을 추가해 뒀다
(`Source/UnrealEngineLab/AnimBudget/AnimBudgetTestSpawner.cpp`).

### 2.3 게임 월드 전용

```cpp
if (Budgeter == nullptr && World->IsGameWorld())
```

에디터 뷰포트에서는 allocator 자체가 생성되지 않는다. **PIE 또는 스탠드얼론에서만** 테스트된다.

### 2.4 URO와 상호 배타

컴포넌트가 등록되는 순간 allocator가 다음을 강제한다:

```cpp
InComponent->bEnableUpdateRateOptimizations = false;
InComponent->EnableExternalTickRateControl(true);
```

Update Rate Optimization(URO)과 같이 쓸 수 없다. allocator를 끄면 원래대로 복구된다.
따라서 **URO 기반 최적화와 성능 비교를 할 때는 별도 시나리오로 나눠야 한다.**

---

## 3. Significance (중요도)

allocator가 어떤 메시를 먼저 깎을지 정하는 값. 두 가지 방식이 있다.

### 3.1 외부에서 푸시

```cpp
Component->SetComponentSignificance(
    Significance,          // 클수록 우선순위 높음
    bNeverSkip,            // = bAlwaysTick. 절대 스킵하지 않음 (reduced work 대상에서도 제외됨)
    bTickEvenIfNotRendered,
    bAllowReducedWork,     // bNeverSkip이 true면 강제로 false가 됨
    bForceInterpolate);
```

> `SetComponentSignificance`를 allocator 등록 전에 호출하면 경고만 찍히고 무시된다.

### 3.2 자동 계산 (`bAutoCalculateSignificance`)

`EditAnywhere` 프로퍼티. 켜면 각 컴포넌트가 매 틱마다 **모든 플레이어 시점과의 거리** 기준으로
significance를 계산한다 (가장 가까운 시점 기준, 1.0 -> 0.0 선형).

전역 커스텀 계산이 필요하면 `USkeletalMeshComponentBudgeted::OnCalculateSignificance()`
(static 델리게이트)에 바인드하면 거리 계산을 대체한다.

**주의 — 이 플래그는 등록 시점에 캡처된다.**
`FAnimationBudgetAllocator::RegisterComponent`가 `ComponentData.bAutoCalculateSignificance`로
값을 복사해 가므로, `SetAutoCalculateSignificance()`는 **`RegisterComponent()` 호출 전에** 해야 한다.
반대로 `SetComponentSignificance()`는 등록이 끝난 **뒤에** 불러야 한다 (6.10절).

**주의 — 거리 기본값 문서 오류.**
`AutoCalculatedSignificanceMaxDistance`의 실제 기본값은 구조체 정의상 `30000.0f`(= 300 m)인데,
CVar 도움말 문자열에는 `Default = 300.0`으로 적혀 있다. 도움말 쪽이 미터 단위로 잘못 적힌 것으로
보이며, `a.Budget.AutoCalculatedSignificanceMaxDistance`에 실제로 넣어야 하는 값은 **cm**다.

---

## 4. Reduced work는 델리게이트 없이는 동작하지 않는다 — 두 번째 함정

```cpp
if (bAllowReducedWork && !ComponentData.bReducedWork && ComponentData.Component->OnReduceWork().IsBound())
```

`FOnReduceWork`는 **C++ 전용 델리게이트**이고 Blueprint에 노출되어 있지 않다.
바인드하지 않으면 4·5단계(reduced work / emergency reduced work)는 전부 no-op이 되고,
틱 레이트 스로틀링과 보간까지만 동작한다.

게임에서 이 콜백에 넣을 만한 것: 메시 LOD 강제, 저가 AnimBP로 스왑, 클로스/피직스 비활성화,
자식 컴포넌트 틱 끄기 등.

---

## 5. 측정 방법

### 5.1 stat 그룹

```
stat AnimationBudgetAllocator
```

노출되는 값:

| 항목 | 의미 |
|---|---|
| Num Registered Components | 등록된 전체 컴포넌트 수 |
| Num Ticked Components | 이번 프레임에 실제로 틱한 수 |
| Demand | 풀 틱을 원하는 work unit 수 |
| Budget | 현재 예산 (work unit 환산) |
| Average Work Unit (ms) | 컴포넌트 1개 평균 틱 비용 |
| Always Tick / Throttled / Interpolated | 각 단계에 속한 컴포넌트 수 |
| SmoothedBudgetPressure | 예산 압력. 1.0 초과 = 오버버짓 |

### 5.2 CSV 프로파일러

`AnimationBudget` 카테고리가 기본 활성이다 (`CSV_DEFINE_CATEGORY(AnimationBudget, true)`).

```
csvprofile start
csvprofile stop
```

**주의 — 품질 스탯은 기본 빌드에 없다.** 소스에 보이는 `NumTicked`, `AnimQuality`,
`AverageTickRate`, `NumThrottled`, `NumInterpolated`, `NumAlwaysTicked`는 전부
`BUDGET_CSV_STAT` 매크로로 감싸여 있는데, 이 매크로는 `WITH_EXTRA_BUDGET_CSV_STATS`
(= `WITH_TICK_DEBUG`)가 켜져야만 코드로 확장된다. 기본 빌드에서는 컴파일 아웃된다.

기본 빌드에서 실제로 CSV에 나오는 것:

| 컬럼 | 의미 |
|---|---|
| `AnimationBudget/GameThread/BudgetedAnimation` | 예산 대상 애니메이션의 게임스레드 시간 |
| `AnimationBudget/AverageWorkUnitTimeMs` | 컴포넌트 1개 평균 비용 |
| `Exclusive/GameThread/AnimationBudgetAllocator` | allocator 자체 오버헤드 |

품질을 재려면 `USkeletalMeshComponent::PoseTickedThisFrame()`
(`GFrameCounter == LastPoseTickFrame`)으로 직접 세는 편이 확실하다. 이 리포의
테스트 액터가 그렇게 하고 `AnimBudgetTest/*` CSV 스탯으로 내보낸다.

### 5.3 온스크린 디버그

```
a.Budget.Debug.Enabled 1
```

`ENABLE_DRAW_DEBUG` 빌드에서만 컴파일된다 (Shipping 제외). 상세 정보는 `a.Budget.Debug.Verbose*` 계열 참고.

---

## 6. CVar 레퍼런스

### 6.1 활성화 / 동작 변경

| CVar | 기본값 | 설명 |
|---|---|---|
| `a.Budget.Enabled` | 0 | 전역 게이트. **월드별 플래그와 AND로 묶인다** (2.2절) |
| `a.Budget.MaintainReduceWorkWhenOffScreen` | 0 | 화면 밖 컴포넌트가 예산이 남아도 reduced work를 유지 |
| `a.Budget.ComponentsWithZeroSigAreNonRendered` | 0 | significance 0인 컴포넌트를 비렌더로 취급 |
| `a.Budget.ForceTickWhenComponentExitsOffScreen` | 0 | 화면 밖으로 나갈 때 강제 1회 틱 |
| `a.Budget.EmergencyReduceWorkDisabled` | 0 | 5단계(emergency) 비활성화 |

### 6.2 예산 / 품질

| CVar | 기본값 | 범위 | 설명 |
|---|---|---|---|
| `a.Budget.BudgetMs` | 1.0 | > 0.1 | **핵심 값.** 스켈레탈 메시 작업에 할당할 ms |
| `a.Budget.MinQuality` | 0.0 | [0, 1] | 최소 품질(틱한 비율). 0이 아니면 예산을 넘길 수 있음 |
| `a.Budget.MaxTickRate` | 10 | >= 1 | 최대 틱 간격(프레임). 품질 하한 역할 |
| `a.Budget.WorkUnitSmoothingSpeed` | 5.0 | > 0.1 | 평균 work unit 수렴 속도 |
| `a.Budget.InitialEstimatedWorkUnitTime` | 0.08 | > 0.0 | 첫 틱 전 컴포넌트 비용 추정치(ms) |

### 6.3 폴오프 / 보간

| CVar | 기본값 | 범위 | 설명 |
|---|---|---|---|
| `a.Budget.AlwaysTickFalloffAggression` | 0.8 | [0.1, 0.9] | 클수록 always-tick 그룹을 빨리 줄임 |
| `a.Budget.InterpolationFalloffAggression` | 0.4 | [0.1, 0.9] | 클수록 보간 그룹을 빨리 줄임 |
| `a.Budget.InterpolationMaxRate` | 6 | > 1 | 보간 중 최대 틱 간격 |
| `a.Budget.MaxInterpolatedComponents` | 16 | >= 0 | 스로틀 전 최대 보간 컴포넌트 수 |
| `a.Budget.InterpolationTickMultiplier` | 0.75 | [0.1, 0.9] | 보간 틱의 상대 비용 추정. 실측 약 0.46. 낮추면 예산이 throttle 그룹으로 흘러가 품질이 오른다 (결과 문서 9절). **보간이 일어나지 않는 구간에서는 무의미** |

### 6.4 Reduced work

| CVar | 기본값 | 범위 | 설명 |
|---|---|---|---|
| `a.Budget.BudgetFactorBeforeReducedWork` | 1.5 | > 1 | 이 압력을 넘어야 reduced work 시작 |
| `a.Budget.BudgetFactorBeforeReducedWorkEpsilon` | 0.25 | > 0.0 | 복구 히스테리시스 |
| `a.Budget.BudgetFactorBeforeAggressiveReducedWork` | 2.0 | > 1 | 이 압력을 넘으면 더 빠르게 적용 |
| `a.Budget.BudgetPressureBeforeEmergencyReducedWork` | 2.5 | > 0.0 | 5단계 진입 압력 |
| `a.Budget.BudgetPressureSmoothingSpeed` | 3.0 | > 0.0 | 압력 스무딩 속도 |
| `a.Budget.ReducedWorkThrottleMinInFrames` | 2 | [1, 255] | 압력 높을 때 전환 간격 |
| `a.Budget.ReducedWorkThrottleMaxInFrames` | 20 | [1, 255] | 압력 낮을 때 전환 간격 |
| `a.Budget.ReducedWorkThrottleMaxPerFrame` | 4 | [1, 255] | 프레임당 전환 컴포넌트 수 상한 |

### 6.5 기타

| CVar | 기본값 | 설명 |
|---|---|---|
| `a.Budget.MaxTickedOffsreen` | 4 | 화면 밖에서 틱할 최대 개수. **엔진 오타 그대로다 — `Offsreen`** (`Offscreen` 아님) |
| `a.Budget.StateChangeThrottleInFrames` | 30 | 노이즈로 인한 잦은 전환 방지 (1~128) |
| `a.Budget.AutoCalculatedSignificanceMaxDistance` | 30000 (cm) | 자동 significance가 0이 되는 거리. 3.2절 문서 오류 주의 |

### 6.6 디버그 (`ENABLE_DRAW_DEBUG` 필요)

| CVar | 설명 |
|---|---|
| `a.Budget.Debug.Enabled` | 디버그 렌더링 on/off |
| `a.Budget.Debug.DisableGraph` | 성능 그래프만 끔 |
| `a.Budget.Debug.ShowAddresses` | 컴포넌트 데이터 주소 표시 |
| `a.Budget.Debug.VerboseActive` | 상세 모드 |
| `a.Budget.Debug.Verbose.ShowNames` | 상세 모드 - 컴포넌트 이름 |
| `a.Budget.Debug.Verbose.ShowActorNames` | 상세 모드 - 액터 이름 |
| `a.Budget.Debug.Verbose.ShowNonTicking` | 상세 모드 - 틱하지 않는 컴포넌트 |
| `a.Budget.Debug.Verbose.ShowOnCanvas` | 상세 모드 - 2D 캔버스 출력 |

### 6.7 강제 오버라이드 (Shipping / Test 빌드 제외)

예산 계산을 무시하고 값을 고정한다. A/B 비교 시 유용하다.

| CVar | 기본값 | 설명 |
|---|---|---|
| `a.Budget.Debug.Force` | 0 | 아래 강제 값들을 활성화 |
| `a.Budget.Debug.Force.Rate` | 4 | 모든 컴포넌트를 이 틱 레이트로 고정 |
| `a.Budget.Debug.Force.Interp` | 0 | 보간 강제 on |
| `a.Budget.Debug.Force.Reduced` | 0 | reduced work 강제 on |
| `a.Budget.Debug.Force.ExcludeAlwaysTicked` | 0 | always-tick 컴포넌트는 강제에서 제외 |

---

## 6.8 실측으로 확인된 함정 — `MaxTickRate`가 `BudgetMs`를 무력화한다

기본값 `a.Budget.MaxTickRate = 10`, `a.Budget.InterpolationMaxRate = 6`은 컴포넌트를
그보다 드물게 틱시킬 수 없게 만드는 **하한선**이다. 예산이 그보다 적은 작업을 요구해도
더 내려갈 수단이 없으므로, 어느 지점부터는 `BudgetMs`를 낮춰도 아무 변화가 없다.

400개 메시 실측(`results/2026-08-28-i9-10900F.md`)에서 `BudgetMs`를 0.25 / 0.5 / 1.0 / 2.0으로
바꿔도 결과가 완전히 동일했고(품질 0.210, 2.9 ms), `MaxTickRate`를 60으로 올리자마자
`BudgetMs 0.25`가 1.01 ms / 품질 0.062로 내려갔다.

낮은 예산을 실제로 달성하려면 `a.Budget.MaxTickRate`를 먼저 올려야 한다.
반대로 이 상한은 품질 하한을 보장하는 안전장치이기도 하므로, 올릴 때는 시각적 끊김을 함께 확인할 것.

---

## 6.9 오프스크린 감축은 `bTickEvenIfNotRendered` 없이는 일어나지 않는다

`a.Budget.MaxTickedOffsreen`은 컴포넌트가 `NonRenderedComponentData` 목록에 들어가야 적용되는데,
그 목록에 들어가려면 `SetComponentSignificance(..., bTickEvenIfNotRendered=true, ...)`가 되어 있어야 한다.
꺼져 있으면 `ShouldComponentTick`의 다른 조건(`ShouldTickPose()` 등)으로 살아남아
**화면 밖이어도 온스크린과 똑같이 처리된다.**

400개 실측: 플래그 off면 카메라를 등져도 품질 0.208 그대로,
플래그 on이면 `MaxTickedOffsreen`이 정확히 상한으로 동작했다 (4 -> 4.0틱, 32 -> 31.8틱).

이름이 "렌더 안 돼도 틱해라"로 읽히지만, 실제로는 **오프스크린 예산 관리 대상에 편입시키는 스위치**다.

### 여기에 Lumen이 한 겹 더 얹힌다

UE5 기본값인 Lumen이 켜져 있으면 시야 밖 프리미티브의 `LastRenderTime`도 계속 갱신되어,
allocator 입장에서는 **오프스크린 컴포넌트가 아예 존재하지 않는다**
(400개 전부 `LastRenderTime > World->TimeSeconds - 1`).
`r.DynamicGlobalIlluminationMethod 0`으로 꺼야 오프스크린으로 분류되기 시작한다.
그림자(`r.ShadowQuality 0`)는 무관했다.

## 6.10 `SetComponentSignificance`는 등록 직후에 부르면 조용히 무시된다

월드 BeginPlay 도중에 컴포넌트를 스폰하면 `USkeletalMeshComponentBudgeted::BeginPlay`가
`RegisterComponentDeferred`를 타서 아직 allocator를 물지 않은 상태가 된다.
이때 `SetComponentSignificance`를 부르면 다음 경고만 남기고 값이 버려진다:

```
LogSkeletalMesh: Warning: SetComponentSignificance called on [...] before registering with budget allocator
```

**첫 `Tick` 이후에 호출해야 한다.** 3.2절의 `SetAutoCalculateSignificance`가
`RegisterComponent()` **전에** 호출되어야 하는 것과 순서가 정반대이니 주의.

---

## 6.11 보간은 공짜가 아니다

같은 평가 횟수(400개 중 100개)에서 보간을 켜면 애니메이션 게임스레드 시간이
**3.29 ms -> 7.86 ms 로 2.4배** 늘었다.

`EnableExternalInterpolation`이 켜진 컴포넌트는 틱 함수가 **매 프레임 살아있고**,
평가하지 않는 프레임에는 포즈를 보간한다. 스로틀링(틱 자체를 끔)과 달리
프레임당 비용이 계속 발생한다.

부드러움이 필요 없는 원거리 메시라면 `a.Budget.MaxInterpolatedComponents`를 낮추거나
`a.Budget.InterpolationFalloffAggression`을 올려 보간 대상을 줄이는 쪽이
같은 품질에서 비용을 크게 줄인다.

한편 순수 스로틀링의 비용은 틱 레이트에 **거의 정확히 반비례**한다
(Rate 2/4/8 -> 6.82 / 3.29 / 1.50 ms, baseline 13.12 ms). 숨은 프레임당 고정비용은 없다.

---

## 6.12 보간은 "중간 부하" 단계다 — 압력이 높으면 아예 안 쓰인다

400개 실측에서 `BudgetMs 1.0`(압력 2.5 초과, emergency reduced work 구간)일 때
**보간 중인 컴포넌트가 0개**였다. `a.Budget.MaxInterpolatedComponents`를 16에서 200으로 올려도
0이었다. 보간 밴드가 열리기 전에 전부 throttle로 떨어지기 때문이다.

`BudgetMs 5.0`으로 압력을 낮추자 65~74개가 보간에 들어갔다.

따라서 `InterpolationTickMultiplier`, `MaxInterpolatedComponents`,
`InterpolationFalloffAggression` 같은 보간 파라미터는 **중간 부하 구간에서만 의미가 있다.**
튜닝하기 전에 먼저 보간이 실제로 일어나고 있는지 확인할 것
(엔진 CSV로는 볼 수 없다 — 5.2절 참고. `IsUsingExternalInterpolation()`으로 직접 세야 한다).

---

## 7. 요약 체크리스트

테스트가 "동작하지 않을" 때 순서대로 확인:

1. `.uproject`에 `AnimationBudgetAllocator` 플러그인이 enabled 인가
2. 메시가 `USkeletalMeshComponentBudgeted` 인가 (일반 SkeletalMeshComponent 아님)
3. **PIE / 스탠드얼론**인가 (에디터 뷰포트에서는 allocator가 없음)
4. `a.Budget.Enabled 1` **그리고** 월드별 `SetEnabled(true)` 둘 다 되었는가
5. `stat AnimationBudgetAllocator`의 Num Registered Components > 0 인가
6. reduced work가 안 보인다면 -> `OnReduceWork()`를 바인드했는가
7. 컴포넌트 수가 적어서 예산 안에 다 들어가는 건 아닌가 (`a.Budget.BudgetMs`를 0.2 정도로 낮춰 확인)
8. `BudgetMs`를 낮춰도 변화가 없다면 -> `a.Budget.MaxTickRate` 상한에 걸린 것 (6.8절)
9. 오프스크린인데 비용이 안 줄면 -> `bTickEvenIfNotRendered`가 꺼져 있거나 Lumen 때문에 계속 렌더 판정 (6.9절)
