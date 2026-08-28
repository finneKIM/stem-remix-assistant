# EXP-001 — 베이스라인 (생성 + 분리 검증)

01번 노트북에서 이미 완료한 검증을 실험 기록 형식에 맞춰 소급 정리한 것. 코드나 노트북은 그대로 두고, 이 폴더는 문서만 추가한다.

## 목적

생성-분리-재생성 루프의 앞부분(생성, 분리)이 예산 0원, Colab 무료 T4 환경에서 실제로 동작하는지 확인.

## 방법

`config.yaml` 참고. MusicGen(facebook/musicgen-stereo-medium)으로 15초 트랙을 생성한 뒤, Demucs(htdemucs)로 4개 스템으로 분리.

## 결과

생성과 분리 모두 성공. GPU 사용 여부는 `next(model.lm.parameters()).device`와 `nvidia-smi`로 직접 확인(`cuda:0`, 5679MiB 사용). 산출물은 `docs/samples/`에 보존.

## 결론 및 다음 실험

end-to-end 파이프라인의 절반(생성, 분리)이 동작함을 확인했으나, 재생성 시 원곡과의 타이밍 정렬 문제는 아직 검증 전. 이 문제를 다루기 위해 EXP-002(MusiConGen)와 EXP-003(MusicGen-Melody/Style) 두 파이프라인을 병행 실험한다.
