# 환경 세팅 가이드

GPU가 없는 Windows 환경을 기준으로 한다. 코드 작성은 로컬 VSCode에서, 실제 모델 실행(생성/분리)은 Google Colab에서 진행하는 하이브리드 방식을 사용한다.

## 1. 로컬 (VSCode)

1. 저장소 클론
```
git clone https://github.com/finneKIM/stem-remix-assistant.git
cd stem-remix-assistant
```

2. VSCode로 폴더 열기
```
code .
```

3. 이 저장소에서 로컬로 하는 작업
- `src/` 아래 파이프라인 코드 작성 및 정리
- `notebooks/` 아래 Colab 노트북 편집 (VSCode의 Jupyter 확장으로 셀 단위 미리보기 가능, 단 실행은 GPU가 없어 Colab에서)
- `docs/troubleshooting/` 아래 문제 발생 시 기록
- git add / commit / push로 버전 관리

## 2. Colab (실행)

1. `notebooks/01_setup_and_test.ipynb` 파일을 GitHub에서 연다.
2. 주소창에서 `github.com`을 `colab.research.google.com/github`로 바꾸면 바로 Colab에서 열린다.
   예: `https://colab.research.google.com/github/finneKIM/stem-remix-assistant/blob/main/notebooks/01_setup_and_test.ipynb`
3. 런타임 -> 런타임 유형 변경 -> 하드웨어 가속기를 T4 GPU로 설정
4. 셀을 위에서부터 순서대로 실행
5. 결과물은 Google Drive에 저장되도록 노트북에 설정되어 있어, 세션이 끊겨도 유지된다.

## 3. 노트북 수정 후 다시 저장소에 반영하는 법

Colab에서 코드를 실험하다가 잘 동작하는 버전이 나오면:

1. Colab 상단 메뉴 파일 -> GitHub에 사본 저장 으로 바로 커밋하거나
2. Colab에서 노트북을 다운로드(.ipynb) 받아 로컬 `notebooks/` 폴더에 덮어쓰고 VSCode에서 git commit

## 4. 알려진 제약

- Colab 무료 티어는 연속 사용 시간과 GPU 할당에 제한이 있다. 정확한 시간 수치는 상황에 따라 달라지므로, 작업은 중간 저장을 전제로 진행한다.
- 로컬 Windows 환경에서 AudioCraft를 직접 실행하는 것은 공식 지원 대상이 아니다. 필요시 WSL2를 통한 실행을 별도로 검토할 수 있으나, 이번 프로젝트에서는 Colab을 기본 실행 환경으로 한다.
