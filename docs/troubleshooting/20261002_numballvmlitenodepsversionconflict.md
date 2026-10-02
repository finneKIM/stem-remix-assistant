# [2026-10-02] pandas/numba를 `--no-deps`로 묶어 재설치했다가 llvmlite 버전 불일치 재발

## 상황

numpy를 `1.26.4`로 고정(hydra-core/flashy 등 구버전 의존성 호환용)했다가, torch/transformers가 numpy 2.x를 요구해서 다시 최신으로 되돌린 뒤, pandas가 numpy 1.x ABI로 캐시된 채 남아있어 다음 에러가 발생했다.

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

이를 해결하기 위해 pandas와 numba를 한 번에 재설치했다.

```python
!pip install --force-reinstall --no-deps pandas numba
```

## 문제

위 명령 실행 후 `import numba`에서 새로운 에러가 발생했다.

```
ImportError: Numba requires at least version 0.50.0 of llvmlite.
Installed version is 0.44.0.
```

이어서 `--no-deps` 없이 `pip install --upgrade llvmlite numba`로 재설치했더니, pip는 "already satisfied"(llvmlite 0.50.0, numba 0.68.0)로 보고했음에도 `import numba`에서 **똑같은 에러가 다시 발생**했다 (`Installed version is 0.44.0`).

## 원인

두 단계의 원인이 겹쳐 있었다.

1. **`--no-deps`의 적용 범위**: `--no-deps`는 명령에 나열된 모든 패키지(`pandas numba`)에 적용된다. numba는 `llvmlite`라는 필수 의존 C 확장 라이브러리를 요구하는데, `--no-deps`가 그 업그레이드를 막아 numba만 최신으로 올라가고 llvmlite는 구버전(0.44.0)에 머물렀다.
2. **C 확장 모듈의 인메모리 캐시**: `--no-deps` 없이 llvmlite/numba를 다시 올바르게 재설치한 뒤에도 같은 에러가 재발한 이유는, llvmlite가 컴파일된 바이너리(C 확장) 모듈이기 때문이다. 이미 해당 Python 프로세스가 구버전 llvmlite를 메모리에 로드한 상태라면, 디스크 상의 파일을 `pip install --upgrade`로 교체해도 실행 중인 프로세스는 이를 다시 읽지 않는다. `sys.modules`에서 지우는 것도 C 확장에는 효과가 없고, 프로세스(런타임) 자체를 재시작해야 새 버전이 실제로 로드된다.

## 해결

- pandas(`--no-deps`)와 numba(`--upgrade llvmlite numba`, 의존성 포함)를 **별도 셀로 분리**해서 설치한다.

```python
# 셀 A: pandas만 --no-deps로 재설치 (numpy 버전을 다시 끌어내리지 않게)
import numpy
print("numpy:", numpy.__version__)
!pip install --force-reinstall --no-deps pandas
```

```python
# 셀 B: numba/llvmlite는 --no-deps 없이 함께 업그레이드
!pip install --upgrade llvmlite numba
```

- 위 두 셀 실행 직후 Runtime → Restart session을 반드시 실행한다.
- 재시작된 새 프로세스에서 버전을 재확인한다.

```python
import numba, llvmlite
print("numba:", numba.__version__)
print("llvmlite:", llvmlite.__version__)
```

## 배운 점

`--no-deps`는 "문제가 되는 패키지 하나만" 적용되는 옵션이 아니라, 명령에 나열된 모든 패키지에 적용된다. 의존성 체인이 서로 다른 여러 패키지를 한 줄에 묶어서 `--no-deps`로 설치하면, 어느 한쪽의 필수 의존성이 조용히 누락될 수 있다. 또한 pip가 "Requirement already satisfied"라고 보고하는 것은 디스크 상태에 대한 보고일 뿐, 이미 import되어 실행 중인 C 확장 모듈이 그 새 버전을 실제로 쓰고 있다는 보장은 아니다. 컴파일된 바이너리 의존성(C 확장)이 얽힌 패키지를 손볼 때는 설치 직후 import 테스트만으로 검증하지 말고, 항상 런타임을 재시작한 뒤 검증하는 습관이 필요하다.
