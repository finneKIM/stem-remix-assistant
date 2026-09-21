# 트러블슈팅 로그 — madmom → librosa + BTC-ISMIR2019 전환 과정

오디오 분석 파이프라인의 코드/비트 인식 도구를 [madmom](https://github.com/CPJKU/madmom)에서 [librosa](https://librosa.org/) + [BTC-ISMIR2019](https://github.com/jayg996/BTC-ISMIR19) 조합으로 전환하는 과정에서 겪은 문제들을 정리했다. 순서대로 읽으면 왜 전환을 결정했고, 대체 도구를 검증하는 과정에서 어떤 문제를 만나 어떻게 해결했는지 흐름을 따라갈 수 있다.

## 목록

1. [madmom이 Python 3.13 / numpy 2.x 환경에서 구조적으로 비호환인 문제](./20260921_madmompython313numpyincompatibility.md) — 전환을 결정하게 된 근본 원인
2. [BTC-ISMIR2019 실행 시 yaml.load() Loader 인자 누락 에러](./20260921_btcismir2019yamlloadererror.md)
3. [BTC-ISMIR2019 실행 시 np.float 등 제거된 numpy 별칭 에러](./20260921_btcismir2019npfloatdeprecated.md)
4. [BTC-ISMIR2019 체크포인트 로드 시 torch.load weights_only 에러](./20260921_btcismir2019torchloadweightsonly.md)
5. [Colab에서 apt-get install fluidsynth가 원인 불명으로 실패](./20260921_fluidsynthaptinstallfailure.md)
6. [Colab에서 별도로 전달받은 .py 유틸 모듈을 import하지 못하는 문제](./20260921_colablocalmoduleimporterror.md)

## 핵심 요약

madmom은 오래된 코드베이스(대략 Python 3.6~3.8 / numpy 1.x대 기준)라 최신 환경(Python 3.13 / numpy 2.5.3)에서 문법 자체가 제거된 문제(97건/19개 파일)와 Cython 바이너리 재컴파일 리스크까지 겹쳐, 계속 패치하기보다 대체 도구로 전환하는 것이 더 안전하다고 판단했다.

대체 도구로 선택한 BTC-ISMIR2019는 순수 PyTorch 기반이라 바이너리 호환성 문제가 없었고, 실제로 겪은 문제도 모두 "라이브러리가 문법을 지원 중단한" 근본적 문제가 아니라 "보안 강화를 위해 기본값이 바뀐" 가벼운 API 변경(PyYAML의 Loader 인자 필수화, numpy의 구버전 타입 별칭 제거, PyTorch의 weights_only 기본값 변경)이었다. 세 가지 모두 한두 줄의 패치로 해결되었고, 최종적으로 원곡에서 코드 진행 추출까지 성공했다.

이 경험에서 얻은 일반적인 교훈:

- 정규식을 셸 명령(`grep -E`)과 언어 내장 모듈(Python `re`)에서 함께 쓸 때는 문법 차이(특히 lookahead/lookbehind 지원 여부)를 주의해야 한다. "결과 없음"을 그대로 믿지 않고 재검증하는 습관이 필요하다.
- 원인 불명의 설치 실패는 로그를 캡처만 하지 말고 화면에 그대로 출력해야 원인을 알 수 있다.
- 오래된 오픈소스 코드베이스를 최신 환경에서 실행할 때는, 실제로 "언어/라이브러리가 문법 자체를 지원 중단"한 문제와 "기본 동작만 더 안전하게 바뀐" 문제를 구분하는 것이 중요하다. 후자는 대개 인자 하나만 명시하면 해결된다.
