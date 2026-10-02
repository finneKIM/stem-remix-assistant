# [2026-10-02] Colab 재연결 복구 시 이미 폐기된 conda(stemremix) 분기를 실행해서 발생한 에러

## 상황

GPU/런타임 연결이 끊긴 뒤 `02a_regenerate_musicongen.ipynb`를 복구 실행하던 중, "1. 저장소 클론 + MusiConGen 설치" 섹션 안의 pandas 설치 셀을 실행했다.

```python
# pandas 의존성 확인 -> requirements_filterd.txt 기존에는 없음
!head -50 /content/MusiConGen/audiocraft/audiocraft/data/chords.py
```

```python
# pandas latest ver. installation
!/content/miniconda3/envs/stemremix/bin/python -m pip install pandas
```

## 문제

`/content/miniconda3/envs/stemremix/bin/python`이라는 경로를 직접 호출하는 셀인데, 이번 복구 세션에서는 miniconda 자체를 설치하지 않았기 때문에 해당 경로가 존재하지 않아 설치가 실패한다. 이전에도 비슷한 재발이 있었는데, 그때는 "저장소 연결 끊겼을 때"(노트북 내 특정 섹션)만 건너뛰면 된다고 판단했지만 여전히 이 단계에서 에러가 재발했다.

## 원인

GitHub에 올라간 노트북 원본(166개 셀)을 처음부터 끝까지 직접 재검토한 결과, 문제는 특정 섹션 하나가 아니라 **"1. 저장소 클론 + MusiConGen 설치" 섹션 전체(셀 19~81에 해당하는 범위)가 통째로 쓰이지 않는 죽은 분기**였다.

- 이 구간은 `/content/miniconda3`에 `stemremix`라는 별도 conda 환경을 만들고, `subprocess.run(['/content/miniconda3/envs/stemremix/bin/python', ...])` 혹은 `!/content/miniconda3/envs/stemremix/bin/python -m pip install ...` 방식으로 그 환경에 직접 설치/검증하는 구조다.
- 이 conda 환경을 Colab의 Jupyter 커널로 등록해서 전환하려는 시도도 있었는데, 해당 셀 자신의 주석에 "colab에서 kernelspec과 무관하게 연결 안됨"이라고 명시돼 있어, 원래 세션에서도 이미 실패로 결론 난 접근이었다.
- 결정적으로, 뒤에 나오는 "2. 체크포인트 다운로드" 섹션은 이 conda 환경을 전혀 참조하지 않는다. 체크포인트 다운로드/의존성 설치/numpy 조정 등은 전부 `!pip install`이나 `subprocess.run([sys.executable, ...])`로 **base Colab 파이썬에 직접** 수행된다.
- `requirements_filtered.txt` 역시 생성 이후 특정 구간에서만 쓰이고 그 뒤로는 어디서도 다시 참조되지 않는, 버려진 산출물이었다.

즉 실제로 작동하는 유일한 경로는 "저장소 클론(+ 기본 pip install)" → "체크포인트 다운로드 섹션에서 base 파이썬에 직접 의존성 설치"였고, 그 사이에 있던 conda 환경 구축 전체는 처음부터 끝까지 사용되지 않았다.

## 해결

재연결 복구 시 저장소 클론 셀까지만 실행하고, 그 뒤 conda 환경 구축 구간 전체를 건너뛴 뒤 바로 체크포인트 다운로드 섹션으로 진입하도록 복구 절차를 수정했다. 순서는 다음과 같다.

1. GPU 확인
2. 저장소 클론 (`stem-remix-assistant`, `MusiConGen`) + 기본 `pip install -r requirements.txt` + ffmpeg
3. (conda 환경 구축 섹션 전체 스킵)
4. 체크포인트 다운로드 섹션 진입 → 의존성을 base 파이썬에 직접 설치

## 배운 점

노트북 안의 섹션 제목("저장소 연결 끊겼을 때" 등)만 보고 "복구용이니 당연히 실행해야 한다"고 판단하면 틀릴 수 있다. 어떤 셀이 실제로 뒤에서 참조/사용되는지는 섹션 제목이 아니라 전체 소스를 직접 훑어서 데이터 흐름(변수, 경로, import 방식)을 추적해야 확정할 수 있다. 특히 과거에 여러 번 접근을 바꿔가며 디버깅한 "작업 일지형" 노트북에서는, 한 번 시도했다가 포기한 분기가 그대로 남아있는 경우가 흔하므로 재연결 복구 가이드 자체도 섹션 제목이 아니라 실제 셀 번호 기준으로 고정해둘 필요가 있다.
