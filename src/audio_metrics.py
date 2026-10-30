"""오디오 품질 정량 지표 — 프로젝트 전체에서 유일한 측정 함수.

이 파일을 노트북에 복사하지 않는다. import해서 쓴다.

    import sys; sys.path.insert(0, "/content/repo")
    from src.audio_metrics import measure, BASELINE, to_row

왜 단일 정의여야 하는가
----------------------
측정값을 서로 비교하려면 측정 함수가 바이트 단위로 동일해야 한다.
노트북마다 복사본이 생기면 그 순간부터 버전이 갈라지고, 과거 측정값과의
비교가 조용히 무효가 된다. 에러가 나지 않으므로 알아차리기 어렵다.

이 파일을 수정할 때는 반드시 _reference/ 의 기준선을 재측정해
아래 BASELINE 값과 일치하는지 확인한다. 값이 달라지면 과거 모든
측정값을 재측정해야 한다.
"""

import numpy as np
import librosa

SAMPLE_RATE = 32000
N_FFT = 2048

# ── 기준선 (2026-10-30 측정, _reference/ 기준) ────────────────────────
# codec: 원곡을 EnCodec으로 인코딩 후 디코딩한 왕복 결과.
#        생성 모델이 도달할 수 있는 이론적 하한선.
# orig:  원곡 그대로.
# control: MusiConGen 저자의 공식 설정을 그대로 돌린 대조군.
#          "우리가 추가한 잡음"을 재는 기준이 이것이다.
BASELINE = {
    "codec":   {"flatness": 0.00451, "hi8k": 0.0472},
    "orig":    {"flatness": 0.00679, "hi8k": 0.0579},
    "control": {"flatness": 0.03212, "hi8k": 0.1874},
}


def measure(path, hint_bpm=None, sr=SAMPLE_RATE):
    """wav 한 개의 품질 지표를 측정한다.

    Parameters
    ----------
    path : str
        wav 경로.
    hint_bpm : float, optional
        목표 BPM. **반드시 넘긴다.** librosa.beat.beat_track은 힌트가 없으면
        옥타브 오류(2배/절반)를 낸다. 2026-10-30에 코덱 왕복 음원이
        89 BPM 대신 178.6 BPM으로 측정된 원인이 이것이었다.

    Returns
    -------
    dict
        flatness : spectral flatness, 주파수 스펙트럼의 "평평함".
            봉우리가 뾰족하면 작고(음정 있는 소리), 평평하면 크다(백색잡음).
            잡음 총량의 대리 지표.
        hi8k : 8kHz 이상 대역이 전체 에너지에서 차지하는 비율.
            "지지직" 계열 잡음은 고역에 몰리므로 flatness와 독립적인 단서가 된다.
        perc : HPSS(Harmonic-Percussive Source Separation)로 분리한 뒤
            타격음(음정 없는 성분 — 드럼, 클릭, 잡음)의 에너지 비중.
            flatness가 그대로인데 perc만 내려가면 "잡음이 줄었다"가 아니라
            "조화음 비중이 올라갔다"는 뜻이다. 반드시 교차로 읽는다.
        bpm : 측정된 템포.
        sec : 길이(초).
        rms : 전체 RMS. 라우드니스 정규화 차이를 잡아내는 보조 지표.

    Notes
    -----
    지표를 세 개 두는 이유: 하나만 보면 반대 결론도 나온다.
    2026-10-30 cfg_coef 1.5 실험에서 flatness는 +2.0%(불변), perc는 -37.3%였다.
    flatness만 봤다면 "변화 없음", perc만 봤다면 "크게 개선"으로 오판했을 것이다.
    """
    y, sr = librosa.load(path, sr=sr, mono=True)

    flat = float(np.mean(librosa.feature.spectral_flatness(y=y)))

    S = np.abs(librosa.stft(y, n_fft=N_FFT))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
    hi = float(S[freqs >= 8000].sum() / (S.sum() + 1e-12))

    y_h, y_p = librosa.effects.hpss(y)
    perc = float(np.sum(y_p ** 2) / (np.sum(y_h ** 2) + np.sum(y_p ** 2) + 1e-12))

    kw = {"start_bpm": hint_bpm} if hint_bpm else {}
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, **kw)

    return {
        "flatness": flat,
        "hi8k": hi,
        "perc": perc,
        "bpm": float(np.atleast_1d(tempo)[0]),
        "sec": len(y) / sr,
        "rms": float(np.sqrt(np.mean(y ** 2))),
    }


def normalized(m):
    """측정값을 기준선 대비 배수로 바꾼다.

    절대값만으로는 "좋다/나쁘다"를 말할 수 없다. 코덱 왕복 대비 몇 배인지,
    공식 대조군 대비 몇 배인지가 판단 가능한 숫자다.

    x_codec   : 이론적 하한선 대비. 모델 고유 잡음 + 우리 기여분의 합.
    x_control : 저자 공식 설정 대비. **우리가 추가한 분만** 분리해서 본다.
    """
    return {
        "x_codec": m["flatness"] / BASELINE["codec"]["flatness"],
        "x_control": m["flatness"] / BASELINE["control"]["flatness"],
    }


CSV_COLUMNS = [
    "run_id", "date", "label", "duration_s", "cfg_coef", "bpm_target", "bars",
    "flatness", "hi8k", "perc", "bpm_measured", "x_codec", "x_control", "note",
]


def to_row(run_id, date, label, cfg, m, note=""):
    """metrics.csv 한 행으로 변환한다.

    원장은 append-only다. 기존 행을 고치지 않는다. 측정 함수가 바뀌어
    값이 달라졌다면 새 run_id로 다시 넣고, note에 그 사실을 적는다.
    """
    n = normalized(m)
    return {
        "run_id": run_id,
        "date": date,
        "label": label,
        "duration_s": cfg.get("duration"),
        "cfg_coef": cfg.get("cfg_coef"),
        "bpm_target": cfg.get("bpm"),
        "bars": cfg.get("bars"),
        "flatness": round(m["flatness"], 5),
        "hi8k": round(m["hi8k"], 4),
        "perc": round(m["perc"], 3),
        "bpm_measured": round(m["bpm"], 1),
        "x_codec": round(n["x_codec"], 2),
        "x_control": round(n["x_control"], 2),
        "note": note,
    }


def run_id_for(cfg, stamp):
    """설정 해시를 포함한 고정 길이 run_id.

    파일명에 파라미터를 박는 방식(cfg1.5_seed42_bars11)은 파라미터가
    늘어나면 무너진다. 해시는 "같은 설정인가"를 한눈에 판별하는 용도이고,
    설정 자체는 같은 폴더의 config.json에 원문으로 남긴다.

    stamp : "YYYYMMDD_HHMM" (KST). Colab 런타임은 UTC이므로 호출하는 쪽에서
            ZoneInfo("Asia/Seoul")로 만든 값을 넘긴다.
    """
    import hashlib
    import json
    h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:8]
    return f"{stamp}_{h}"
