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
  samples/                  # 데모 오디오 샘플 (생성/분리 검증 결과물)
  experiments/              # 실험 간 비교 문서
notebooks/                  # Colab 노트북
src/                        # 파이프라인 코드
experiments/                # 실험별 config, 결과, 결론 기록 (규칙은 experiments/README.md 참고)
```

## 실험

여러 생성 모델과 조건화 방식을 실험 단위로 비교한다. 실험 규칙과 브랜치 전략은 [`experiments/README.md`](experiments/README.md) 참고.

- EXP-001 — 베이스라인 (MusicGen 생성 + Demucs 분리 검증, 완료)
- EXP-002 — MusiConGen 파이프라인 (예정)
- EXP-003 — MusicGen-Melody/Style 파이프라인 (예정)

## 진행 상태

- [x] 기획 완료
- [x] 환경 세팅 (Colab, AudioCraft, Demucs)
- [x] MusicGen 단독 생성 검증 (GPU 동작 확인)
- [x] Demucs 단독 분리 검증
- [x] 재생성/재조합 로직 설계 확정 (파이프라인 A/B결정, 실험 프레임워크 구축)
- [ ] 재생성/재조합 로직 구현 (EXP-002 MusiConGen · EXP-003 MusicGen-Melody/Style, 진행 중 )
- [ ] 정량 평가
- [ ] 결과 정리
