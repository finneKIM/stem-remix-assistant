# Colab 노트북을 GitHub에 저장하면 재생 위젯의 base64 오디오가 커밋된다

## 상황

Colab에서 생성한 오디오를 바로 들어보려고 `IPython.display.Audio`로 재생 셀을 넣어 두고 작업했다. 이 노트북은 GitHub에서 열었기 때문에 Ctrl+S를 누르면 GitHub API로 직접 커밋된다.

저장소 공개 전에 노출 점검을 하려고 커밋된 `.ipynb`를 긁어 민감 패턴을 스캔했다.

## 에러

**에러가 없다.** 저장은 정상적으로 끝난다.

스캔 결과에서 드러났다.

```
셀 207개 / 저장된 출력 191개

민감 패턴 1962건:
  [Drive 폴더 ID   ] 셀153 출력      18k9wLvJH8HxyeLBDMqcwhLKYcNCyg3ENMqXxP
  [Drive 폴더 ID   ] 셀153 출력      1JgcvsydkLqYoqi1tKW8t5CmALZUqJy0XKyItlyvHLC8sUyydLFEsMC0HLFgtSCvXLf0qC
  [Drive 폴더 ID   ] 셀153 출력      1MCSwFrAo0DPALdAVUC0QCnAh4BoAIPApgC2QJtAq0AOAJGARwCDgAaAs
  ... (같은 셀에서 약 1,956건)
```

처음에는 자격 정보가 대량 유출된 것으로 보였다. 실제로는 전부 오탐이었고, **그 오탐이 다른 문제를 드러냈다.**

## 원인

스캔에 쓴 정규식이 `\b1[A-Za-z0-9_-]{32,}\b`, 즉 "1로 시작하는 33자 이상의 영숫자"였다. 셀153의 출력에 **base64로 인코딩된 오디오가 통째로 들어 있어서** 그 안의 수많은 조각이 이 패턴에 걸렸다.

셀153은 `IPython.display.Audio(path)` 호출 셀이다. 이 함수는 파일을 읽어 **base64로 변환한 뒤 노트북 출력에 직접 삽입**한다. 브라우저가 외부 파일에 접근할 수 없으므로 데이터를 HTML 안에 넣는 설계이고, 그 자체는 의도된 동작이다.

문제는 Colab의 저장 동작과 겹칠 때 생긴다.

- Ctrl+S는 `.ipynb` **한 개만** 커밋한다. `/content`나 마운트된 저장소의 파일은 올라가지 않는다
- 따라서 wav/mp3 파일 자체는 `.gitignore`로 막혀 있어도 안전하다
- 그런데 **출력 셀에 base64로 박힌 오디오는 `.ipynb`의 일부**이므로 `.gitignore`와 무관하게 커밋된다

크기를 계산하면 규모가 보인다. 30초 모노 32kHz 16bit wav는

```
30 x 32000 x 2 = 1,920,000 B  ~= 1.92 MB
base64 인코딩은 약 4/3 배  ->  약 2.6 MB
```

이것이 커밋마다 새 blob으로 쌓인다. git 히스토리는 되돌릴 수 없으므로 영구 누적이다.

Colab에는 "저장할 때 출력만 제외" 기능이 없다. 로컬 git 저장소라면 `nbstripout`을 git filter로 걸어 자동화할 수 있지만, **웹 에디터로 직접 커밋하는 흐름에는 로컬 clone도 staging area도 없어 그 방법을 쓸 수 없다.**

## 해결

### 1. 저장 전에 출력을 지운다 — 유일한 수단

```
메뉴  수정 -> 출력 모두 지우기   ->   Ctrl+S
```

수동이므로 잊기 쉽다. 그래서 다음 항목이 필요하다.

### 2. 출력을 지워도 손실이 없게 코드를 짠다

출력을 지우는 것이 안전하려면, **봐야 하는 숫자가 출력에만 있으면 안 된다.** 측정·집계 결과를 내는 셀은 반드시 파일로도 쓴다.

```python
# 나쁜 예 — 출력을 지우면 결과가 사라진다
print(f"flatness: {flat:.5f}")

# 좋은 예 — 출력을 지워도 남는다
import json
rows[label] = {"flatness": flat, "hi8k": hi}
json.dump(rows, open(OUT, "w"), ensure_ascii=False, indent=2)
print(f"flatness: {flat:.5f}  -> {OUT}")
```

이 규칙을 지키면 출력은 확인용 사본이 되고, 지우는 것이 손실이 아니게 된다.

### 3. 노출·용량 점검 스캔

공개 저장소라면 토큰 없이 raw 파일을 받아 점검할 수 있다. `저장된 출력 N개`가 0이 아니면 출력이 커밋되어 있다는 뜻이고, 그것이 1차 점검이다.

