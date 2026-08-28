# 스템 리믹스 도우미 (Stem Remix Assistant) — 프로젝트 기획서

> 원하는 분위기의 음악을 생성하고, 스템 단위로 분리한 뒤, 마음에 들지 않는 파트만 재생성해 교체하는 반복적 음악 창작 도구
>
> 작성자: 김하나 | 최종 수정: 2026-08-26 | 상태: 재생성/재조합 파이프라인 A/B 비교 실험 진행 중 (EXP-002, EXP-003)

---

## 0. 한 줄 요약

텍스트 프롬프트로 음악을 생성하고(MusicGen), 스템 단위로 분리한 뒤(Demucs), 마음에 안 드는 파트만 다시 생성해서 갈아 끼우는 **생성 → 분리 → 재생성 루프**를 예산 0원으로 구현하는 토이 프로젝트. 이상적인 방식(스템 단위 조건부 재생성)은 아직 오픈소스로 공개되지 않았다는 것을 확인했고, 그 한계를 인정한 상태에서 현실적인 우회 파이프라인을 설계·검증하는 과정 자체를 산출물로 삼는다.

---

## 1. 배경 및 동기

### 1.1 프로젝트 진행 이유

음악을 만들고 싶은 사람은 많지만, 결과물이 마음에 들지 않을 때 "이 부분만 다시" 라는 니즈를 해소해주는 도구는 드물다. 대부분의 AI 음악 생성 서비스(Suno, Soundful 등)는 전체 곡을 통째로 재생성하게 만들어서, 마음에 드는 80%를 버리고 처음부터 다시 뽑는 비효율이 생긴다. 제한 조건에서 생성물을 부분적으로 통제하며 반복 개선하는 것을 프로젝트의 목적으로 한다.

### 1.2 프로젝트 조건 설정 이유

- Claude Code 활용 능력(프롬프트 설계, 결과 검증, 반복 개선) 향상을 위해 Claude Code로 진행하며 그 과정을 기록에 남김
- 오디오 소스 분리(보컬/BGM/SFX) 도메인 경험 획득을 위해 해당 프로젝트로 실전 감각을 확보한다.
- 예산은 0원, 사용 가능한 GPU는 Google Colab 무료 티어(T4) 수준이라는 제약 안에서 움직인다.

---

## 2. 사전 조사 및 기술적 한계 검증

이상적으로 하고 싶었던 방식과 실제로 가능한 방식 사이의 troubleshooting 기록

### 2.1 이상적인 방식: 스템 조건부 생성 (Stem-conditioned Generation)

원래 그리던 그림은 "드럼과 베이스는 그대로 두고, 이 파트만 다시 만들어줘"라고 요청하면 나머지와 자연스럽게 어우러지는 새 스템을 만들어주는 모델을 쓰는 것이었다. 이런 능력을 가진 연구가 실제로 존재한다.

| 연구 | 발표 시점 | 상태 |
|---|---|---|
| MusicGen-Stem (Rouard et al.) | 2025.01 (arXiv 2501.01757), IEEE 게재 확정 | 논문에 "코드와 가중치를 공개할 예정"이라고 명시했으나, 2026.08 기준 GitHub 저장소를 찾지 못함 — 실질적으로 미공개 상태로 판단 |
| Stemphonic | 2026.02 (arXiv 2602.09891), ICASSP 2026 게재 예정 | 데모 웹사이트만 존재, 코드/모델 공개 여부 확인 불가 |

**결론**: 이 방식은 학계 최전선 연구 수준이며, 예산 0원으로 지금 당장 가져다 쓸 수 없다. 공개되기를 기다리기보다, 이번 프로젝트에서는 우회 파이프라인을 직접 설계한다.

### 2.2 실제로 사용 가능한 도구 (검증 완료)

| 도구 | 역할 | 라이선스/비용 | 확인된 사실 |
|---|---|---|---|
| MusicGen (Meta, AudioCraft) | 텍스트 → 음악 생성 | 코드 MIT, 가중치 CC-BY-NC 4.0 (비상업 한정) | Colab 무료 T4에서 `musicgen-stereo-medium`으로 60초 생성 실사용 사례 확인 |
| Demucs (Meta) | 음원 → 스템 분리 | 오픈소스, 사전학습 가중치 즉시 사용 가능 | 학습 없이 바로 추론에 사용 가능, 경량이라 무료 GPU에서도 무리 없음 |
| OnAir Music Dataset | 검증/데모용 소규모 데이터 | CC BY-SA 4.0, 상업적 이용 포함 완전 자유 | 16곡, 스템 4종(드럼/베이스/보컬/기타) 포함 |
| MUSDB18 | 정량 평가용 벤치마크 데이터 | CC BY-NC-SA (비상업), Zenodo 승인제 | 4.4GB(표준) / 22.7GB(HQ), 신청 후 통상 1일 내 승인 |

