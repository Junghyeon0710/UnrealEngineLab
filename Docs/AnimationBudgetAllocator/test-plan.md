# Animation Budget Allocator 테스트 계획

이 리포(`D:\UnrealEngineLab`, UE 5.8)에서 Animation Budget Allocator를 재현 가능하게 측정하기 위한 절차.
시스템 자체에 대한 설명과 CVar 레퍼런스는 [README.md](README.md) 참고.

---

## 0. 셋업 (한 번만)

이미 리포에 반영되어 있는 것:

| 항목 | 내용 |
|---|---|
| 플러그인 | `UnrealEngineLab.uproject`에 `AnimationBudgetAllocator` enabled |
| 모듈 의존성 | `UnrealEngineLab.Build.cs`의 `PrivateDependencyModuleNames`에 `AnimationBudgetAllocator` 추가 |
| 테스트 액터 | `Source/UnrealEngineLab/AnimBudget/AnimBudgetTestSpawner.{h,cpp}` |
| 테스트 에셋 | `Content/Characters/Mannequins/` (엔진 `Templates/TemplateResources/High/Characters`에서 복사) |

### 0.1 빌드

Build.cs에 모듈 의존성이 추가됐기 때문에 **Live Coding으로는 안 되고 전체 리빌드가 필요하다.**

1. Unreal Editor를 완전히 종료
2. 프로젝트 파일 재생성 후 빌드:

```bash
"D:/UE_5.8/Engine/Build/BatchFiles/Build.bat" UnrealEngineLabEditor Win64 Development -Project="D:/UnrealEngineLab/UnrealEngineLab.uproject" -WaitMutex
```

3. 에디터 재실행

### 0.2 테스트 레벨 구성

1. 빈 레벨을 만들고 `Content/Maps/AnimBudgetTest` 로 저장 (없으면 Basic 레벨로 시작)
2. `AnimBudgetTestSpawner`를 레벨에 배치하고 Details에서 설정:

| 프로퍼티 | 값 | 비고 |
|---|---|---|
| Test Mesh | `SKM_Manny_Simple` | `/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple` |
| Test Anim Instance | `ABP_Unarmed` | `/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed` |
| Grid Size | `20` | 400개. 사양에 따라 조정 |
| Grid Spacing | `150.0` | cm |
| Enable Budget On Begin Play | `true` | 월드별 게이트 (README 2.2절) |
| Auto Calculate Significance | `true` | 거리 기반 significance |
| Bind Reduce Work | `true` | reduced work 경로 활성화 |
| Report Interval Seconds | `0.0` | 필요할 때만 켜기 |

3. PlayerStart를 그리드에서 약 1500cm 떨어진 곳에 배치 (그리드 절반 정도가 화면에 들어오게)

> 그리드 크기는 **Game 스레드가 실제로 애니메이션에 눌리는 지점**까지 올려야 의미가 있다.
> `stat unit`의 Game이 baseline에서 눈에 띄게 늘어날 때까지 Grid Size를 키운다.

### 0.3 콘솔 명령

테스트 액터가 등록하는 명령:

| 명령 | 설명 |
|---|---|
| `AnimBudgetTest.Enable <0\|1>` | 월드별 allocator 토글 |
| `AnimBudgetTest.Spawn <N>` | 그리드를 N x N 으로 재생성 |
| `AnimBudgetTest.Clear` | 스폰된 컴포넌트 전부 제거 |
| `AnimBudgetTest.Report` | 컴포넌트 수 / reduced work 수 / 두 게이트 상태 로그 출력 |

`AnimBudgetTest.Report`는 **두 게이트가 모두 켜졌는지**를 `budgeting ACTIVE / INACTIVE`로 알려준다.
측정 시작 전에 항상 한 번 확인할 것.

---

## 1. 측정 지표

매 시나리오에서 같은 값을 기록한다.

| 지표 | 출처 | 의미 |
|---|---|---|
| Game (ms) | `stat unit` | 게임 스레드 프레임 시간. **주 지표** |
| Num Ticked Components | `stat AnimationBudgetAllocator` | 실제 틱한 컴포넌트 수 |
| Num Registered Components | 동일 | 전체 등록 수 (그리드 크기와 일치해야 함) |
| SmoothedBudgetPressure | 동일 | 1.0 초과 = 오버버짓 |
| Average Work Unit (ms) | 동일 | 컴포넌트 1개 평균 비용 |
| AnimQuality | CSV `AnimationBudget` | NumTicked / 전체. **주 품질 지표** |
| AverageTickRate | CSV 동일 | 평균 틱 간격 |
| reducedWork | `AnimBudgetTest.Report` | reduced work 상태인 컴포넌트 수 |

### 1.1 공통 측정 준비

PIE 진입 후, 카메라를 고정하고 **10초 안정화** 후 측정한다
(`WorkUnitSmoothingSpeed`, `StateChangeThrottleInFrames` 때문에 값이 수렴하는 데 시간이 걸린다).

```
stat unit
stat AnimationBudgetAllocator
t.MaxFPS 0
```

CSV로 남길 경우:

```
csvprofile start
(10초 이상 대기)
csvprofile stop
```

결과는 `Saved/Profiling/CSV/` 에 떨어진다.

---

## 2. 시나리오

### 시나리오 A — Baseline vs Budget (핵심)

allocator를 껐을 때와 켰을 때의 게임 스레드 시간을 비교한다.

```
# A-1 baseline
AnimBudgetTest.Enable 0
a.Budget.Enabled 0
AnimBudgetTest.Report        # -> budgeting INACTIVE 확인

# A-2 budget on
a.Budget.Enabled 1
AnimBudgetTest.Enable 1
a.Budget.BudgetMs 1.0
AnimBudgetTest.Report        # -> budgeting ACTIVE 확인
```

