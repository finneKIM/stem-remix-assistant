# 데모 샘플

01_setup_and_test.ipynb에서 검증용으로 생성한 첫 결과물.

- `draft_0.wav` — MusicGen(facebook/musicgen-stereo-medium)으로 생성한 15초 원본 트랙. 프롬프트: "lofi hiphop with mellow piano, 90 BPM, warm and relaxed"
- `bass.wav`, `drums.wav`, `other.wav`, `vocals.wav` — 위 트랙을 Demucs(htdemucs)로 분리한 4개 스템

생성 및 분리 파이프라인이 예산 0원, Colab 무료 T4 환경에서 end-to-end로 동작함을 보여주는 최초 검증 샘플.
