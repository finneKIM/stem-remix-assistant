# "어느 환경에서 실행 중인가"를 먼저 확인하지 않아서 겪은 의존성 두더지잡기

## 상황

이름 충돌 문제를 해결한 뒤 `import audiocraft`를 다시 시도했다. 이 프로젝트에서는 audiocraft/MusicGen이 요구하는 오래된 의존성(`hydra-core==1.1`, `numpy==1.24.4` 등)이 최신 Python과 충돌해서, 별도의 conda 환경을 만들어 그 안에 필요한 패키지를 전부 맞춰둔 상태였다.

## 문제

`import audiocraft`에서 다음 모듈이 없다는 에러가 연쇄적으로 나왔다.

1. `ModuleNotFoundError: No module named 'av'` — 오디오 I/O에 PyAV(FFmpeg 바인딩)가 필요
2. `av` 설치 후 `ModuleNotFoundError: No module named 'julius'` — 오디오 리샘플링 라이브러리 필요

하나 설치하면 다음 모듈이 없다는 에러가 나오는 whack-a-mole 패턴이 반복됐다.

## 원인

먼저 지금 코드가 어느 파이썬 환경에서 실행되고 있는지부터 확인했다.

```python
import sys, os
print(sys.executable)
print(os.environ.get("CONDA_DEFAULT_ENV"))
```

결과, 코드가 실행되고 있던 커널은 따로 준비해둔 conda 환경이 아니라 **기본 Python 커널**이었다. 즉 애써 만들어둔 별도 환경이 있었음에도, 실제 실행은 아무 패키지도 설치되지 않은 다른 환경에서 이뤄지고 있었던 것이다.

여기서 바로 하나씩 pip install로 대응하지 않고, 저장소의 `requirements.txt`를 먼저 확인했다. 그 결과 원본이 요구하는 버전 조합(`hydra-core==1.1`, `numpy==1.24.4`, `flashy==0.0.1`, `xformers==0.0.22`, `torch==2.0.0`)이, 앞서 conda 환경을 구축할 때 이미 한 번 충돌을 겪고 다른 버전으로 교체했던 바로 그 조합과 정확히 일치한다는 걸 확인했다. 즉 원본 requirements.txt를 그대로 설치하면 과거에 해결한 numpy/hydra-core ABI 충돌이 재발할 것이 예상됐다.

## 해결

에러가 날 때마다 패키지를 하나씩 추가하는 대신, 저장소의 requirements 파일 전체를 먼저 확인해 의존성 목록을 파악하고, 원본 버전이 아니라 이전에 이미 검증해둔 버전 조합으로 설치하는 방향으로 정리했다.

```python
!pip install -q --upgrade numpy==1.26.4
!pip install -q --upgrade hydra-core==1.3.2 hydra_colorlog
!pip install -q --upgrade flashy==0.0.2
!pip install -q av julius einops num2words sentencepiece spacy==3.6.1 \
    tqdm demucs librosa soundfile torchmetrics encodec protobuf pesq pystoi transformers==4.31.0
```

torch/torchaudio/xformers는 노트북 환경의 GPU 드라이버와 맞물려 있어서, 기존 설치 버전을 먼저 확인한 뒤 신중하게 결정하는 별도 단계로 분리했다.

## 배운 점

- 새 에러가 날 때마다 그 패키지만 설치하는 방식은 당장은 편하지만, 이미 한 번 해결한 버전 충돌을 다시 만나게 될 위험이 있다. 저장소의 requirements 파일을 먼저 통째로 확인하고, 과거에 검증된 버전과 대조해서 계획을 세우는 편이 훨씬 효율적이었다.
- 코드가 지금 어떤 환경/커널에서 실제로 실행되고 있는지(`sys.executable`, 환경변수)를 먼저 확인하지 않으면, 애써 만들어둔 별도 환경이 있어도 그걸 안 쓰고 있다는 사실 자체를 놓칠 수 있다.
- 동일한 의존성 충돌이 여러 환경(원래 만든 conda 환경, 이번의 기본 커널)에서 반복될 수 있으므로, 한 번 해결한 트러블슈팅 기록에 정확한 버전 번호까지 남겨두면 재발했을 때 처음부터 원인을 다시 찾지 않고 바로 검증된 해법을 적용할 수 있다.