### 2.3 채택하는 우회 파이프라인과 그 한계

기획 초안(2026-08-13 시점)에서는 MusicGen의 melody conditioning 하나만으로 재생성을 처리하는 단일 파이프라인을 가정했다. 이후 실제 설계를 진행하며 다음 두 가지가 추가로 확인되어 파이프라인을 다시 잡았다(논의 과정 전체는 Notion "02번 노트북 — 재생성/재조합 로직 설계" 페이지에 기록).

1. **"스템 하나만 재생성"은 문자 그대로 불가능하다.** MusicGen은 입력 조건과 무관하게 항상 전체 믹스만 출력하며, 스템 단위로 직접 생성하는 기능이 없다. 따라서 재생성 대상 스템마다 (1) 전체 트랙을 조건부로 새로 생성 → (2) Demucs로 재분리 → (3) 원하는 스템만 추출하는 우회가 필요하다.
2. **BPM/코드를 명시적으로 강제할 수 있는 대안이 존재한다.** MusicGen 기반으로 BPM과 코드 진행을 직접 입력받아 템포·화성을 강제하는 **MusiConGen**(arXiv 2407.15060, 2024)이 코드·체크포인트 모두 공개된 상태로 존재하며, Colab 무료 T4로 추론 가능하다(8절 참고 자료). 원곡에서 1회 추출한 BPM/코드를 모든 스템 재생성에 동일하게 적용하면, 여러 스템을 동시에 재생성할 때 서로 어긋나는 문제를 줄일 수 있다.

이 두 가지를 반영해 **2026-08-26 기준, 파이프라인을 하나로 확정하지 않고 두 파이프라인을 각각 구현해 청취 비교로 우열을 가리는 A/B 비교 방식**으로 전환했다. 정량 지표만으로는 "타이밍 정확도"와 "원곡스러운 느낌" 중 무엇이 더 중요한지 판단할 근거가 없기 때문이다.

- **파이프라인 A — MusiConGen**: BPM·코드를 명시적으로 강제해 타이밍 정확도가 높다. 원곡 오디오를 직접 참조하지 않아 멜로디·음색의 원곡 유사성은 낮을 수 있다.
- **파이프라인 B — MusicGen-Melody/Style**: 원곡 오디오를 직접 참조해 멜로디·음색의 원곡 유사성이 높다. BPM은 텍스트 프롬프트 삽입 수준의 약한 신호라 타이밍 정확도는 상대적으로 낮을 수 있다.

두 파이프라인 모두 Demucs(분리) + madmom(비트/온셋/다운비트/코드 분석) + 사용자 프롬프트를 공통 입력으로 받고, 생성 결과를 Alignment Engine(Beat Align / Transient Align / Time Stretch)에서 원곡과 타이밍을 맞춘 뒤 FINAL STEM으로 산출한다(4.1절 참고).

**여전히 남아 있는 한계** (기획 단계에서 미리 인정하는 부분):
1. 두 파이프라인 모두 재생성 결과가 원곡과 템포·키·타이밍에서 완벽히 일치한다는 보장은 없다. Alignment Engine이 이를 보정하지만 완전한 싱크를 보장하지 않는다.
2. "자연스러운 블렌딩"이 이상적인 방식(스템 조건부 생성)만큼 매끄럽지 않을 가능성이 높고, 이는 정량적으로 측정해야 할 부분이다(4.3절 평가 지표 참고).
3. MusicGen·MusiConGen 가중치가 각각 CC-BY-NC 등 비상업 라이선스 제약을 받으므로, 이 파이프라인들은 비상업적 데모/포트폴리오 용도로 한정된다.
4. 두 파이프라인을 병행 구현·검증하는 데 드는 시간이 단일 파이프라인 대비 늘어난다. 이는 "어느 쪽이 더 중요한 속성인지" 자체가 사전에 판단 불가능한 트레이드오프였기 때문에 감수하는 비용으로 본다.

프로젝트 README와 최종 보고서에 그대로 남기는 것이라는 기획 원칙에 따라 완벽한 결과보다 한계를 인지하고 이를 우회하거나 측정한 과정을 보여주는 것이 목적에 더 부합한다.

---

## 3. 목표

### 3.1 이번 단계(토이 프로젝트)의 목표

