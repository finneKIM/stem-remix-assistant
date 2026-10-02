# [2026-10-02] audiocraft import 시 ModuleNotFoundError('av') — 일괄 설치 중 조용한 실패

## 상황

numpy를 최신 버전으로 되돌린 뒤(의존성 일괄 설치 셀에서 `av`도 함께 설치 대상에 포함돼 있었음), `sys.modules` 캐시를 정리하고 `audiocraft`를 다시 import했다.

```python
import sys

for mod in list(sys.modules):
    if mod == "audiocraft" or mod.startswith("audiocraft.") or mod == "librosa" or mod.startswith("librosa.") or mod == "numba" or mod.startswith("numba."):
        del sys.modules[mod]

sys.path.insert(0, "/content/MusiConGen/audiocraft")
import audiocraft
print("audiocraft 위치 확인:", audiocraft.__file__)
```

## 문제

```
ModuleNotFoundError: No module named 'av'
```

`audiocraft/data/audio.py`가 `import av`를 하는 지점에서 실패했다. 같은 에러가 이어서 `from audiocraft.models import MusicGen` 셀에서도 동일하게 재발했다.

## 원인

`av`는 의존성 일괄 설치 셀(`!pip install -q av julius einops ... transformers==4.31.0`)에 포함돼 있었지만, Colab 기본 Python(3.13)용 `av` 사전 빌드 wheel이 없어 설치가 조용히 실패했을 가능성이 높다. `-q` 옵션으로 설치 로그를 숨긴 상태였기 때문에 설치 단계에서는 실패 여부가 드러나지 않았고, 실제로 `import av`를 시도하는 시점에서야 문제가 드러났다. (동일한 패턴의 문제가 2026-09-21에도 한 번 발생한 적 있어 반복되는 유형이다.)

## 해결

verbose 로그로 실제 설치 실패 원인부터 확인했다.

```python
!pip install av --no-cache-dir -v 2>&1 | tail -n 60
```

소스 빌드로 빠지면서 ffmpeg 개발 헤더가 없어 컴파일에 실패하는 경우를 대비해, 필요 시 아래처럼 ffmpeg 관련 개발 패키지를 먼저 설치한 뒤 재시도하도록 했다.

```python
!apt-get -y install -q ffmpeg libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libswresample-dev libavfilter-dev
!pip install av --no-cache-dir
```

재설치 후 `import av`가 정상 동작했고, 이어서 `audiocraft` import와 `MusicGen.get_pretrained()`까지 통과했다.

## 배운 점

`-q`(quiet) 옵션으로 묶어서 여러 패키지를 한 번에 설치하면 그중 하나가 조용히 실패해도 셀 자체는 에러 없이 끝나버려서, 나중에 엉뚱한 import 지점에서야 문제가 드러난다. 특히 `av`처럼 바이너리 확장을 포함한 패키지는 Python 버전(3.13처럼 비교적 최신)에 따라 사전 빌드 wheel이 없을 수 있으므로, 일괄 설치 블록에 넣기보다 설치 직후 바로 `import`로 검증하는 단독 셀을 하나 더 두는 편이 디버깅 시간을 줄인다.
