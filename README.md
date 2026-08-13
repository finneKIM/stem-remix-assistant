# Stem Remix Assistant

생성 → 분리 → 재생성 루프로 스템 단위 음악 리믹스를 시도하는 토이 프로젝트.
예산 0원, MusicGen(생성) + Demucs(분리) 조합으로 구현한다.

자세한 배경, 기술적 한계 검증(스템 조건부 생성 관련 최신 연구 조사), 시스템 설계는
[`docs/PROPOSAL.md`](docs/PROPOSAL.md) 참고.

환경 세팅(로컬 VSCode + Colab 하이브리드)은 [`docs/ENVIRONMENT_SETUP.md`](docs/ENVIRONMENT_SETUP.md) 참고.

## 노트북

- [01_setup_and_test.ipynb](notebooks/01_setup_and_test.ipynb) — 환경 확인, MusicGen 단독 생성, Demucs 단독 분리 테스트
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/finneKIM/stem-remix-assistant/blob/main/notebooks/01_setup_and_test.ipynb)

## 폴더 구조

```
docs/
  PROPOSAL.md               # 기획서
  ENVIRONMENT_SETUP.md      # 환경 세팅 가이드
  troubleshooting/          # 트러블슈팅 기록 (문제-원인-해결 md, 날짜별)
notebooks/                  # Colab 노트북
src/                        # 파이프라인 코드
```

## 진행 상태

- [x] 기획 완료
- [ ] 환경 세팅 (Colab, AudioCraft, Demucs)
- [ ] 생성 파이프라인 구현
- [ ] 분리 파이프라인 구현
- [ ] 재생성/재조합 로직 구현
- [ ] 정량 평가 지표 구현
- [ ] 결과 정리