```python
import urllib.request, json, re

RAW = "https://raw.githubusercontent.com/<owner>/<repo>/main/notebooks/<name>.ipynb"
nb = json.loads(urllib.request.urlopen(RAW).read().decode())

PATTERNS = {
    "email":      r"[\w.\-]+@[\w\-]+\.\w+",
    "long-id":    r"\b1[A-Za-z0-9_-]{32,}\b",
    "token":      r"\b(hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})\b",
    "local-path": r"(/Users/[^\s\"']+|[A-Z]:\\\\)",
}

found, n_out, out_bytes = [], 0, 0
for i, cell in enumerate(nb.get("cells", [])):
    for pat_name, pat in PATTERNS.items():
        for m in set(re.findall(pat, "".join(cell.get("source", [])))):
            found.append((pat_name, f"cell{i} source", (m if isinstance(m, str) else m[0])[:70]))
    for o in cell.get("outputs", []):
        n_out += 1
        txt = "".join(o.get("text", [])) if "text" in o else json.dumps(o.get("data", {}))
        out_bytes += len(txt)
        for pat_name, pat in PATTERNS.items():
            for m in set(re.findall(pat, txt)):
                found.append((pat_name, f"cell{i} output", (m if isinstance(m, str) else m[0])[:70]))

print(f"cells {len(nb.get('cells', []))} / stored outputs {n_out} / output bytes {out_bytes:,}")
for name, where, hit in found:
    print(f"  [{name:10}] {where:16} {hit}")

md = nb.get("metadata", {}).get("colab", {})
print("\ncolab metadata keys:", list(md.keys()))
print("provenance entries :", len(md.get("provenance", [])))
```

### 4. 오탐을 분류한 뒤 보고한다

건수만 세면 과잉 경보가 된다. 한 셀의 출력에서 수십~수천 건이 쏟아지면 base64를 의심하고, 그 셀이 `Audio`/`Image` 호출 셀인지 확인한다.

| 패턴 | 흔한 오탐 | 구분법 |
|---|---|---|
| 긴 ID | base64 오디오·이미지 조각 | 한 셀 출력에 대량으로 몰려 있는지, 그 셀이 표시 함수 호출인지 |
| 이메일 | pip install 로그의 라이브러리 메인테이너 주소 | 도메인이 제3자 프로젝트인지 |
| 로컬 경로 | 컨테이너 내부 경로 | `/content`, `/usr/local` 은 민감하지 않음 |

실측에서는 1,962건 중 1,956건이 base64 오탐이었고, 실제 확인이 필요한 것은 6건이었다. 그리고 그 6건도 노출 위험은 없었다.

### 5. 노트북을 바이너리로 표시해 diff를 접는다

출력이 이미 커밋된 히스토리는 되돌릴 수 없다. 최소한 커밋 히스토리를 읽을 수 있게 만든다.

```
# .gitattributes
*.ipynb binary
```

이렇게 하면 GitHub가 노트북의 diff를 생략하므로, 수천 줄짜리 base64 diff가 히스토리를 덮는 것을 막는다.

## 주의사항

이미 push된 것은 **지우지 않고 무효화하는 쪽이 확실하다.** 히스토리 재작성은 웹 에디터 흐름에서는 불가능하고, 가능하더라도 fork·clone된 사본에 소급되지 않는다. 자격 정보라면 발급처에서 폐기하고, 접근 식별자라면 공유 설정을 제한으로 바꾼다.

용량 문제는 무효화할 수 없다. 누적이 심하면 저장소를 새로 만드는 것이 현실적인 선택일 수 있고, 그 판단은 히스토리 크기를 확인한 뒤에 한다.

## 배운 점 / Development Way

**조치를 제안하기 전에 그 조치가 실행 가능한 환경인지 확인한다.** `nbstripout`은 이 문제의 표준 해법이고, 로컬 clone이 없는 흐름에서는 쓸 수 없다. 좋은 도구인 것과 지금 쓸 수 있는 것은 다른 문제다. "보통 이렇게 한다"가 떠오를 때가 환경을 확인할 시점이다.

**저장소에 무엇을 추가하자고 말하기 전에 이미 무엇이 있는지 본다.** 이 사례에서 `.gitignore`는 이미 오디오를 제외하고 있었고 데모 샘플만 예외로 허용하는 설계까지 되어 있었다. 확인하지 않고 제안하면 이미 한 일을 다시 하라는 말이 되고, 신뢰를 잃는다.

**출력을 휘발성으로 취급하는 설계를 먼저 만든다.** "저장 전에 출력을 지운다"는 규칙은 혼자 서지 못한다. 출력에만 있는 결과가 있으면 지우는 것이 손실이 되고, 손실이 되면 규칙이 깨진다. 결과를 파일로 쓰는 습관이 선행 조건이고, 그것이 갖춰지면 출력 삭제는 비용 없는 동작이 된다.

**스캔 결과는 건수가 아니라 분류로 보고한다.** 오탐이 압도적인 탐지기는 정확한 탐지기보다 위험할 수 있다. 1,962건을 그대로 전하면 받는 쪽은 전체를 무시하거나 과도하게 놀란다. 분류해서 "실제 6건, 오탐 1,956건, 오탐의 원인은 base64 오디오"로 전하면, 그 오탐이 사실은 **다른 문제의 증거**라는 것까지 전달된다. 이번에는 오탐 자체가 발견이었다.

**데이터를 문서에 삽입하는 함수는 그 문서가 어디로 가는지와 함께 생각한다.** 표시·재생·시각화 함수 중 결과를 파일 참조가 아니라 인라인 데이터로 넣는 것들이 있고, 그 문서가 버전 관리에 들어가면 저장소가 데이터 저장소가 된다. 편의 함수의 출력 형태를 한 번 확인해 두는 것으로 피할 수 있다.
