# MusiConGen 저장소의 requirements.txt를 설치하면 Colab 환경이 깨진다

## 상황

Colab에서 MusiConGen으로 실험하는 중이었다. Colab은 런타임이 끊기면 설치한 패키지가 전부 사라지므로, 재연결할 때마다 환경을 다시 세워야 한다.

재연결 후 저장소의 `requirements.txt`를 그대로 설치하는 방식으로 복구를 시도했고, 그 경로가 반복적으로 실패하면서 복구에만 긴 시간이 들었다. 복구 비용이 커지자 실험 자체가 몇 주간 중단됐다.

## 에러

**이 건의 에러 로그는 보존하지 않았다.** 당시 출력을 남기지 않아 원문을 인용할 수 없다. 재구성하지 않고 관측한 사실만 적는다.

관측된 것:

- `pip install -r requirements.txt`(MusiConGen 저장소의 것)를 돌리면 설치 중 의존성 해석이 기존 Colab 패키지와 충돌했다
- 설치가 끝난 뒤에도 `import audiocraft`가 실패하거나, 성공해도 `audiocraft.__file__`이 `None`이 되는 상태가 나왔다
- 런타임 재시작을 반복하게 되고, 재시작하면 설치가 다시 날아간다

`audiocraft.__file__ is None`은 **네임스페이스 패키지가 잡힌 상태**를 뜻한다. 같은 이름의 디렉터리가 `sys.path`에 여러 개 있고 실제 패키지가 아닌 쪽이 먼저 잡히면 파이썬이 빈 네임스페이스 패키지를 만들어 주고, 그 안에는 아무것도 없다.

## 원인

원인이 두 겹이다.

### 1. 저장소 requirements와 런타임 기본 패키지의 충돌

MusiConGen 저장소의 `requirements.txt`는 저자 환경 기준으로 핀이 박혀 있다. Colab 런타임에는 torch, numpy 등이 이미 특정 버전으로 들어 있고, 그 조합을 저장소 핀으로 덮으려 하면 ABI가 어긋나는 패키지가 생긴다. 한 패키지를 고치면 다른 패키지가 깨지는 연쇄가 생겨 끝이 보이지 않는다.

### 2. audiocraft 경로가 두 곳에 생긴다

MusiConGen은 audiocraft를 저장소 안에 포함한 형태로 배포된다. 그런데 pip로 설치된 audiocraft가 이미 있거나, clone 위치가 여러 개면 **같은 이름의 import 후보가 둘 이상** 생긴다.

어느 쪽이 잡히는지는 `sys.path` 순서와 이미 import된 모듈 캐시(`sys.modules`)에 따라 달라진다. 특히 **한 번 잘못 import한 뒤에는 `sys.path`를 고쳐도 캐시가 남아 있어 계속 잘못된 쪽이 쓰인다.** 이것이 "경로를 고쳤는데도 안 된다"의 원인이고, 런타임 재시작으로 해결하려다 설치를 날리는 악순환을 만든다.

## 해결

### 1. 저장소 requirements를 쓰지 않고 검증된 조합을 따로 고정한다

한 번 성공한 환경에서 `pip freeze`를 떠서 **그 파일을 저장소에 커밋**하고, 복구할 때는 그것만 쓴다. 저자 환경의 핀이 아니라 **실제로 이 런타임에서 돌아간 조합**이 기준이다.

```python
# 성공한 세션에서 한 번만
import subprocess
with open("/content/drive/MyDrive/<project>/requirements.txt", "w") as f:
    f.write(subprocess.run(["pip", "freeze"], capture_output=True, text=True).stdout)
```

이후 복구는 이 파일로만 한다.

```python
!pip install -r "/content/drive/MyDrive/<project>/requirements.txt" -q
```

### 2. 복구를 5셀로 고정한다 — 런타임 재시작 없이

순서가 중요하다. clone을 먼저 하고 설치를 나중에 하면 설치가 clone 안의 패키지를 덮을 수 있다.

**셀 1 — 영구 저장소 마운트**

```python
from google.colab import drive
drive.mount('/content/drive', force_remount=False)
```

**셀 2 — 저장소 clone (저장소 자체 requirements는 설치하지 않는다)**

```python
!git clone -q https://github.com/<owner>/<project>.git /content/project
!git clone -q https://github.com/YatingMusic/MusiConGen.git /content/MusiConGen
```

**셀 3 — 검증된 조합 설치**

```python
!pip install -r "/content/drive/MyDrive/<project>/requirements.txt" -q
```

**셀 4 — audiocraft 경로 확정**

추측하지 않고 찾는다. 후보가 여러 개면 어느 것을 쓸지 명시적으로 고른다.

```python
import glob, os
cands = sorted(set(os.path.dirname(p) for p in
                   glob.glob("/content/**/audiocraft/__init__.py", recursive=True)))
for c in cands:
    print("candidate:", c)

AUDIOCRAFT_ROOT = "/content/MusiConGen/audiocraft"
assert os.path.isfile(os.path.join(AUDIOCRAFT_ROOT, "audiocraft", "__init__.py")) \
    or os.path.isfile(os.path.join(AUDIOCRAFT_ROOT, "__init__.py")), \
    f"audiocraft 패키지를 {AUDIOCRAFT_ROOT} 에서 찾지 못했다"
print("selected:", AUDIOCRAFT_ROOT)
```

