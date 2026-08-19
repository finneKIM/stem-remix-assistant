# 2026-08-14 torch import 시 undefined symbol ncclCommResume

## 상황

Colab에서 AudioCraft(MusicGen) 설치를 여러 차례 시도하는 과정에서, torch/torchvision/torchaudio/xformers 버전을 수동으로 맞추는 시도를 반복했다. 이후 audiocraft를 --no-deps로 설치하고 import 테스트를 하는 단계로 넘어갔다.

## 문제

torch import 자체가 실패했다.

```
ImportError: /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so: undefined symbol: ncclCommResume
```

세션(런타임) 재시작 후에도 동일하게 재현되었다.

## 원인

Colab의 세션 재시작은 파이썬 프로세스만 재기동할 뿐, 이미 설치된 패키지는 그대로 유지된다. 이전 단계에서 torch, torchvision, torchaudio, xformers를 여러 번 지웠다 설치하는 과정 중, torch가 필요로 하는 nvidia-nccl-cu12 버전과 실제 설치된 버전이 어긋난 상태로 남았다. 세션 재시작만으로는 이 상태가 복구되지 않는다.

동일한 증상이 PyTorch 공식 GitHub 이슈(#186591)에도 미해결 버그로 보고되어 있었으나, 이번 경우는 그것과 무관하게 자체적으로 유발한 패키지 상태 불일치로 판단된다.

## 해결

torch를 강제로 재설치해 pip가 torch 메타데이터에 명시된 정확한 nvidia-nccl-cu12 버전을 함께 다시 받도록 했다.

```python
!{sys.executable} -m pip install --force-reinstall --no-cache-dir torch
```

재설치 후 세션을 한 번 더 재시작하자 정상 동작했다.

```
torch.__version__: 2.13.0+cu130
torch.cuda.is_available(): True
```

## 배운 점

Colab의 세션 재시작과 런타임 삭제는 다르다. 세션 재시작은 프로세스만 초기화하고 패키지 상태는 유지되므로, 패키지 설치를 반복 시행착오하는 동안 문제가 생겼다면 세션 재시작만으로는 해결되지 않는다.

torch, torchvision, torchaudio, xformers처럼 CUDA 하위 라이브러리(nccl, cublas 등)에 의존하는 패키지는 개별적으로 지웠다 깔았다 하지 말고, 필요하면 한 번에 일관된 조합으로 재설치하는 것이 안전하다.

audiocraft처럼 오래된 고정 버전(requirements.txt)을 요구하는 라이브러리는 --no-deps로 설치하고 실제 필요한 의존성만 개별 설치하는 전략이 최신 Colab 환경에서 더 안정적이다.
