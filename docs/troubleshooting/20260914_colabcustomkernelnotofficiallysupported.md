# Colab에서 커스텀 conda 커널로 전환을 시도했다가 되돌린 이야기

## 상황

MusiConGen 기반 파이프라인을 Colab에서 돌리고 있었다. Python 3.13 기본 환경과 MusiConGen의 오래된 의존성(`hydra-core==1.1`, `numpy==1.24.4` 등)이 서로 안 맞아서, 별도로 Python 3.11 miniconda 환경(`stemremix`)을 만들어 그 안에 필요한 패키지를 전부 설치해둔 상태였다.

문제는 그 다음부터였다. Colab 노트북 자체는 기본 Python 커널로 돌아가고 있었기 때문에, `stemremix` 환경의 파이썬을 쓰려면 매번 이렇게 해야 했다.

```python
import subprocess
result = subprocess.run(
    ['/content/miniconda3/envs/stemremix/bin/python', '-c',
     'import audiocraft; ...'],
    capture_output=True, text=True
)
```

한두 줄짜리 검증 코드는 이 방식으로도 괜찮았지만, 모델 로드 → 오디오 생성 → 후처리 → 지표 계산으로 이어지는 긴 파이프라인을 전부 문자열로 감싸서 넘기는 건 비효율적이라, 노트북 커널 자체를 `stemremix` 환경으로 전환하는 방법을 시도했다.

## 시도한 방법

`stemremix` 환경에 `ipykernel`을 설치하고 Jupyter 커널로 등록했다.

```bash
python -m pip install ipykernel
python -m ipykernel install --user --name stemremix --display-name "Python (stemremix)"
```

등록 자체는 성공했고, Colab의 "Change runtime type" 화면에도 실제로 "Python (stemremix)"라는 옵션이 나타났다. 그래서 이를 선택하고 저장했다.

## 문제

저장 후 "connecting" 상태가 비정상적으로 오래(체감상 10분 이상) 지속되며 멈췄다. 결국 브라우저 탭을 새로고침해서 풀었는데, 그 과정에서 Colab 런타임 연결이 끊어졌다(다행히 재연결되었고 디스크의 conda 환경은 그대로 남아있었다).

## 원인

세 곳의 독립된 자료를 대조해서 확인했다.

1. [googlecolab/colabtools#3988](https://github.com/googlecolab/colabtools/issues/3988) — Colab 확장 커널 개발자의 보고에 따르면, Colab은 등록된 kernelspec과 무관하게 자체 IPython 래퍼 커널을 강제로 실행한다.
2. Colab 공식 블로그의 런타임 업데이트 공지 — "Change runtime type"의 공식 기능은 하드웨어 가속기와 런타임 버전 선택뿐이며, 커스텀 Jupyter/conda 커널 지원은 언급되지 않는다.
3. [j3soon/colab-python-version](https://github.com/j3soon/colab-python-version) — Colab에서 커스텀 Python 커널을 쓰는 방법들은 저장소 제목부터 "Unofficial instructions"라고 명시하고 있고, Colab 백엔드가 바뀔 때마다 깨지는 사례가 보고되어 있다.

결론: **Colab의 hosted runtime은 커스텀 conda/Jupyter 커널을 공식적으로 지원하지 않는다.** "Change runtime type" 드롭다운에 옵션이 뜨는 것은 로컬에 kernelspec이 등록되어 있기 때문일 뿐, 실제로 그 환경으로 완전히 전환된다는 보장은 없다.

## 해결

1. 커널 전환은 포기하고, 기존의 `subprocess.run([...])` 방식으로 되돌렸다.
2. 재연결 후 `stemremix` conda 환경이 그대로 남아있는지 확인했다 — 다행히 설치했던 패키지(numpy, xformers, pandas 등)가 전부 유지되어 있어서 처음부터 다시 설치할 필요는 없었다.

```bash
# 환경이 살아있는지 확인
ls /content/miniconda3/envs/stemremix

# 주요 패키지 버전 확인
/content/miniconda3/envs/stemremix/bin/python -c \
  "import numpy, xformers, pandas; print(numpy.__version__, xformers.__version__, pandas.__version__)"
```

## 배운 점

- Colab에서 특정 conda 환경을 반복적으로 써야 한다면, 커널 전환이 아니라 `subprocess.run([환경경로, '-c', ...])` 이나 `%%bash` 매직 명령어 + `conda run -n <env> ...` 방식을 쓰는 것이 안전하다.
- UI에 옵션이 보인다고 해서 그 기능이 공식적으로 지원된다는 뜻은 아니다. 판단이 애매할 때는 개발자 커뮤니티 이슈, 공식 문서, 실제 사용 사례를 여러 곳에서 대조해보는 게 유용했다.
- 런타임이 재연결된 경우(완전히 새 VM으로 교체된 게 아니라면) 디스크에 설치해둔 환경은 그대로 남아있을 수 있다. 문제가 생겼다고 바로 처음부터 재설치하기보다, 먼저 기존 상태부터 확인하는 게 시간을 아낄 수 있다.
