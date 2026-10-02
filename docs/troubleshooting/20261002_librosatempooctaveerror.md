# [2026-10-02] librosa 스템 BPM이 원곡의 정확히 2배로 추정됨 — 템포 옥타브 오류

## 상황

- madmom이 Python 3.13 바이너리 비호환으로 완전히 폐기된 뒤, BPM/비트/온셋 추출 기능을 librosa 기반 함수로 새로 작성했다.

- 최초 작성한 코드는 다음과 같다.

```python
import librosa

def get_bpm(path):
    y, sr = librosa.load(path, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)

orig_bpm = get_bpm(ORIG_TRACK)
orig_beats = get_beats(ORIG_TRACK)
orig_onsets = get_onsets(ORIG_TRACK)

stem_bpm = get_bpm(ORIG_STEM)
stem_beats = get_beats(ORIG_STEM)
```

- 실행 결과는 다음과 같았다.

```
원곡 BPM: 89.3 / 스템 BPM: 178.2 / 차이: 88.92
원곡 비트 개수: 22 / 온셋 개수: 83
```

## 문제

- 에러는 나지 않았지만 같은 곡에서 Demucs로 분리한 스템인데도 BPM이 원곡의 정확히 2배(178.2 ≈ 89.3 × 2)로 나왔다.

- 템포가 달라질 이유가 없는 상황이라, 세 가지 가설을 세우고 순서대로 검증했다.

### 가설 1 — 비트 자체가 잘못 찍혔는가, 숫자만 잘못 보고됐는가

- 검증 코드: 라이브러리가 보고한 BPM과, 실제로 찾아낸 비트 간격에서 직접 역산한 BPM을 비교했다.

```python
import numpy as np

def bpm_from_beat_intervals(beats):
    if len(beats) < 2:
        return None
    intervals = np.diff(beats)
    return 60.0 / np.median(intervals)

print(f"원곡: beat_track BPM = {orig_bpm:.1f} / 간격 역산 BPM = {bpm_from_beat_intervals(orig_beats):.1f}")
print(f"스템: beat_track BPM = {stem_bpm:.1f} / 간격 역산 BPM = {bpm_from_beat_intervals(stem_beats):.1f}")
```

- 결과:

```
원곡: beat_track BPM = 89.3 / 간격 역산 BPM = 89.3
스템: beat_track BPM = 178.2 / 간격 역산 BPM = 178.2
```

- 해석: 두 값이 완전히 일치 → 숫자만 잘못 보고된 게 아니라, 비트 자체를 실제보다 2배 촘촘하게 찍은 탐지 단계 오류로 확정.

### 가설 2 — 원곡 BPM을 힌트로 주면 수렴하는가

- 검증 코드:

```python
y_stem, sr_stem = librosa.load(ORIG_STEM, sr=None)
tempo_hinted, beats_hinted = librosa.beat.beat_track(y=y_stem, sr=sr_stem, start_bpm=orig_bpm)
print(f"힌트 없이: {stem_bpm:.1f} BPM / 원곡 BPM({orig_bpm:.1f})을 힌트로 줬을 때: {float(np.asarray(tempo_hinted).reshape(-1)[0]):.1f} BPM")
```

- 결과:

```
힌트 없이: 178.2 BPM / 원곡 BPM(89.3)을 힌트로 줬을 때: 90.7 BPM
```

- 해석: 힌트를 주자 원곡과 거의 같은 값(90.7)으로 수렴 → 탐지 범위/우선순위의 문제임을 확인, 동시에 원곡과 스템의 실제 템포가 같다는 전제도 재확인.

### 가설 3 — 특정 구간(초반)이 전체 집계를 끌어당겼는가

- 검증 코드:

```python
onset_env = librosa.onset.onset_strength(y=y_stem, sr=sr_stem)
tempo_candidates = librosa.feature.tempo(onset_envelope=onset_env, sr=sr_stem, aggregate=None)
print("상위 템포 후보(앞 10개 프레임 추정치):", np.round(tempo_candidates[:10], 1))
print("전체 중앙값:", np.median(tempo_candidates))
```

- 결과:

```
상위 템포 후보(앞 10개 프레임 추정치): [178.2 178.2 178.2 178.2 178.2 178.2 178.2 178.2 178.2 178.2]
전체 중앙값: 90.67
```

- 해석: 초반 프레임은 전부 178.2로 쏠려 있지만 곡 전체 중앙값은 90.67 → 초반 구간의 국소 편향이 전체 단일 집계값을 끌어올린 것으로 확정.

## 원인

- 비트 트래킹은 자기상관(autocorrelation)으로 "몇 박마다 강세가 반복되는가"를 찾는데, 진짜 박자 주기뿐 아니라 그 정수배/분수배 지점에서도 비슷하게 강한 신호가 나와 구조적으로 혼동되기 쉽다.

- 스템에만 남은 드럼/퍼커션의 8분음표 단위 세부 리듬이 특히 초반 구간에서 강하게 나타나, 알고리즘이 그걸 박자로 오인했다.

- 위 세 가지 가설 검증 결과가 모두 같은 방향을 가리켜 옥타브 오류로 결론 내렸다.

## 해결

- 스템처럼 정답 기준(원곡 BPM)이 이미 있는 경우, `start_bpm` 힌트로 탐지 범위를 유도하도록 `get_bpm` 함수를 수정했다.

```python
def get_bpm(path, hint_bpm=None):
    y, sr = librosa.load(path, sr=None)
    if hint_bpm is not None:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=hint_bpm)
    else:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.asarray(tempo).reshape(-1)[0])

orig_bpm = get_bpm(ORIG_TRACK)                      # 원곡은 기준이므로 힌트 없이
stem_bpm = get_bpm(ORIG_STEM, hint_bpm=orig_bpm)    # 스템은 원곡 BPM을 힌트로
```

- 이 패턴은 이후 섹션 8(Alignment)에서 재생성 스템의 BPM을 구할 때도 `generate()` 호출 시 지정한 BPM 값을 힌트로 넘기는 방식으로 동일하게 적용하기로 했다.

## 배운 점

- 비트 트래킹 결과가 기준값의 정수배/분수배로 나오면(특히 정확히 2배) 우선 옥타브 오류를 의심한다.

- "보고값 vs 실측 역산값 비교 → 비율 확인 → 기준점으로 교차검증 → 구간별 분포 확인" 네 단계로 원인을 구조적으로 좁힐 수 있다.

- 에러 없이 숫자만 미묘하게 틀린 경우가 오히려 더 위험하다 — 넘어가면 다음 단계(정렬, 정량지표)에서 조용히 잘못된 결과로 이어진다.