- 생성 → 분리 → 재생성 → 재조합의 전체 파이프라인이 예산 0원, 무료 GPU 환경에서 end-to-end로 동작하는 것을 증명한다.
- 재조합 결과가 "그럴듯한지"를 주관적 인상이 아니라 최소한의 정량 지표로 측정한다.
- Claude Code를 이용해 파이프라인을 설계·구현·디버깅하는 과정(프롬프트, 시행착오, 개선)을 기록으로 남긴다.

### 3.2 이번 단계에서 하지 않는 것 (Out of Scope)

- 실시간 처리, 웹 서비스화, 배포는 다루지 않는다. 로컬/Colab 노트북 수준의 파이프라인으로 한정한다.
- 스템 조건부 생성 모델을 직접 학습시키는 것은 하지 않는다(데이터·컴퓨팅 자원상 비현실적). 대신 기존 오픈소스 조합으로 근사한다.
- 상업적 이용은 고려하지 않는다(MusicGen 가중치 라이선스 제약).

---

## 4. 시스템 설계

### 4.1 전체 흐름

1~3단계(프롬프트 입력 → MusicGen 초안 생성 → Demucs 4-스템 분리)는 기획 초안과 동일하게 유지한다. 4~8단계(재생성·재조합)는 2.3절의 A/B 비교 결정에 따라 아래처럼 다시 설계했다(2026-08-26 확정, 상세 다이어그램은 Notion "02번 노트북" 페이지).

```
[1] 사용자 프롬프트 입력
      ↓
[2] MusicGen으로 초안 트랙 생성 (예: "lofi hiphop with mellow piano, 90 BPM")
      ↓
[3] Demucs로 4-스템 분리 (드럼 / 베이스 / 보컬 / 기타)
      ↓
[4] 사용자가 마음에 안 드는 스템을 지정 (예: "드럼이 별로야")
      ↓
[5] 세 입력이 독립적으로 결합:
      Demucs(분리 결과) + madmom(비트/온셋/다운비트/코드 분석) + 사용자 재생성 프롬프트
      ↓
[6] 재생성 — 두 파이프라인을 각각 실행해 비교(A/B)
      파이프라인 A: MusiConGen (BPM·코드 명시적 강제)
      파이프라인 B: MusicGen-Melody/Style (원곡 오디오 직접 참조)
      ↓
[7] Alignment Engine — 재생성 스템의 beat/onset을 원곡과 비교해 정렬
      (Beat Align → Transient Align → Time Stretch)
      ↓
[8] FINAL STEM 산출
      마음에 안 들면 → [6]으로 루프백(재프롬프트 후 재시도)
      마음에 들면   → Recombination(유지할 Original Stems + FINAL STEM) → FINAL MIX
      ↓
[9] 정량 지표 측정(4.3절) + 청취 비교로 파이프라인 A/B 우열 판단
```

Alignment Engine과 Recombination은 서로 다른 단계다 — Alignment Engine은 재생성된 스템 하나의 타이밍만 보정하고, Recombination은 여러 스템을 하나의 최종 믹스로 합치는 별도 작업이다.

### 4.2 기술 스택

