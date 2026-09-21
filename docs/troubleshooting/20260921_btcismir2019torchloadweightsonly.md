# BTC-ISMIR2019 체크포인트 로드 시 torch.load weights_only 에러

## 상황

[BTC-ISMIR2019](https://github.com/jayg996/BTC-ISMIR19)의 yaml 로더 문제와 numpy 별칭 문제를 모두 해결한 후 다시 실행하자, 사전학습 체크포인트를 불러오는 단계에서 세 번째 에러가 발생했다.

## 에러

```
Traceback (most recent call last):
  File "test.py", line 39, in <module>
    checkpoint = torch.load(model_file)
  File ".../torch/serialization.py", line 1602, in load
    raise pickle.UnpicklingError(_get_wo_message(str(e))) from None
_pickle.UnpicklingError: Weights only load failed. This file can still be loaded, to do so you have two options, do those steps only if you trust the source of the checkpoint.
	(1) In PyTorch 2.6, we changed the default value of the `weights_only` argument in `torch.load` from `False` to `True`. Re-running `torch.load` with `weights_only` set to `False` will likely succeed, but it can result in arbitrary code execution. Do it only if you got the file from a trusted source.
	(2) Alternatively, to load with `weights_only=True` please check the recommended steps in the following error message.
	WeightsUnpickler error: Unsupported global: GLOBAL numpy.core.multiarray.scalar was not an allowed global by default. Please use `torch.serialization.add_safe_globals([numpy.core.multiarray.scalar])` or the `torch.serialization.safe_globals([numpy.core.multiarray.scalar])` context manager to allowlist this global if you trust this class/function.
```

## 원인

PyTorch 2.6부터 `torch.load()`의 기본값이 `weights_only=False`에서 `weights_only=True`로 변경되었다. 이는 pickle 파일에 임의 코드가 포함되어 악용될 수 있는 보안 취약점을 막기 위한 조치다. `weights_only=True`는 안전하다고 알려진 타입들만 역직렬화를 허용하는데, 2019년에 저장된 체크포인트 파일은 당시 numpy 버전의 내부 객체(`numpy.core.multiarray.scalar`)를 포함하고 있어 기본 안전 목록에 없어 차단되었다.

## 해결

체크포인트가 신뢰할 수 있는 공식 출처(원본 프로젝트 저장소)에서 받은 것이 확실하다면, `weights_only=False`를 명시적으로 지정해 우회할 수 있다.

```python
import os, re

test_py = os.path.join(BTC_DIR, "test.py")

with open(test_py) as f:
    content = f.read()

pattern = re.compile(r"torch\.load\(([^)]*)\)")

def add_weights_only(match):
    args = match.group(1)
    if "weights_only" in args:
        return match.group(0)
    return f"torch.load({args}, weights_only=False)"

new_content = pattern.sub(add_weights_only, content)

if new_content != content:
    with open(test_py, "w") as f:
        f.write(new_content)
```

패치 후 체크포인트 로드 및 추론이 정상적으로 완료되었다.

## 주의사항

`weights_only=False`는 pickle 역직렬화 과정에서 임의 코드가 실행될 수 있는 옵션이다. **출처가 불분명하거나 신뢰할 수 없는 체크포인트 파일에는 절대 사용해서는 안 된다.** 공식 저장소에서 직접 받은 파일처럼 출처가 명확한 경우에만 이 방법을 적용하는 것이 안전하다. 더 안전한 대안으로는 에러 메시지가 안내하는 대로 `torch.serialization.add_safe_globals([numpy.core.multiarray.scalar])`로 특정 타입만 허용 목록에 추가하는 방법도 있다.

## 요약

| 항목 | 내용 |
|---|---|
| 원인 | PyTorch 2.6부터 torch.load()의 weights_only 기본값이 True로 변경(보안 강화) |
| 트리거 | 2019년에 저장된 체크포인트가 구버전 numpy 객체를 포함해 기본 안전 목록에 없음 |
| 해결 | 신뢰 가능한 출처일 때 한해 weights_only=False 명시 |
| 대안 | torch.serialization.add_safe_globals()로 필요한 타입만 개별 허용 |

## 배운 점 / Development Way

보안 강화를 위해 기본값이 바뀐 API를 오래된 코드에서 만났을 때는, 우회 방법(여기서는 `weights_only=False`)을 적용하기 전에 그 우회가 실제로 안전한 상황인지부터 판단하는 순서를 지키는 것이 중요하다. 판단 기준은 "이 파일을 누가, 어떤 경로로 만들었는가"다. 공식 저장소가 직접 배포한 파일처럼 출처가 명확하면 우회해도 되지만, 출처가 불분명한 파일에는 같은 코드를 그대로 적용해서는 안 된다. 에러 메시지 자체가 이런 트레이드오프를 이미 안내해주는 경우가 많으므로(이번 경우도 두 가지 옵션을 제시했다), 가장 빠른 해결책을 바로 적용하기보다 에러 메시지가 제공하는 대안들을 먼저 비교해보는 습관이 안전한 결정으로 이어진다.

이런 유형의 에러(라이브러리가 보안을 이유로 기본값을 바꾼 경우)는 "고쳐야 할 버그"가 아니라 "확인 후 명시적으로 승인해야 할 신호"로 다루는 것이 적절하다.
