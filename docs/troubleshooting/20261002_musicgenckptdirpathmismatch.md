# [2026-10-02] MusicGen 체크포인트 로드 시 HFValidationError — ckpt_dir 상대경로/절대경로 불일치

## 상황

numpy/pandas/numba 문제를 모두 해결한 뒤, 다운로드해 둔 체크포인트로 모델을 로드했다.

```python
from transformers import EncodecModel as HFEncodecModel, RobertaTokenizer, T5EncoderModel, T5Tokenizer
print("transformers 관련 클래스 import 성공")

from audiocraft.models import MusicGen
ckpt_dir = "/content/musicongen_checkpoints"
model = MusicGen.get_pretrained(ckpt_dir)
print("모델 로드 완료")
```

## 문제

```
HFValidationError: Repo id must be in the form 'repo_name' or 'namespace/repo_name':
'/content/musicongen_checkpoints'. Use `repo_type` argument if needed.
```

`ckpt_dir`에 로컬 디렉토리 경로를 줬는데도 HuggingFace repo id로 취급되어 검증에 실패했다.

## 원인

`audiocraft/models/loaders.py`의 `_get_state_dict` 함수는 다음 순서로 분기한다.

```python
if os.path.isfile(file_or_url_or_id):
    return torch.load(file_or_url_or_id, map_location=device)
if os.path.isdir(file_or_url_or_id):
    file = f"{file_or_url_or_id}/{filename}"
    return torch.load(file, map_location=device)
elif file_or_url_or_id.startswith('https://'):
    ...
else:
    # 로컬 파일도 URL도 아니면 HuggingFace repo id로 간주
    file = hf_hub_download(repo_id=file_or_url_or_id, filename=filename, cache_dir=cache_dir)
```

`os.path.isdir(ckpt_dir)`이 `False`가 되면 마지막 else 분기로 빠져 repo id로 오인된다. 체크포인트를 다운로드한 셀은 다음과 같이 **상대경로**를 사용했다.

```python
ckpt_dir = os.path.abspath("./musicongen_checkpoints")
```

이 셀이 실행된 시점의 작업 디렉토리는 앞선 `%cd MusiConGen` 때문에 `/content/MusiConGen`이었고, 따라서 실제 체크포인트는 `/content/MusiConGen/musicongen_checkpoints`에 저장됐다. 반면 로드 셀에는 `/content/musicongen_checkpoints`(`MusiConGen` 없이)로 하드코딩돼 있어 두 경로가 어긋났다. `find`로 실제 위치를 확인해 교차검증했다.

```python
import subprocess
result = subprocess.run(["find", "/content", "-iname", "state_dict.bin"], capture_output=True, text=True)
print(result.stdout)
# /content/MusiConGen/musicongen_checkpoints/state_dict.bin
```

## 해결

실제 저장 위치를 `find`로 확인한 뒤 `ckpt_dir`을 정확한 절대경로로 수정했다.

```python
ckpt_dir = "/content/MusiConGen/musicongen_checkpoints"
model = MusicGen.get_pretrained(ckpt_dir)
print("모델 로드 완료")
```

재실행 결과 `os.path.isdir(ckpt_dir)`이 `True`가 되어 로컬 파일에서 바로 로드에 성공했다.

## 배운 점

체크포인트/산출물 저장 경로는 상대경로(`./musicongen_checkpoints` 등)로 만들지 말고 처음부터 작업 디렉토리에 의존하지 않는 절대경로로 고정해야 한다. 특히 노트북 안에서 `%cd`로 작업 디렉토리를 바꾸는 지점이 하나라도 있으면, 그 이후 만들어지는 상대경로 기반 변수는 셀 실행 순서/타이밍에 따라 다른 값으로 해석될 수 있다. 다운로드 셀과 로드 셀이 같은 경로 변수를 공유하도록 설계하거나(예: 전역 상수로 한 번만 정의), 최소한 로드 전에 `os.path.isdir()`로 경로 존재를 검증하는 방어 코드를 넣어두면 이런 종류의 조용한 실패를 조기에 잡을 수 있다.
