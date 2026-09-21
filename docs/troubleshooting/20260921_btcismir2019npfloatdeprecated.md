# BTC-ISMIR2019 실행 시 np.float 등 제거된 numpy 별칭 에러

## 상황

[BTC-ISMIR2019](https://github.com/jayg996/BTC-ISMIR19)의 yaml 로더 문제([문서 02](./02-btc-ismir2019-yaml-loader-error.md) 참고)를 해결한 후 재실행하자, 이번에는 numpy 관련 에러가 발생했다.

## 에러

```
Traceback (most recent call last):
  File "test.py", line 35, in <module>
    model = BTC_model(config=config.model).to(device)
  File "btc_model.py", line 158, in __init__
    self.self_attn_layers = bi_directional_self_attention_layers(*params)
  File "btc_model.py", line 106, in __init__
    self.timing_signal = _gen_timing_signal(max_length, hidden_size)
  File "utils/transformer_modules.py", line 30, in _gen_timing_signal
    np.arange(num_timescales).astype(np.float) * -log_timescale_increment)
AttributeError: module 'numpy' has no attribute 'float'.
`np.float` was a deprecated alias for the builtin `float`. To avoid this error in existing code, use `float` by itself.
```

## 원인

`np.float`, `np.int`, `np.bool` 등의 별칭은 numpy 1.20부터 사용 중단(deprecated) 경고가 발생하다가, numpy 1.24에서 완전히 제거되었다. 2019년에 작성된 코드베이스는 이 별칭들을 그대로 사용하고 있어, 최신 numpy 환경에서 즉시 에러가 발생했다.

## 규모 확인

전체 소스에서 Python `re` 모듈로 직접 스캔하여 영향 범위를 먼저 파악했다(참고: 셸 `grep -E`는 lookahead 정규식을 지원하지 않아 오탐이 발생할 수 있으므로 사용하지 않았다).

```python
import os, re

pattern = re.compile(r"\bnp\.(float|int|bool|object|str|complex|long)\b(?!\w)")

hits = []
for root, dirs, files in os.walk(BTC_DIR):
    dirs[:] = [d for d in dirs if d != ".git"]
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                if pattern.search(line):
                    hits.append((fpath, lineno, line.strip()))

print(f"np.float류 문제: {len(hits)}건 / {len(set(h[0] for h in hits))}개 파일")
```

결과: **12건 / 3개 파일**(`audio_dataset.py`, `utils/chords.py`, `utils/transformer_modules.py`). 같은 유형의 문제를 겪었던 다른 오래된 오디오 처리 라이브러리(수십 건~100건 규모)에 비해 훨씬 작은 규모였다. 이 코드베이스가 순수 Python/PyTorch로만 작성되어 있어 문제 범위가 국소적이었기 때문으로 보인다.

## 해결

정규식으로 일괄 치환한다. numpy 공식 안내에 따라 `np.float` → `float`, `np.int` → `int`, `np.bool` → `bool` 등 내장 타입으로 대체한다(동작 차이 없음).

```python
import os, re

pattern = re.compile(r"\bnp\.(float|int|bool|object|str|complex|long)\b(?!\w)")

patched_files = []
for root, dirs, files in os.walk(BTC_DIR):
    dirs[:] = [d for d in dirs if d != ".git"]
    for fname in files:
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        new_content = pattern.sub(lambda m: m.group(1), content)
        if new_content != content:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(new_content)
            patched_files.append(fpath)

print(f"총 {len(patched_files)}개 파일 패치 완료")
```

패치 후 재스캔하여 잔여 문제가 0건임을 확인했다.

## 요약

| 항목 | 내용 |
|---|---|
| 원인 | numpy 1.24+에서 완전히 제거된 구버전 타입 별칭(np.float 등) |
| 규모 | 12건 / 3개 파일 |
| 해결 | 정규식 일괄 치환(np.float → float 등) |
| 비고 | Cython/C 확장이 없는 순수 Python 코드베이스라 재컴파일 이슈 없이 텍스트 치환만으로 해결 가능했음 |

## 배운 점 / Development Way

같은 유형의 문제(제거된 numpy 별칭)라도 코드베이스의 성격에 따라 영향 범위가 크게 달라질 수 있다. 순수 Python/PyTorch로만 작성된 프로젝트는 문제가 텍스트 레벨에 국한되어 규모가 작고 해결도 빠른 반면, C/Cython 확장을 포함한 프로젝트는 같은 문제라도 훨씬 크고 복잡하게 나타날 수 있다. 따라서 대체 라이브러리를 고를 때는 기능만 보고 판단하지 않고, 그 구현체가 순수 언어로 되어 있는지 여부를 함께 확인하는 것이 향후 유지보수 비용을 가늠하는 데 유용한 기준이 된다.

또한 "규모를 먼저 스캔해서 파악한 뒤 일괄 치환하고 재스캔으로 검증한다"는 3단계 절차(스캔 → 치환 → 재검증)는 문제의 크기와 무관하게 반복 가능한 접근법이다. 건수가 적다고 스캔을 생략하면 놓치는 인스턴스가 생길 수 있고, 치환 후 재검증을 생략하면 패치가 실제로 완전했는지 확인할 방법이 없다.
