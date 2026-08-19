# 2026-08-14 AudioCraft import 시 연쇄 의존성 문제 해결

## 상황

torch/NCCL 문제(별도 기록: 2026-08-14_nccl-undefined-symbol.md) 해결 후, audiocraft를 --no-deps로 설치하고 `from audiocraft.models import MusicGen` import를 반복 시도했다.

## 문제

에러가 한 번에 다 나오지 않고, 하나를 고치면 다음 지점에서 새 에러가 나는 형태로 총 3단계에 걸쳐 발생했다.

1. torchaudio CUDA 버전 불일치
```
RuntimeError: Detected that PyTorch and TorchAudio were compiled with different CUDA versions.
PyTorch has CUDA version 13.0 whereas TorchAudio has CUDA version 12.8.
```

2. xformers 누락
```
File ".../audiocraft/modules/transformer.py", line 23, in <module>
    from xformers import ops
ModuleNotFoundError: No module named 'xformers'
```

3. numpy와 numba 버전 불일치
```
File ".../numba/__init__.py", line 45, in _ensure_critical_deps
    raise ImportError(msg)
ImportError: Numba needs NumPy 2.0 or less. Got NumPy 2.5.
```

## 원인

1. torch만 단독으로 강제 재설치했더니 torch는 최신(cu130)으로 바뀌었지만 torchaudio는 이전 버전(cu128) 그대로 남아 CUDA 빌드가 어긋났다.
2. audiocraft의 requirements.txt에는 xformers가 명시되어 있었지만, --no-deps로 설치하며 수동 목록에서 누락했다. audiocraft의 transformer 모듈이 xformers를 조건 없이 import하므로 실제로 필수 의존성이었다.
3. xformers 등 여러 패키지를 설치하는 과정에서 numpy가 2.x 최신 버전(2.5.2)까지 자동으로 올라갔는데, librosa가 사용하는 numba가 numpy 2.0 초과 버전을 아직 지원하지 않는다.

## 해결

각 단계마다 실제 에러 메시지에 나온 것만 정확히 대응했다.

```python
# 1. torch, torchvision, torchaudio를 한 번에 재설치해 CUDA 빌드를 통일
!{sys.executable} -m pip install --force-reinstall --no-cache-dir torch torchvision torchaudio

# 2. xformers 설치 (torch 2.10 이상과 호환되는 최신 버전이 자동 선택됨)
!{sys.executable} -m pip install --no-cache-dir xformers

# 3. numba 호환을 위해 numpy를 audiocraft가 원래 요구하던 범위로 낮춤
!{sys.executable} -m pip install --no-cache-dir "numpy==1.26.4"
```

세 단계 모두 사이사이 `from audiocraft.models import MusicGen` import 테스트로 검증하며 진행했다.

## 배운 점

의존성 충돌은 한 번에 전부 드러나지 않고 import가 진행되는 순서대로 하나씩 드러난다. 미리 전부 예측해서 한 번에 고치려 하기보다, 에러 메시지가 가리키는 지점만 정확히 고치고 다시 시도하는 반복이 더 효율적이었다.

pip의 "ERROR: pip's dependency resolver does not currently take into account..." 경고는 실제 설치 실패가 아니라 사후 정보성 메시지인 경우가 많다. 뒤에 "Successfully installed"가 붙어 있으면 설치 자체는 완료된 것이므로, 이 경고만으로 겁먹지 않고 실제 import 테스트로 확인하는 것이 중요하다.

torch 계열 패키지(torch, torchvision, torchaudio)는 항상 세트로 재설치해야 CUDA 빌드 버전이 어긋나지 않는다.