- **초안 생성**: MusicGen (`facebook/musicgen-stereo-medium`), AudioCraft 라이브러리
- **분리**: Demucs (사전학습 `htdemucs` 모델)
- **재생성 — 파이프라인 A**: MusiConGen ([YatingMusic/MusiConGen](https://github.com/YatingMusic/MusiConGen), BPM·코드 조건부 생성)
- **재생성 — 파이프라인 B**: MusicGen-Melody / MusicGen-Style (레퍼런스 오디오 조건부 생성)
- **분석/정렬**: madmom (비트·온셋·다운비트·코드 분석), 정렬 보정에 타임스트레칭 적용
- **실행 환경**: Google Colab 무료 티어 (T4 GPU)
- **개발 도구**: Claude Code (파이프라인 스크립트 작성, 디버깅, 실험 기록)
- **데이터**: OnAir Music Dataset(데모/검증용), 필요시 MUSDB18(정량 평가용, 승인 후)

### 4.3 평가 방법

이상적인 스템 조건부 생성과 비교할 정답 데이터가 없으므로, 완전한 정답 비교는 불가능하다. 대신 다음을 측정해 파이프라인 A/B를 비교한다(측정 항목·실험 설정은 `experiments/README.md`와 각 실험 폴더의 `config.yaml` 참고).

- **BPM 오차**: madmom으로 측정한 원곡 BPM과 재생성 스템 BPM의 차이
- **Beat alignment**: 원곡과 재생성 스템의 비트 그리드 일치도
- **Onset alignment**: 원곡과 재생성 스템의 온셋(타격 시점) 일치도
- **청취 평가**: 직접 들었을 때 원곡과 자연스럽게 어울리는지에 대한 주관 평가(파이프라인 A/B 비교표는 `docs/experiments/model_comparison.md`에 기록)

---

## 5. 일정 및 진행 현황

| 주차 | 내용 | 상태 |
|---|---|---|
| 1주차 | 환경 세팅 (Colab, AudioCraft, Demucs), MusicGen 단독 생성 테스트 | 완료 |
| 1~2주차 | Demucs 분리 파이프라인 구축, MusicGen 단독 생성 검증 (EXP-001 베이스라인) | 완료 |
| 2~3주차 | 재생성/재조합 로직 설계 확정 (파이프라인 A/B 결정, 2026-08-26), 실험 프레임워크 구축 | 완료 |
| 2~3주차 | 파이프라인 A(MusiConGen, EXP-002) · 파이프라인 B(MusicGen-Melody/Style, EXP-003) 구현 및 재조합 로직 구현 | 진행 중 |
| 3주차 | 정량 평가 지표 구현 및 측정, A/B 비교(`docs/experiments/model_comparison.md`) | 예정 |
| 4주차 | 결과 정리, README/포트폴리오 문서화, GitHub 공개 | 예정 |

*(실제 진행하면서 조정 — 각 단계에서 막히는 지점과 해결 과정은 `docs/troubleshooting/`에, 실험별 결과·결론은 `experiments/`의 각 실험 폴더 README.md에 별도로 기록)*

---

## 6. 리스크 및 대응

| 리스크 | 대응 방안 |
|---|---|
| 재생성 스템과 원곡 스템의 템포/키 불일치가 심함 | Alignment Engine(Beat Align / Transient Align / Time Stretch)으로 후처리 보정, 파이프라인 A(MusiConGen)로 BPM·코드를 애초에 강제해 불일치 폭 자체를 줄임 |
| 두 파이프라인(A/B) 중 무엇이 더 나은지 판단 기준이 모호함 | 정량 지표(BPM 오차, beat/onset alignment)와 청취 평가를 병행해 `docs/experiments/model_comparison.md`에 근거를 남기고 비교 |
| Colab 무료 티어 세션/시간 제한으로 작업 중단 | 중간 산출물(생성된 트랙, 분리된 스템)을 매 단계 로컬/Drive에 저장해 재개 가능하게 설계 |
| MusicGen/MusiConGen 대형 모델이 무료 GPU에서 메모리 부족 | `medium` 이하 모델로 축소, 생성 길이를 짧게(30~60초) 제한 |
| 정량 평가가 기대만큼 의미 있는 수치를 못 줌 | 정량 지표를 보조 수단으로 두고, 재생성 전후 비교 샘플을 직접 제시하는 정성적 근거를 병행 |

---

## 7. 산출물

- GitHub 저장소: 파이프라인 코드, 실행 노트북, README (한계 섹션 포함)
- 데모 샘플: 재조합 전/후 비교 오디오 (몇 개 트랙)
- 진행 기록: Claude Code로 작업하며 남긴 프롬프트/의사결정 로그 (자소서·면접 소재로 재사용)

---

## 8. 참고 자료 (검증 출처)

- [MUSDB18 | SigSep](https://sigsep.github.io/datasets/musdb.html)
- [OnAir Music Dataset - GitHub](https://github.com/sevagh/OnAir-Music-Dataset)
- [Demucs - GitHub (facebookresearch)](https://github.com/facebookresearch/demucs)
- [AudioCraft / MusicGen - GitHub](https://github.com/facebookresearch/audiocraft)
- [MusicGen on Colab Free Tier 실행 사례](https://dev.to/0xkoji/run-musicgen-stereo-on-google-colab-free-tier-4mgk)
- [MusicGen-Stem (arXiv 2501.01757)](https://arxiv.org/abs/2501.01757)
- [MusicGen-Stem 데모 페이지](https://simonrouard.github.io/musicgenstem/)
- [Stemphonic (arXiv 2602.09891)](https://arxiv.org/abs/2602.09891)
- [MusiConGen: Rhythm and Chord Control for Transformer-Based Text-to-Music Generation (arXiv 2407.15060)](https://arxiv.org/abs/2407.15060)
- [MusiConGen - GitHub (YatingMusic)](https://github.com/YatingMusic/MusiConGen)
- [madmom: A New Python Audio and Music Signal Processing Library (arXiv 1605.07008)](https://arxiv.org/abs/1605.07008)