**기대 결과**: A-2에서 Game(ms)이 눌리고, Num Ticked < Num Registered, AnimQuality < 1.0.
A-2의 Game(ms) 감소분이 baseline의 애니메이션 비용에 비례해야 한다.

> A-1에서 Game(ms)이 A-2와 거의 같다면 부하가 부족한 것이다. Grid Size를 키워서 다시.

### 시나리오 B — BudgetMs 스윕

```
a.Budget.BudgetMs 0.25
a.Budget.BudgetMs 0.5
a.Budget.BudgetMs 1.0
a.Budget.BudgetMs 2.0
a.Budget.BudgetMs 5.0
```

각 값에서 10초 안정화 후 기록.

**기대 결과**: BudgetMs가 낮을수록 AnimQuality가 떨어지고 AverageTickRate가 올라가며,
`BudgetedAnimation` 타이밍이 BudgetMs 근처에 수렴한다. 이 곡선이 **budget이 실제로 지켜지는지에 대한 증거**다.

### 시나리오 C — Significance 우선순위

카메라를 그리드 한쪽 끝으로 옮기고 `a.Budget.Debug.Enabled 1`로 확인.

```
a.Budget.Debug.Enabled 1
a.Budget.Debug.VerboseActive 1
a.Budget.Debug.Verbose.ShowOnCanvas 1
```

**기대 결과**: 카메라에 가까운 메시가 always-tick, 먼 메시가 throttled/interpolated로 분류된다.
`a.Budget.AutoCalculatedSignificanceMaxDistance`를 3000(cm)으로 낮추면 훨씬 좁은 범위만 살아남아야 한다.

### 시나리오 D — Reduced work 경로

reduced work는 `OnReduceWork` 델리게이트가 바인드된 컴포넌트에만 적용된다 (README 4절).
`Bind Reduce Work = true`인 상태에서:

```
a.Budget.BudgetMs 0.2                        # 강한 압력
a.Budget.BudgetFactorBeforeReducedWork 1.5
AnimBudgetTest.Report                        # reducedWork > 0 이어야 함
```

대조군으로 스포너의 `Bind Reduce Work`를 false로 두고 재시작하면 `reducedWork`가 계속 0이어야 한다.

emergency 단계 확인:

```
a.Budget.BudgetMs 0.1
a.Budget.BudgetPressureBeforeEmergencyReducedWork 1.2
AnimBudgetTest.Report                        # reducedWork 가 거의 전체 수에 근접
```

### 시나리오 E — 화면 밖 처리

카메라를 돌려 그리드를 화면 밖으로 보낸다.

```
a.Budget.MaxTickedOffsreen 4     # 오타 주의: Offsreen
```

**기대 결과**: Num Ticked가 `MaxTickedOffsreen` 근처까지 떨어진다.
값을 32로 올리면 그만큼 늘어나야 한다.

### 시나리오 F — 강제 오버라이드 (sanity check)

예산 계산 로직을 배제하고 스로틀링 자체의 효과만 본다.

```
a.Budget.Debug.Force 1
a.Budget.Debug.Force.Rate 4      # 전부 4프레임에 1번 틱
a.Budget.Debug.Force.Interp 1
```

**기대 결과**: Game(ms)이 baseline의 대략 1/4 수준. 이 값이 시나리오 A의 **이론적 하한**이다.

---

## 3. 결과 기록 템플릿

측정 결과는 `Docs/AnimationBudgetAllocator/results/YYYY-MM-DD-<하드웨어>.md` 로 남긴다.

```markdown
# 측정 결과 YYYY-MM-DD

- 하드웨어: CPU / GPU / RAM
- 빌드: Development Editor (PIE) / Development Standalone
- 메시: SKM_Manny_Simple + ABP_Unarmed
- Grid Size: N (= N*N 컴포넌트)

## 시나리오 A

| 조건 | Game (ms) | Num Ticked | Registered | AnimQuality | BudgetPressure |
|---|---|---|---|---|---|
| baseline (off) | | | | 1.0 | - |
| BudgetMs 1.0 | | | | | |

## 시나리오 B

| BudgetMs | Game (ms) | AnimQuality | AverageTickRate | Avg Work Unit (ms) |
|---|---|---|---|---|
| 0.25 | | | | |
| 0.5 | | | | |
| 1.0 | | | | |
| 2.0 | | | | |
| 5.0 | | | | |

## 관찰 / 이슈
```

---

## 4. 주의사항

- **PIE는 에디터 오버헤드가 섞인다.** 절대 수치가 필요하면 Standalone(`-game`) 또는 패키징 빌드로 측정한다.
  시나리오 간 상대 비교 목적이면 PIE로도 충분하다.
- **`t.MaxFPS 0`을 반드시 설정한다.** 프레임 레이트가 캡되면 Game(ms) 차이가 묻힌다.
- **URO와 겹치지 않게 한다.** allocator 등록 시 URO가 강제로 꺼지므로, URO와의 비교는
  allocator를 끈 상태에서 별도로 측정해야 한다 (README 2.4절).
- **10초 안정화를 지킨다.** `StateChangeThrottleInFrames`(기본 30) 때문에 상태 전환이 의도적으로 느리다.
- 그리드를 재생성(`AnimBudgetTest.Spawn`)한 직후에는 `InitialEstimatedWorkUnitTime` 추정치로 시작하므로
  첫 몇 초 값은 신뢰하지 않는다.
