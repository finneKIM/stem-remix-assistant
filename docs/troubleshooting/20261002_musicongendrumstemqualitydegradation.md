# [2026-10-02] MusiConGen 드럼 스템 코드 조건화 생성 — 음질 저하(노이즈·템포·화성·음색 전부 불일치)

## 상황

Colab 재연결 후 복구한 MusiConGen 파이프라인으로 환경설정 → config.yaml 로드 → BTC-ISMIR19 Drive 복원 → librosa BPM/코드 추출 → chord_str/bpm_int 계산까지 마치고 duration_sec 스윕(10초/15초/20초, seed=42, TARGET_STEM=drums)으로 음원 3개를 생성해 청취했다.

## 문제

생성된 3개 음원(musicongen_drums_10s_seed42.wav 등) 모두 음질이 심각하게 나빴다. 구체적으로 네 가지 증상이 동시에 나타났다.

- 잡음/지지직거림(static/noise)
- 템포가 원곡과 안 맞음
- 코드 진행이 원곡과 안 맞는 이상한 화성
- 드럼 스템인데 멜로디/화성 악기 소리가 섞여서 이상함

네 증상이 동시에 겹치다 보니 생성 자체가 제대로 안 된 것(예: 재생 버그, 혹은 원본 파일이 그대로 재생된 것)은 아닌지도 의심됐다.

## 원인

먼저 재생/생성 메커니즘 자체는 문제가 없음을 확인했다. `model.generate_with_chords_and_beats([PROMPT], [chord_str], [bpm_int], [4])`가 반환한 `wav` 텐서를 `audio_write`로 매번 새 경로(`experiments/exp_002_musicongen/outputs/musicongen_drums_{duration}s_seed42.wav`)에 저장한 것이므로 원본 트랙/스템을 재생한 게 아니라 모델이 실제로 추론해 만들어낸 새 오디오가 맞다.

근본 원인은 모델-용도 불일치였다. MusiConGen은 드럼 전용 스템을 생성하도록 학습된 모델이 아니라, 코드 진행(chord)과 BPM 조건에 맞춰 기타·베이스·드럼 등이 함께 섞인 풀 백킹 트랙(반주 전체)을 생성하도록 학습된 모델이다. 다음 3개 소스로 교차 확인했다.

- 논문(arXiv 2407.15060): "realistic backing track music that aligns with the specified conditions" — 생성 목표가 반주 전체.
- 공식 데모 페이지(musicongen.github.io): 샘플이 "electric guitar, bass, drums"(록/블루스), "electric piano"(재즈), "trumpet, saxophone"(펑크)처럼 여러 악기가 섞인 풀 밴드 반주로 구성됨. 학습 조건은 RWC-pop-100 데이터셋의 코드 진행+BPM 라벨.
- GitHub README(YatingMusic/MusiConGen): 전처리 과정이 Demucs로 보컬 스템만 제거하고 나머지는 풀 믹스로 학습에 사용한다고 명시. `TARGET_STEM`처럼 특정 악기만 분리 생성한다는 개념이 원본 모델/API에 아예 없음 — 파이프라인이 자체적으로 붙인 라벨일 뿐이다.

여기에 더해 조건화 입력 자체도 거칠었다.

- `chords_to_musicongen_format`이 BTC 코드 이벤트 15개를 마디/박자 정렬 없이 단순 간격 샘플링으로 8개만 추출(chord_str: "F C D:min C D:min G C F")
- `[4]` 4/4박자를 하드코딩(원곡 실제 박자와 다를 수 있음)
- 10초처럼 짧은 duration에 `extend_stride=duration//2`로 생성 윈도우를 겹쳐 잇는 과정에서 아티팩트 가능성

종합하면, TARGET_STEM=drums로 코드 조건화 생성을 시도한 것 자체가 모델의 학습 목적과 맞지 않았고 여기에 거친 조건화 입력까지 겹쳐서 노이즈·템포·화성·음색이 전부 어긋난 품질로 나타났다.

## 해결

TARGET_STEM을 다른 악기로 바꿔보는 임시 대안이 아니라, 프로젝트 기획서(PROPOSAL.md)와 파이프라인 설계 문서를 재확인해 원래 설계대로 되돌리는 것으로 방향을 정정했다.

- 기획서에 이미 명시돼 있던 전제: 스템 하나만 재생성하는 것은 MusicGen 계열 모델(MusiConGen 포함)로는 불가능하며, (1) 전체 트랙을 조건부로 새로 생성 → (2) Demucs로 재분리 → (3) 원하는 스템만 추출하는 우회가 필요하다.
- TARGET_STEM은 생성 호출의 조건이 아니라, 2단계 재분리 이후에 어떤 스템을 추출할지 고르는 라벨이어야 한다. 이번 품질 저하는 이 라벨을 생성 단계에 잘못 끌어들인 구현 실수였지, 설계 자체의 결함이 아니었다.
- 재시도 계획: `TARGET_STEM`을 생성 호출(`model.generate_with_chords_and_beats(...)`)에서 제거하고, 이미 원곡 전체(15초) 기준으로 추출된 chord_str/bpm_int 그대로 duration_sec=15로 전체 백킹트랙을 재생성한다. 그 다음 Demucs로 재분리해 drums 스템을 추출하고, 원곡 drums 스템과 비교 청취한다.
- 현재 단계는 파이프라인 A(MusiConGen) 검증 중이며, 파이프라인 B(MusicGen-Melody/Style)는 아직 테스트 전이다 — 두 파이프라인의 우열 비교(A/B)는 각각 구현·검증을 마친 뒤의 단계다.

## 배운 점

조건화 생성 모델을 쓸 때는 파라미터 설정을 의심하기 전에 먼저 이 모델이 애초에 뭘 생성하도록 학습됐는가를 공식 논문/데모/README에서 확인해야 한다. 증상이 노이즈·템포·화성·음색 등 여러 축에서 동시에 나타나면, 세부 파라미터 버그보다 모델-태스크 불일치 가능성을 먼저 의심하는 게 디버깅 시간을 아낀다.
