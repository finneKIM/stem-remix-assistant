# [2026-10-02] librosa beat_track() tempo 배열 반환으로 인한 TypeError — madmom 대체 함수 작성 중

## 상황

madmom이 Python 3.13 바이너리 비호환 문제로 완전히 폐기되어(2026-09-21 결론), BPM/비트/온셋 추출 기능을 librosa 기반 함수로 새로 작성했다.

```python
import librosa

def get_bpm(path):
    y, sr = librosa.load(path, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)
```

이 함수로 원곡(`ORIG_TRACK`)의 BPM을 구하려고 `get_bpm(ORIG_TRACK)`을 호출했다.

## 문제

```
TypeError: only 0-dimensional arrays can be converted to Python scalars
```

`get_bpm` 안의 `return float(tempo)` 줄에서 발생했다. 같은 패턴(librosa 호출 후 바로 사용)인 `get_beats`/`get_onsets`는 에러가 나지 않았다.

## 원인

librosa 0.10 이상 버전부터 `beat_track()`이 반환하는 `tempo`가 스칼라 float이 아니라 `array([120.])`처럼 원소 1개짜리 numpy 배열로 바뀌었다. 과거 numpy 버전에서는 `float(array([120.]))`가 deprecation 경고만 내고 통과됐지만, 최신 numpy 버전에서는 아예 `TypeError`로 막는다. `get_beats`/`get_onsets`는 결과를 `float()`로 강제 변환하지 않고 `frames_to_time()`의 배열 결과를 그대로 리턴했기 때문에 같은 문제를 겪지 않았다.

## 해결

`tempo`를 1차원 배열로 강제 변환한 뒤 인덱싱해서 스칼라 원소를 꺼내고 나서 `float()`를 적용했다.

```python
import numpy as np

def get_bpm(path):
    y, sr = librosa.load(path, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(np.asarray(tempo).reshape(-1)[0])
```

수정 후 재실행 결과:

```
원곡 BPM: 89.3 / 스템 BPM: 178.2 / 차이: 88.92
원곡 비트 개수: 22 / 온셋 개수: 83
```

## 배운 점

라이브러리 메이저/마이너 버전이 올라가면서 "아예 안 되는" 문제가 아니라 반환 타입(스칼라 ↔ 배열)만 미묘하게 바뀌는 경우가 있는데, 이런 경우가 오히려 디버깅하기 더 까다롭다. import 자체는 멀쩡히 되고 다른 함수들은 통과하기 때문에, 문제가 생긴 그 지점만 보고 "내 코드가 잘못됐나" 하고 헤매기 쉽다. 라이브러리 반환값의 타입/shape을 바로 신뢰해서 `float()`/`int()`로 강제 변환하지 말고, 새로 함수를 작성할 때는 한 번쯤 `type()`/`.shape`을 직접 print해서 실제 반환 형태를 확인하는 습관이 필요하다.

**참고(후속 확인 필요)**: 스템 BPM(178.2)이 원곡 BPM(89.3)의 정확히 약 2배로 나왔다 — librosa 비트 트래킹에서 흔한 "옥타브 오류"(실제 템포의 2배 또는 1/2배로 잘못 추정)일 가능성이 있다. 이후 정렬/정량지표 단계에서 BPM 비율을 그대로 쓰기 전에 별도로 검증이 필요하다.
