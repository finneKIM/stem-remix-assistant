# 체크포인트 저장 폴더 이름이 패키지 이름과 겹쳐서 import가 깨진 이야기

## 상황

MusiConGen 사전학습 체크포인트(`compression_state_dict.bin`, `state_dict.bin`)를 Hugging Face에서 받아 저장할 폴더를 만든 뒤, MusicGen 모델을 로드하려고 `import audiocraft`를 실행했다.

```python
ckpt_dir = "audiocraft/ckpt/musicongen"
os.makedirs(ckpt_dir, exist_ok=True)
```

## 문제

`import audiocraft` 자체는 에러 없이 성공했다. 그런데 바로 다음 줄인 `from audiocraft.data.audio import audio_write`에서 이런 에러가 났다.

```
ModuleNotFoundError: No module named 'audiocraft.data'
```

저장소 안에 `audiocraft/audiocraft/data/` 폴더가 분명히 존재하는데도 못 찾는 상황이라 처음엔 원인을 가늠하기 어려웠다.

## 원인

체크포인트를 저장하려고 만든 `ckpt_dir = "audiocraft/ckpt/musicongen"`이 상대경로였는데, 이 코드를 실행한 시점의 작업 디렉터리가 저장소 루트가 아니었다. 그 결과 `os.makedirs()`가 의도와 다른 위치에 `audiocraft`라는 이름의 **빈 디렉터리**를 새로 만들어버렸다.

이 빈 디렉터리에는 `__init__.py`가 없다. 파이썬은 `__init__.py`가 없는 디렉터리를 "네임스페이스 패키지"로 취급하는데, 하필 이름이 진짜 `audiocraft` 패키지와 동일했기 때문에 `sys.path` 검색 순서상 이 빈 폴더가 실제 코드보다 먼저 매칭돼버렸다.

진단에 결정적이었던 확인 방법은 이거였다.

```python
import audiocraft
print(audiocraft.__file__)   # None
print(audiocraft.__path__)   # _NamespacePath(['.../audiocraft', '.../audiocraft'])
```

`__file__`이 `None`으로 나오는 것이 네임스페이스 패키지(실제 `__init__.py`가 없는 폴더가 패키지처럼 인식된 상태)라는 확실한 신호다.

## 해결

1. 이름이 충돌하는 빈 폴더를 다른 이름으로 옮겨서 체크포인트 파일은 보존하면서 이름 충돌만 없앴다.
2. 진짜 패키지 코드가 있는 경로를 `sys.path.insert(0, ...)`로 명시적으로 최우선 등록했다.
3. 이미 잘못 캐싱된 `sys.modules`의 관련 엔트리를 지우고 다시 `import`해서, 경로를 고친 게 실제로 반영되도록 했다.

```python
import shutil, os, sys

if os.path.exists("./audiocraft") and not os.path.exists("./audiocraft/audiocraft"):
    shutil.move("./audiocraft", "./musicongen_ckpt")

sys.path.insert(0, "/path/to/real/audiocraft/package/root")

for mod in list(sys.modules):
    if mod == "audiocraft" or mod.startswith("audiocraft."):
        del sys.modules[mod]

import audiocraft
print(audiocraft.__file__)  # 실제 __init__.py 경로가 나와야 정상
```

## 배운 점

- 산출물을 저장할 디렉터리 이름을 지을 때는 이미 import 경로상에 존재하는 패키지 이름과 겹치지 않도록 신경 써야 한다. 특히 노트북 환경처럼 작업 디렉터리가 저장소 루트와 다를 수 있는 곳에서는, 상대경로가 의도치 않은 위치에 폴더를 만들 수 있다.
- `import`가 에러 없이 성공했다고 해서 원하는 모듈이 로드됐다는 보장은 없다. `__file__`과 `__path__`를 확인하는 습관이 이런 종류의 네임스페이스 패키지 충돌을 빠르게 진단하는 데 유용했다.
- 캐시된 `sys.modules`는 경로를 고쳐도 자동으로 갱신되지 않는다. 문제를 해결한 뒤에는 관련 모듈을 명시적으로 지우고 재import해야 한다.
