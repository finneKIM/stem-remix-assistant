# Stem Remix Assistant

생성 → 분리 → 재생성 루프로 스템 단위 리믹스를 시도한 실험 프로젝트. 예산 0원, Google Colab 무료 T4에서 MusicGen/MusiConGen 생성과 Demucs 분리를 조합했다.

보컬 레슨 중 받은 피드백 — "요즘 AI로 음원을 많이 만드는데, 스템별로 나눠서 마음에 안 드는 것만 갈아끼우며 테스트할 수 있으면 좋겠다" — 에서 출발했다. 곡 전체를 다시 뽑는 것이 아니라, 원곡의 코드 진행과 템포를 유지한 채 특정 파트만 재생성하는 흐름을 만드는 것이 목표다.

**현재 상태**: 원본 분석(스템 분리 · 코드 인식 · BPM) → 조건부 재생성까지 동작한다. 재생성 음질이 코드 진행 일치도를 측정할 수 있는 수준에 못 미쳐, 그 원인을 정량 지표로 분해하는 단계에 있다. 원인을 3층으로 분리해 코드 결함 기여분은 제거했다 ([결과](#주요-결과--음질-저하-원인의-분리)).

---

## 빠른 실행 (3단계)

**Google Colab 전용이다.** 무료 T4 GPU와 Google Drive 연동을 전제로 만들었다.

1. [`notebooks/02a_regenerate_musicongen.ipynb`](notebooks/02a_regenerate_musicongen.ipynb) 를 Colab에서 연다
2. **"환경 복구" 섹션의 5개 셀**을 순서대로 실행한다 — 저장소 clone, 의존성 설치, MusiConGen 체크포인트(2.6GB) 다운로드, 모델 로드. 약 10분. 런타임 재시작은 필요하지 않다
3. **"생성" 섹션**을 실행한다. 결과 wav와 측정값이 Google Drive에 저장된다

> `requirements.txt`가 2026-10-30에 재검증된 조합이다. **MusiConGen 저장소 자체의 `requirements.txt`는 설치하지 않는다** — 의존성이 충돌한다.

---

## 문서

- 기획 배경, 기술 타당성 조사, 시스템 설계 → [`docs/PROPOSAL.md`](docs/PROPOSAL.md)
- 환경 세팅 가이드 → [`docs/ENVIRONMENT_SETUP.md`](docs/ENVIRONMENT_SETUP.md)
- 트러블슈팅 기록 (문제 → 원인 → 해결, 날짜별) → [`docs/troubleshooting/`](docs/troubleshooting/)
- 실험 간 비교 → [`docs/experiments/`](docs/experiments/)
- 실험별 설정·결과·결론 → [`experiments/`](experiments/) (기록 규칙은 [`experiments/README.md`](experiments/README.md))

---

## 노트북

- [`01_setup_and_test.ipynb`](notebooks/01_setup_and_test.ipynb) — 환경 확인, MusicGen 단독 생성, Demucs 단독 분리 테스트 (EXP-001)
- [`02a_regenerate_musicongen.ipynb`](notebooks/02a_regenerate_musicongen.ipynb) — EXP-002. MusiConGen 재생성 파이프라인(생성 → Demucs 재분리 → Alignment Engine), 환경 복구, 조건부 생성, 정량 측정

> 노트북을 작업 단계별로 분리하는 작업이 진행 중이다. Colab은 **노트북 하나가 VM 하나**이므로 분리 축을 "파이프라인 단계"가 아니라 **"무엇을 로드해야 하는가"**로 잡았다 — 측정은 librosa만 필요해 모델 없이 30초에 뜬다.

---

## 폴더 구조

```
docs/
  PROPOSAL.md               # 기획서
  ENVIRONMENT_SETUP.md      # 환경 세팅 가이드
  troubleshooting/          # 트러블슈팅 기록 (문제-원인-해결 md, 날짜별)
  samples/                  # 데모 오디오 샘플 (생성/분리 검증 결과물)
  experiments/              # 실험 간 비교 문서 (model_comparison.md)
notebooks/                  # Colab 노트북
src/
  audio_metrics.py          # 정량 지표 측정 — 단일 정의. 노트북에 복사 금지
experiments/                # 실험별 config, 결과, 결론 (규칙은 experiments/README.md)
  exp_002_musicongen/
    config.yaml             # 재현에 필요한 설정
    README.md               # 목적 · 방법 · 결과 · 결론
    metrics.csv             # 측정 기록 (append-only)
```

생성물(wav, 스템, 백업)은 Google Drive에 두고 저장소에 올리지 않는다. 생성 음원 1개가 base64로 약 2.6MB이고 git 히스토리는 되돌릴 수 없다.

---

## 파이프라인

```
원곡
 ├─ Demucs (htdemucs)   → 스템 4개 (vocals / drums / bass / other)
 ├─ BTC-ISMIR2019       → 코드 진행
 └─ librosa.beat        → BPM            ※ start_bpm 힌트 필수
        │
        ▼
  MusiConGen (MusicGen-melody 1.5B 파인튜닝, 코드·비트 조건부)
   ├─ LM      : 조건 → 오디오 토큰 예측
   └─ EnCodec : 토큰 → 32kHz 파형
        │
        ▼
  정량 평가 3지표 + 청취 메모
```

---

## 측정 설계

음질을 귀로만 말하지 않기 위해, 구현 전에 평가 기준을 먼저 정했다. 지표는 **세 개를 두고 교차로 읽는다.**

| 지표 | 의미 | 왜 필요한가 |
|---|---|---|
| spectral flatness | 스펙트럼의 평평함. 0에 가까우면 음정 있는 소리, 1에 가까우면 백색잡음 | 잡음 총량 |
| 8kHz+ 에너지 비율 | 고역이 전체 에너지에서 차지하는 비중 | "지지직" 계열 잡음은 고역에 몰린다. flatness와 독립적인 단서 |
| HPSS 타격음 비율 | 조화음/타격음 분리 후 타격음 쪽 에너지 비중 | **잡음 총량과 성분 분포를 구분한다** |

세 번째가 왜 필요한지는 실측으로 드러났다. `cfg_coef`를 3.0 → 1.5로 낮춘 실험에서 flatness는 +2.0%(불변)였지만 타격음 비율은 **−37.3%**였다. 청취상으로는 "멜로디가 선명해졌다"로 들렸는데, 실제로는 **잡음이 줄어든 것이 아니라 조화음 비중이 올라간 것**이었다. 지표가 하나였다면 어느 쪽으로든 오판했다.

측정 함수는 [`src/audio_metrics.py`](src/audio_metrics.py)에 단일 정의로 둔다. 노트북에 복사하지 않는다 — 복사본이 생기면 버전이 갈라지고 과거 측정값과의 비교가 조용히 무효가 된다.

---

## 주요 결과 — 음질 저하 원인의 분리

절대값만으로는 좋고 나쁨을 말할 수 없다. 기준선 두 개를 두고 정규화했다.

- **코덱 왕복**: 원곡을 EnCodec으로 인코딩 후 디코딩. 생성 모델이 도달할 수 있는 이론적 하한선
- **공식 설정 대조군**: MusiConGen 저자의 기본 설정을 그대로 실행. **우리가 추가한 분**을 재는 기준

| 실행 | flatness | ×코덱 | ×대조군 |
|---|---|---|---|
| 코덱 왕복 (하한선) | 0.00451 | 1.00 | 0.14 |
| 원곡 | 0.00679 | 1.51 | 0.21 |
| **공식 설정 대조군** | 0.03212 | **7.12** | **1.00** |
| 원곡 조건 30초 | 0.03765 | 8.35 | **1.17** |
| 원곡 조건 15초 | 0.06467 | 14.34 | **2.01** |

**저자의 공식 설정을 그대로 돌려도 코덱 대비 7.12배다.** 잡음의 대부분은 우리가 만든 것이 아니라 이 체크포인트가 32kHz에서 내는 소리의 기본 특성이다. 이 기준선이 없으면 통제 가능한 부분과 불가능한 부분을 구분할 수 없다.

| 층 | 기여 | 성격 | 대응 |
|---|---|---|---|
| ① 체크포인트 고유 잡음 | 코덱 대비 5.3~7.1배 | MusiConGen 1.5B 특성 | 통제 밖 (모델 교체 외) |
| ② `ConditionFuser` 결함 | 추가 약 1.7배 | 코드 결함 | **해결** |
| ③ 조건 주입 초과분 | 추가 1.17배 | `sum` 경로 추정 | 후속 검증 항목 |

②는 `audiocraft/modules/conditioners.py`의 `prepend` 분기가 조건 길이 1500을 CFG 드롭아웃 판별에 하드코딩한 것이다. 학습 설정이 `segment_duration: 30` × `frame_rate: 50` = 1500이므로 학습 중에는 문제가 없었고, 추론 시 15초(750프레임)를 넣으면 실제 조건이 드롭아웃으로 오판되어 235개 토큰이 0으로 채워진다. 30초로 전환해 flatness 41.8%, 고역 에너지 26.7% 감소를 확인했다.

상세 분석과 전체 측정값 → [`experiments/exp_002_musicongen/README.md`](experiments/exp_002_musicongen/README.md)

---

## 알려진 함정

실제로 잘못된 진단을 유발한 것들이다.

**`librosa.beat.beat_track`의 옥타브 오류** — `start_bpm` 힌트 없이 호출하면 템포를 2배 또는 절반으로 측정한다. 코덱 왕복 음원이 89 BPM 대신 178.6 BPM으로 측정되어 "코덱이 템포를 망가뜨린다"는 잘못된 결론으로 갈 뻔했다. 모든 측정에 힌트를 넘긴다.

**`beat_gap` 정수 내림** — `int(60/89*50) = int(33.70) = 33` → 실효 BPM은 50/33×60 = **90.91**이 된다. 89를 넣어도 모델은 90.91로 연주한다. 버그가 아니라 양자화의 필연적 결과지만, 모르면 "89를 넣었는데 91이 나온다"를 모델 오류로 진단한다.

**`compression_state_dict.bin`이 589바이트** — 손상이 아니다. `facebook/encodec_32khz`를 참조하는 포인터이며 `HFEncodecCompressionModel`로 로드되는 정상 설계다. 파일 크기만 보고 손상으로 판단해 한동안 잘못된 방향을 수사했다.

**madmom 사용 불가** — 제거된 numpy 별칭(`np.float`, `np.int` 등)을 19개 파일 97곳에서 참조한다. librosa + BTC 조합으로 대체했다.

---

## 실험

| ID | 내용 | 상태 |
|---|---|---|
| EXP-001 | 베이스라인 — MusicGen 단독 생성 + Demucs 분리 | 완료 |
| EXP-002 | MusiConGen 조건부 재생성 파이프라인 | **부분 완료** — 음질 저하 원인 3층 분리, ②층 제거. 코드 진행 일치도 측정은 보류 |
| EXP-003 | MusicGen-Melody / Style 파이프라인 | 예정 |

실험 기록 규칙(폴더명, 필수 파일, 브랜치 규약) → [`experiments/README.md`](experiments/README.md)

---

## 진행 현황

**완료**

- 기획, 환경 세팅, MusicGen·Demucs 단독 검증, 설계 확정
- 평가 지표 설계 및 측정 함수 구현
- EXP-002 재생성 로직 구현
- 음질 저하 원인 분리 — 모델 고유 특성(코덱 대비 5.3~7.1배)과 코드 결함 기여분(추가 1.7배)을 기준선으로 분리하고 결함분 제거

**진행 중**

- 노트북 분리 (로드 비용 기준 3개 + scratch)
- `src/` 모듈 추출 (`bootstrap`, `conditioning`, `io_drive`)

**미착수**

- ③층(조건 주입 초과분 1.17배) 검증 — forward hook으로 `sum` 경로 크기 실측
- 코드 진행 일치도 · 비트 정렬 측정 — ①층이 남아 판별 신뢰도 미확보
- EXP-003 — ①층이 더 낮은 모델이 있는지 비교
- `docs/ENVIRONMENT_SETUP.md` 갱신 — 현재 로컬 VSCode 경로가 함께 적혀 있으나 실제 작업은 Colab 전용이다

---

## 실행 환경

| 항목 | 값 |
|---|---|
| 플랫폼 | Google Colab (무료 T4) |
| 생성 모델 | MusiConGen (`Cyan0731/MusiConGen`) — MusicGen-melody 1.5B 파인튜닝 |
| 스템 분리 | Demucs `htdemucs` |
| 코드 인식 | BTC-ISMIR2019 |
| 샘플레이트 | 32,000 Hz / frame_rate 50 fps |
| 예산 | 0원 |

MusiConGen 가중치는 **CC-BY-NC** 라이선스다. 상업적 사용은 허용되지 않는다.
