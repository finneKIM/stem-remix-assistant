# BTC-ISMIR2019 실행 시 yaml.load() Loader 인자 누락 에러

## 상황

madmom을 대체할 코드 인식(chord recognition) 도구로 [BTC-ISMIR2019](https://github.com/jayg996/BTC-ISMIR19)(Bi-Directional Transformer 기반 코드 인식 모델)를 사용하던 중, config 로드 단계에서 에러가 발생했다.

## 에러

```
Traceback (most recent call last):
  File "test.py", line 22, in <module>
    config = HParams.load("run_config.yaml")
  File "utils/hparams.py", line 29, in load
    return cls(**yaml.load(f))
                 ~~~~~~~~~^^^
TypeError: load() missing 1 required positional argument: 'Loader'
```

## 원인

PyYAML은 버전 5.1부터 임의 코드 실행을 방지하기 위한 보안 조치로, `yaml.load()` 호출 시 `Loader` 인자를 명시하도록 요구한다(인자를 생략하면 경고, 이후 버전에서는 필수 인자로 강제). BTC-ISMIR2019는 2019년에 작성된 코드로, PyYAML 구버전(Loader 인자 생략 가능) 기준으로 작성되어 있었다. 실행 환경에는 최신 PyYAML(6.x)이 설치되어 있어 이 문제가 즉시 드러났다.

## 해결

문제가 되는 파일(`utils/hparams.py`)의 `yaml.load(f)` 호출에 `Loader=yaml.FullLoader`를 명시적으로 추가한다.

```python
import os

hparams_path = os.path.join(BTC_DIR, "utils", "hparams.py")

with open(hparams_path) as f:
    content = f.read()

target = "yaml.load(f)"
if target in content:
    new_content = content.replace(
        "yaml.load(f)",
        "yaml.load(f, Loader=yaml.FullLoader)"
    )
    with open(hparams_path, "w") as f:
        f.write(new_content)
```

패치 후 정상적으로 config가 로드되었다.

## 참고

이 문제는 라이브러리가 "문법을 지원 중단"한 것이 아니라 "기본 동작을 더 안전한 방식으로 바꾼" 경우다. 즉 코드 자체가 완전히 못 쓰게 된 것이 아니라, 명시적으로 옵션 하나만 지정해주면 정상 동작한다. 오래된 오픈소스 저장소를 최신 환경에서 실행할 때 흔히 마주치는 유형의 문제이며, 에러 메시지가 요구하는 인자를 그대로 채워주는 것으로 해결되는 경우가 많다.

## 배운 점 / Development Way

에러 메시지에 `missing 1 required positional argument`처럼 "무엇이 빠졌는지"가 명확히 나와 있는 경우는, 그 자리에서 바로 원인을 추정하기보다 먼저 해당 라이브러리의 버전과 변경 이력을 짧게 확인하는 편이 빠르다. 특히 보안 관련 API(직렬화/역직렬화, YAML/pickle 로더 등)는 라이브러리 메이저 업데이트마다 "위험한 기본값"에서 "안전한 기본값"으로 옮겨가는 경향이 있으므로, 오래된 코드가 이런 API를 호출하고 있다면 최신 버전에서 인자 요구사항이 바뀌었는지를 먼저 의심하는 것이 좋다. 이런 유형의 문제는 대개 코드를 재작성할 필요 없이 인자 하나만 채우면 해결되므로, 초기 진단에 드는 시간을 아낄 수 있다.
