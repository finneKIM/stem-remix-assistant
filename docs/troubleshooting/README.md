# 트러블슈팅 로그

날짜별 묶음으로 작업 흐름 정리.

| 날짜 | 묶음 | 건수 |
|---|---|---|
| 2026-09-21 | madmom → librosa + BTC-ISMIR2019 전환 과정 | 6 |
| 2026-10-02 | MusiConGen 스템 단위 생성 시도 | 1 |
| 2026-10-30 | 조건부 음악 생성의 음질 저하 원인 분해 | 6 |

---

## 2026-09-21 — madmom → librosa + BTC-ISMIR2019 전환 과정

오디오 분석 파이프라인의 코드·비트 인식 도구를 [madmom](https://github.com/CPJKU/madmom)에서 [librosa](https://librosa.org/) + [BTC-ISMIR2019](https://github.com/jayg996/BTC-ISMIR19) 조합으로 전환. 전환 결정의 근거와 대체 도구 검증 과정에서 발생한 문제 6건.

### 목록

1. [madmom이 Python 3.13 / numpy 2.x 환경에서 구조적으로 비호환인 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_madmompython313numpyincompatibility.md) — 전환을 결정하게 된 근본 원인
2. [BTC-ISMIR2019 실행 시 yaml.load() Loader 인자 누락 에러](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_btcismir2019yamlloadererror.md)
3. [BTC-ISMIR2019 실행 시 np.float 등 제거된 numpy 별칭 에러](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_btcismir2019npfloatdeprecated.md)
4. [BTC-ISMIR2019 체크포인트 로드 시 torch.load weights_only 에러](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_btcismir2019torchloadweightsonly.md)
5. [Colab에서 apt-get install fluidsynth가 원인 불명으로 실패](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_fluidsynthaptinstallfailure.md)
6. [Colab에서 별도로 전달받은 .py 유틸 모듈을 import하지 못하는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20260921_colablocalmoduleimporterror.md)

### 핵심 요약

madmom은 오래된 코드베이스(대략 Python 3.6~3.8 / numpy 1.x대 기준)라 최신 환경(Python 3.13 / numpy 2.5.3)에서 문법 자체가 제거된 문제(97건/19개 파일)와 Cython 바이너리 재컴파일 리스크까지 겹쳐, 계속 패치하기보다 대체 도구로 전환하는 것이 더 안전하다고 판단했다.

대체 도구로 선택한 BTC-ISMIR2019는 순수 PyTorch 기반이라 바이너리 호환성 문제가 없었고, 실제로 겪은 문제도 모두 "라이브러리가 문법을 지원 중단한" 근본적 문제가 아니라 "보안 강화를 위해 기본값이 바뀐" 가벼운 API 변경(PyYAML의 Loader 인자 필수화, numpy의 구버전 타입 별칭 제거, PyTorch의 weights_only 기본값 변경)이었다. 세 가지 모두 한두 줄의 패치로 해결되었고, 최종적으로 원곡에서 코드 진행 추출까지 성공했다.

### 시사점

- 정규식을 셸 명령(`grep -E`)과 언어 내장 모듈(Python `re`)에서 함께 쓸 때는 문법 차이(특히 lookahead/lookbehind 지원 여부)를 주의해야 한다. "결과 없음"을 그대로 믿지 않고 재검증하는 습관이 필요하다.
- 원인 불명의 설치 실패는 로그를 캡처만 하지 말고 화면에 그대로 출력해야 원인을 알 수 있다.
- 오래된 오픈소스 코드베이스를 최신 환경에서 실행할 때는, 실제로 "언어/라이브러리가 문법 자체를 지원 중단"한 문제와 "기본 동작만 더 안전하게 바뀐" 문제를 구분하는 것이 중요하다. 후자는 대개 인자 하나만 명시하면 해결된다.

---

## 2026-10-02 — MusiConGen 스템 단위 생성 시도

목표 스템(drums)만 재생성하려고 그 스템을 생성 조건으로 직접 전달했다가 음질이 저하됐다. MusicGen 계열 모델이 스템 단위 생성을 지원하지 않아 구조적으로 불가능한 접근이었고, "전체 트랙 생성 → Demucs 재분리 → 목표 스템 추출" 구조로 정정했다.

### 목록

1. [MusiConGen에 목표 스템을 생성 조건으로 전달해 음질이 저하된 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261002_musicongendrumstemqualitydegradation.md)

---

## 2026-10-30 — 조건부 음악 생성의 음질 저하 원인 분해

조건부 음악 생성 모델(MusiConGen)에 원곡의 코드 진행·BPM을 조건으로 넣어 백킹 트랙을 재생성. 결과물의 잡음이 심해 비트와 코드 진행을 판별할 수 없었고 평가 지표 측정이 막혔다. 원인을 분해하며 확인한 6건.

**6건 중 5건은 에러를 내지 않는다.** 예외도 경고도 없이 잘못된 값이나 상태로 진행된다. 각 문서의 "에러" 절에는 로그 대신 관측값을 싣고, 로그가 없다는 사실을 함께 적었다.

### 목록

1. [생성 길이가 학습 segment_duration과 다르면 조건의 prepend 경로가 무시되는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_conditionfuserhardcodedconditionlength.md) — 코드 결함 기여분을 특정한 건
2. [librosa.beat.beat_track이 start_bpm 없이 호출되면 템포를 2배로 측정하는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_librosabeattrackoctaveerror.md) — 측정 도구 자체의 함정
3. [비트 간격을 프레임 정수로 계산하면 지시한 BPM과 실제 BPM이 달라지는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_beatgapintegerfloortempodrift.md) — 버그가 아니라 양자화의 필연적 결과
4. [589바이트짜리 코덱 체크포인트를 파일 손상으로 오판한 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_encodeccompressionstatedictpointerfile.md) — 실제로는 Hub 참조 포인터
5. [저장소의 requirements.txt를 그대로 설치하면 Colab 환경이 깨지는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_musicongencolabenvironmentrecovery.md) — 복구를 5셀로 고정
6. [노트북 재생 위젯의 base64 오디오가 저장소에 커밋되는 문제](https://github.com/finneKIM/stem-remix-assistant/blob/main/docs/troubleshooting/20261030_notebookoutputbase64audiocommitbloat.md)

### 핵심 요약

원인은 하나가 아니라 세 층이었다. 단일 원인을 전제한 탓에 초기에 시간을 소모했다. 기준선 두 개(원곡의 코덱 왕복 결과, 저자 공식 설정 대조군)로 정규화하자 세 층으로 갈라졌다.

| 층 | 기여 | 성격 |
|---|---|---|
| 모델 고유 잡음 | 코덱 왕복 대비 5.3~7.1배 | 저자 공식 설정으로도 동일. 통제 밖 |
| 조건 주입 코드 결함 | 추가 약 1.7배 | 생성 길이를 학습 설정에 맞춰 해결 |
| 잔여 초과분 | 추가 1.17배 | 조건별 가중치 스케일 차이로 추정. 미해결 |

**아무것도 바꾸지 않은 대조군이 이미 코덱 대비 7.12배였다.** 이 값을 확인한 뒤 진단 방향을 바꿨다. 그 전에는 "무엇을 잘못 넣었나"를 찾았고, 이후에는 "기여분 1.17배가 어디서 오나"로 질문을 좁혔다.

이 분해는 측정 설계 없이는 불가능했다. 지표를 세 개(spectral flatness, 8kHz 이상 에너지 비율, HPSS 타격음 비율) 두고 교차로 읽었다. `cfg_coef`를 3.0에서 1.5로 낮춘 실험에서 flatness는 +2.0%로 사실상 불변이었고 타격음 비율은 −37.3%였다. 귀로는 "멜로디가 선명해졌다"로 들렸다. flatness만 봤다면 "변화 없음", 타격음 비율만 봤다면 "37% 개선"으로 각각 오판한다. 두 지표를 함께 봐야 잡음 총량은 같고 성분 분포만 바뀌었다는 해석이 나온다.

2번 librosa 옥타브 오류도 같은 방식으로 찾았다. flatness와 고역 에너지는 같은 방향인데 BPM만 반대로 튀었고, 그래서 대상이 아니라 측정 쪽을 의심했다.

### 시사점

- 에러를 내지 않는 실패가 가장 비싸다. 예외는 발생 지점에서 멈추지만 잘못된 값은 그대로 다음 단계의 전제가 되고, 거기서 내린 결론이 문서에 남는다. 조용히 성공할 수 있는 지점에는 단정문을 심는다. `import`가 성공한 것과 그 모듈을 쓸 수 있는 상태인 것이 다르고, 생성이 완료된 것과 조건이 들어간 것이 다르다.
- 기준선이 없으면 절대값으로 좋고 나쁨을 판단할 수 없다. 이론적 하한선과 변경 없는 대조군이 있어야 추가 기여분을 분리할 수 있다.
- 개별 가설을 검증하기 전에 "전부 아님"을 한 번에 보일 방법을 찾는다. 생성 파라미터 가설 다섯 개를 저자의 공식 설정 대조군 한 번으로 동시에 기각했다. 같은 증상이 대조군에서도 나오면 내가 바꾼 것은 원인이 아니다.
- 판정 기준은 측정 전에 적는다. 결과를 먼저 보면 자기 가설에 유리하게 해석하게 된다. `cfg_coef` 실험은 한 지표가 불변이고 다른 지표가 크게 움직인 애매한 결과였는데, 기준이 먼저 있었기 때문에 기각으로 끝낼 수 있었다.
- 라이브러리의 하드코딩된 숫자는 학습 설정에서 출처를 찾는다. 출처를 확인하면 왜 그렇게 짜도 당시에는 문제가 없었는지와 어떤 입력에서 깨지는지가 동시에 설명된다. 출처를 모르면 "이상한 코드"로만 보이고 어느 범위가 안전한지 판단할 수 없다.
- 측정 범위를 넓혀 본다. 가장 중요한 사실은 측정 대상을 방금 만든 파일 하나에서 전체 여섯 개로 넓힌 순간 나왔다. 측정 함수는 이미 있었고 범위를 넓히는 비용은 루프 한 줄이었다.
- 미해결 항목은 근거와 검증 방법을 함께 적어 남긴다. 그러면 미완이 아니라 후속 과제가 된다.
- 조치를 제안하기 전에 그 조치가 실행 가능한 환경인지 확인한다. 표준 해법이 지금 환경에서 쓸 수 없는 경우가 있다. 노트북 출력 문제의 표준 해법은 git filter이고, 웹 에디터로 직접 커밋하는 흐름에는 로컬 저장소가 없어 쓸 수 없다.