**셀 5 — 모듈 캐시를 비우고 import, 그 다음 체크포인트**

이 셀이 핵심이다. `sys.modules`에서 audiocraft 관련 항목을 전부 지운 뒤 `sys.path`를 앞쪽에 삽입한다. **그래야 재시작 없이 올바른 쪽이 잡힌다.**

```python
import sys
from huggingface_hub import hf_hub_download

for name in [m for m in list(sys.modules) if m == "audiocraft" or m.startswith("audiocraft.")]:
    del sys.modules[name]

sys.path.insert(0, AUDIOCRAFT_ROOT)

import audiocraft
assert audiocraft.__file__ is not None, \
    "네임스페이스 패키지가 잡혔다. sys.path 순서와 중복 경로를 다시 확인한다"
print("audiocraft:", audiocraft.__file__)

ckpt_dir = None
for fn in ["compression_state_dict.bin", "state_dict.bin"]:
    p = hf_hub_download(repo_id="Cyan0731/MusiConGen", filename=fn)
    ckpt_dir = ckpt_dir or os.path.dirname(p)
    print("downloaded:", fn, os.path.getsize(p), "B")

from audiocraft.models import MusicGen
model = MusicGen.get_pretrained(ckpt_dir)
print("loaded. sample_rate =", model.sample_rate, "frame_rate =", model.frame_rate)
```

### 3. `assert`로 조용한 실패를 막는다

위 두 개의 `assert`가 이 복구 경로의 핵심이다. 둘 다 **에러 없이 잘못된 상태로 진행되는 지점**을 막는다. `audiocraft.__file__ is None`이면 import는 성공했지만 내용이 비어 있고, 그 상태로 진행하면 한참 뒤에 엉뚱한 `AttributeError`가 난다.

### 4. 산출물은 영구 저장소에 즉시 쓴다

복구 비용을 줄이는 것과 별개로, 생성·측정 결과는 런타임이 끊기면 사라진다. 생성 직후 영구 저장소로 복사하고 해시로 검증한다. 체크포인트와 저장소 clone은 다시 받으면 되므로 백업 대상이 아니다. **재생성 비용이 낮고 결정적인 것은 백업하지 않고, 재생성이 불가능하거나 비결정적인 것만 백업한다.**

## 주의사항

`sys.path.insert(0, ...)`는 전역 상태를 바꾼다. 같은 세션에서 다른 버전의 같은 패키지를 쓰려면 충돌한다. 노트북 하나가 한 환경을 쓰는 구조에서는 문제가 없지만, 라이브러리 코드에 이 패턴을 넣지는 않는다.

`sys.modules` 삭제도 전역이다. 이미 그 모듈의 객체를 들고 있는 코드가 있으면 그 객체는 옛 모듈을 가리킨 채 남는다. 복구 셀처럼 **import 전에 한 번** 쓰는 용도로만 쓴다.

## 배운 점 / Development Way

**재현 환경은 저자의 핀이 아니라 내 런타임에서 성공한 조합이다.** 저장소의 `requirements.txt`는 저자 환경의 기록이고, 다른 런타임에서는 출발점일 뿐 정답이 아니다. 한 번 성공하면 그 순간의 `pip freeze`를 떠서 커밋하고, 그 파일을 복구의 유일한 입력으로 삼는다. 이 전환 하나가 복구를 반복 가능한 절차로 만들었다.

**복구 절차 자체를 작업 대상으로 본다.** 실험이 멈춘 원인이 의욕이나 난이도가 아니라 복구 비용이었다. 매번 긴 시간이 드는 준비 단계가 있으면 그 단계가 작업 재개의 문턱이 되고, 문턱이 높으면 재개하지 않는다. 준비 비용을 측정해서 눈에 보이게 하고, 그 비용을 줄이는 일을 실험과 같은 우선순위로 다룬다.

**런타임 재시작으로 해결하려는 충동을 의심한다.** 재시작은 상태를 지워 문제를 가리지만, 설치 상태도 함께 지우는 환경에서는 비용이 크다. 재시작이 필요해 보이면 먼저 "무엇이 캐시되어 문제를 만드는가"를 특정한다. 파이썬의 import 문제는 대부분 `sys.modules`와 `sys.path`이고, 둘 다 세션 안에서 고칠 수 있다.

**조용히 성공하는 실패 지점에 `assert`를 심는다.** `import`가 성공하는 것과 그 모듈이 쓸 수 있는 상태인 것은 다르다. 이렇게 성공과 실패의 경계가 흐린 지점은 절차마다 몇 개씩 있고, 거기에 단정문을 하나 두면 실패가 **발생 지점에서** 드러난다. 한참 뒤의 엉뚱한 에러를 거꾸로 추적하는 비용이 사라진다.

**백업 대상은 재생성 비용으로 결정한다.** 크기가 아니라 비용이다. 수 GB짜리 체크포인트는 명령 한 줄로 다시 받을 수 있으므로 백업하지 않고, 수백 KB짜리 측정 기록은 다시 만들 수 없으므로 백업한다. 여기에 환경 스냅샷을 함께 넣어 두면, 복원 후 같은 측정을 다시 돌려 값이 일치하는지 보는 것으로 **환경 복원 자체를 검증**할 수 있다.
