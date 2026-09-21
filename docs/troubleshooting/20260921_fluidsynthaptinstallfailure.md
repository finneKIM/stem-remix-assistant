# Colab에서 apt-get install fluidsynth가 원인 불명으로 실패

## 상황

MIDI 파일을 실제로 들어볼 수 있는 오디오(WAV)로 변환하기 위해 `fluidsynth`(오픈소스 소프트웨어 신디사이저)를 Colab 환경에 설치하려 했으나, 설치가 실패했다.

## 에러

```python
result = subprocess.run(
    ["apt-get", "install", "-y", "fluidsynth"],
    capture_output=True, text=True
)
print("returncode:", result.returncode)
# 출력: returncode: 100
```

설치가 `returncode: 100`으로 실패했지만, `capture_output=True`로 로그를 캡처만 하고 화면에 출력하지 않아 정확한 실패 사유를 바로 알 수 없었다. 이후 변환 코드를 실행하자 다음 에러로 이어졌다.

```
FileNotFoundError: [Errno 2] No such file or directory: 'fluidsynth'
```

## 원인

`apt-get install`을 실행하기 전에 `apt-get update`(패키지 인덱스 최신화)를 먼저 실행하지 않았다. Colab 기본 이미지의 apt 패키지 인덱스가 오래되어 있으면, `apt-get install`이 대상 패키지의 최신 메타데이터를 찾지 못하고 실패할 수 있다.

## 해결

1. `apt-get install` 전에 `apt-get update`를 먼저 실행해 패키지 인덱스를 최신화한다.
2. 설치 로그(STDOUT/STDERR)를 캡처만 하지 말고 그대로 화면에 출력해서, 실패 시 원인을 즉시 확인할 수 있게 한다.
3. `which fluidsynth`로 실행 파일이 실제로 설치되었는지 확인한 후 다음 단계로 진행한다.

```python
import subprocess

print("=== apt-get update ===")
result = subprocess.run(["apt-get", "update"], capture_output=True, text=True)
print("returncode:", result.returncode)
print(result.stdout[-1500:])
print(result.stderr[-1500:])

print("=== fluidsynth 설치 ===")
result = subprocess.run(
    ["apt-get", "install", "-y", "fluidsynth"],
    capture_output=True, text=True
)
print("returncode:", result.returncode)
print("STDOUT:\n", result.stdout[-2000:])
print("STDERR:\n", result.stderr[-2000:])

which_result = subprocess.run(["which", "fluidsynth"], capture_output=True, text=True)
print("which fluidsynth ->", which_result.stdout.strip() or "(없음)")
```

`apt-get update`를 먼저 실행한 뒤 재시도하자 `returncode: 0`으로 정상 설치되었고, `which fluidsynth`로 실행 파일 경로(`/usr/bin/fluidsynth`)가 확인되었다. 이후 MIDI → WAV 변환도 정상적으로 완료되었다.

## 교훈

apt 패키지 설치가 원인 불명으로 실패하면 다음 두 가지부터 점검한다.

1. `apt-get update`를 먼저 실행했는가 — Colab처럼 이미지가 미리 빌드되어 있고 세션마다 새로 시작되는 환경에서는 패키지 인덱스가 오래되어 있을 가능성이 높다.
2. 설치 로그를 실제로 화면에 출력하고 있는가 — `capture_output=True`로 로그를 캡처만 해두고 화면에 출력하지 않으면, 실패해도 원인을 파악할 단서 자체가 없어진다. 디버깅이 필요한 명령은 항상 로그를 그대로 출력하도록 작성하는 것이 좋다.

## 요약

| 항목 | 내용 |
|---|---|
| 증상 | apt-get install이 returncode 100으로 실패, 이후 FileNotFoundError |
| 원인 | apt-get update 없이 바로 install을 시도해 패키지 인덱스가 오래된 상태였음 |
| 해결 | apt-get update 선행 + 로그를 화면에 그대로 출력해 원인 확인 |
| 교훈 | 원인 불명의 실패는 로그를 가두지 말고 노출시키는 것이 우선 |

## 배운 점 / Development Way

세션마다 초기화되는 클라우드 노트북 환경(Colab 등)에서는 시스템 패키지 설치가 "항상 최신 인덱스에서 시작한다"고 가정해서는 안 된다. 새 세션을 시작할 때 시스템 패키지를 설치하는 코드에는 `apt-get update`를 습관적으로 앞에 붙이는 것이, 나중에 원인 불명의 설치 실패를 마주하고 되짚어가는 것보다 비용이 훨씬 적다.

더 일반적으로는, 자동화 스크립트에서 외부 명령을 실행할 때 `capture_output=True`(또는 이에 준하는 로그 억제 옵션)를 기본값처럼 습관적으로 쓰는 것을 경계해야 한다. 로그를 캡처하는 것 자체는 나쁘지 않지만, 실패했을 때 그 로그를 확인하는 절차까지 함께 만들어두지 않으면 "실패했다"는 사실만 알고 "왜 실패했는지"는 영영 알 수 없게 된다. 디버깅 단계에서는 로그를 억제하지 않고 그대로 노출하는 것을 기본값으로 삼는 편이 안전하다.
