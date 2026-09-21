# madmom이 Python 3.13 / numpy 2.x 환경에서 구조적으로 비호환인 문제

## 상황

오디오 분석 파이프라인에서 비트/온셋/다운비트/코드 진행을 추출하기 위해 [madmom](https://github.com/CPJKU/madmom)을 사용하려 했으나, 최신 Colab 기본 환경(Python 3.13, numpy 2.5.3)에서 연쇄적인 호환성 문제가 발생했다.

## 에러 1 — collections.MutableSequence

```
ImportError: cannot import name 'MutableSequence' from 'collections'
```

### 원인

`collections.MutableSequence` 등의 추상 베이스 클래스는 Python 3.3부터 `collections.abc`로 이동이 예고되었고, Python 3.10에서 `collections`에서 완전히 제거되었다. madmom은 이 옛 문법을 그대로 사용하고 있었다.

### 해결

madmom 소스 내 `from collections import MutableSequence` 형태의 import 구문을 정규식으로 찾아 `from collections.abc import MutableSequence`로 일괄 치환.

```python
import subprocess, re, os

result = subprocess.run(["pip", "show", "-f", "madmom"], capture_output=True, text=True)
location = next(l.split("Location:")[1].strip() for l in result.stdout.splitlines() if l.startswith("Location:"))
madmom_dir = os.path.join(location, "madmom")

search = subprocess.run(
    ["grep", "-rln", "-E",
     r"from collections import (MutableSequence|MutableMapping|MutableSet|Sequence|Mapping|Set|Iterable|Callable)",
     madmom_dir],
    capture_output=True, text=True
)
problem_files = search.stdout.strip().splitlines()

pattern = re.compile(
    r"from collections import (MutableSequence|MutableMapping|MutableSet|Sequence|Mapping|Set|Iterable|Callable)"
)
for f in problem_files:
    with open(f, "r") as fh:
        content = fh.read()
    new_content = pattern.sub(r"from collections.abc import \1", content)
    if new_content != content:
        with open(f, "w") as fh:
            fh.write(new_content)
```

패치 대상은 1개 파일이었고 정상 해결되었다.

## 에러 2 — np.float 등 numpy에서 제거된 별칭

패치 후 재검증하자 새로운 에러가 발생했다.

```
AttributeError: module 'numpy' has no attribute 'float'.
`np.float` was a deprecated alias for the builtin `float`.
```

### 원인

`np.float`, `np.int`, `np.bool` 등은 numpy 1.20부터 deprecated 경고가 나오다가 numpy 1.24에서 완전히 제거되었다. madmom 소스 곳곳에 이 옛 별칭이 남아 있었다.

### 규모 확인 — 잘못된 첫 스캔과 재스캔

처음에 `grep -rnE`로 전체 규모를 스캔했을 때 0건이 나왔다.

```python
pattern = alias.replace(".", r"\.") + r"(?![a-zA-Z0-9_])"
result = subprocess.run(
    ["grep", "-rnE", pattern, madmom_dir, "--include=*.py"],
    capture_output=True, text=True
)
```

하지만 이 결과는 잘못된 것이었다. **원인은 `grep -E`(POSIX 확장 정규식)가 lookahead `(?!...)`를 지원하지 않기 때문**이다. Python의 `re` 모듈 문법을 그대로 셸 `grep`에 넘기면 lookahead 부분이 조용히 무시되거나 매치 자체가 실패한다.

Python `re` 모듈로 직접 재스캔하자 실제 규모가 드러났다.

```python
import os, re

deprecated_pattern = re.compile(r"\bnp\.(float|int|bool|object|str|complex|long)\b(?!\w)")

np_hits = []
for root, dirs, files in os.walk(madmom_dir):
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                if deprecated_pattern.search(line):
                    np_hits.append((fpath, lineno, line.strip()))

print(f"np.float류 문제: {len(np_hits)}건 / {len(set(h[0] for h in np_hits))}개 파일")
# 결과: np.float류 문제: 97건 / 19개 파일
```

**교훈**: 정규식을 셸 명령(grep -E)과 언어 내장 모듈(Python re) 양쪽에서 쓸 때는 문법이 다르다는 것을 반드시 확인해야 한다. lookahead/lookbehind, 문자 클래스 표기 등은 도구마다 지원 여부가 다르다. "0건"이라는 결과 자체를 의심하지 않으면 실제로는 존재하는 문제를 놓친 채 다음 단계로 넘어가게 된다.

### 최종 판단

97건/19개 파일이라는 규모, 그리고 madmom 일부 모듈이 Cython으로 컴파일된 바이너리 확장을 포함하고 있어 최신 환경에서 재컴파일 실패 위험까지 겹쳐, 이 라이브러리를 최신 Python/numpy 환경에 맞춰 계속 패치하는 것은 비용 대비 리스크가 크다고 판단했다. 대체 라이브러리로 전환하는 결정으로 이어졌다(별도 문서 참고).

## 요약

| 항목 | 내용 |
|---|---|
| 환경 | Python 3.13, numpy 2.5.3 |
| 근본 원인 | madmom이 Python 3.6~3.8 / numpy 1.x대 기준으로 작성된 오래된 라이브러리 |
| 발견된 문제 | collections 추상클래스 제거(1건), numpy 제거된 별칭(97건/19파일) |
| 부수적으로 발견한 문제 | grep -E와 Python re의 정규식 문법 차이로 인한 스캔 오탐 |
| 최종 결정 | 계속 패치하지 않고 대체 라이브러리 조합으로 전환 |

## 배운 점 / Development Way

오래된 오픈소스 라이브러리를 최신 환경에 맞춰 패치할지 결정할 때는, 먼저 "문제의 성격"부터 나눠 보는 것이 순서다. 이름이 바뀌었거나 인자가 하나 추가된 수준의 문제는 정규식 치환으로 빠르게 해결되지만, 컴파일된 바이너리 확장(Cython/C 확장)에 걸친 문제는 텍스트 치환으로 손댈 수 없고 재컴파일이라는 훨씬 큰 불확실성을 동반한다. 패치를 시작하기 전에 그 라이브러리가 순수 언어로만 되어 있는지, 아니면 바이너리 확장을 포함하는지부터 확인하면 "계속 팔지 말지"를 초반에 판단할 수 있다.

또한 스캔 결과가 예상과 다르게(특히 유난히 낙관적으로) 나올 때는 스캔 도구 자체를 의심하는 습관이 필요하다. 셸 명령과 프로그래밍 언어의 정규식 엔진은 겉보기엔 비슷해 보여도 지원하는 문법이 다르므로, 중요한 의사결정(패치 규모 판단, 전환 여부 결정)의 근거로 삼는 스캔은 가능하면 실제로 그 언어의 표준 라이브러리로 재검증하는 것이 안전하다.
