# EXP-002 — MusiConGen 파이프라인 (진행 중)

## 목적

BPM·코드를 명시적으로 강제하는 MusiConGen을 재생성 단계에 써서, 원곡과의 타이밍 정렬 문제를 처음부터 줄일 수 있는지 검증.

## 방법

`config.yaml` 참고. 파이프라인 전체 구조는 Notion "02번 노트북 — 재생성/재조합 로직 설계" 페이지의 다이어그램 참고.

파이프라인 순서 (PROPOSAL.md 2.3, 4.1):

1. 원곡에서 BPM·코드를 한 번 추출한다 (madmom).
2. MusiConGen으로 BPM·코드 조건부 전체 백킹트랙을 생성한다.
3. 생성된 전체 트랙을 Demucs로 재분리한다.
4. 재분리 결과에서 `target_stem`(예: drums)만 추출한다.

`target_stem`은 생성 조건이 아니라 3단계 재분리 이후의 추출 라벨이다. MusiConGen을 비롯한 MusicGen 계열 모델은 스템 단위 생성을 지원하지 않는다.

## 진행 상황 (2026-10-02)

- 초기 구현에서 `target_stem`을 생성 조건으로 직접 전달해 드럼 전용 생성을 시도했다가 음질 저하가 발생했다. 설계를 재검토한 뒤 위 파이프라인 순서로 정정했다.
- 현재 15초 길이(EXP-001 산출물 `draft_0.wav` 기준)로 1차 검증 진행 중 — 전체 트랙 재생성(target_stem 미사용) → Demucs 재분리 → 드럼 추출 순서로 재실행할 예정이다.
- 상세 트러블슈팅: [`docs/troubleshooting/20261002_musicongendrumstemqualitydegradation.md`](../../docs/troubleshooting/20261002_musicongendrumstemqualitydegradation.md)

## 예상 트레이드오프

BPM·코드 정합성은 높을 것으로 예상되나, 원곡 오디오를 직접 참조하지 않아 멜로디·음색의 원곡 유사성은 EXP-003보다 낮을 수 있음. 실제 결과는 청취 비교와 정량 지표로 확인.

## 결과

(진행 후 기록)

## 결론

(진행 후 기록)
