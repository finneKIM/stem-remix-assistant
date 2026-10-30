# 589바이트짜리 compression_state_dict.bin을 파일 손상으로 오판했다

## 상황

MusiConGen 체크포인트를 Hugging Face에서 받아 모델을 로드한 뒤, 생성물의 음질 저하 원인을 찾는 중이었다. 체크포인트 파일 목록을 확인했을 때 두 파일의 크기 차이가 비정상적으로 커 보였다.

## 에러

**에러가 없다.** 모델은 정상 로드되고 생성도 끝까지 된다. 파일 크기만 이상해 보였다.

```
state_dict.bin               2,643 MB
compression_state_dict.bin        589 B
```

LM 가중치가 2.6GB인데 코덱(압축 모델) 가중치가 589바이트였다. EnCodec 같은 뉴럴 코덱은 수십~수백 MB가 정상이므로, **다운로드가 잘렸거나 파일이 손상된 것**으로 판단했다.

그 판단을 전제로 "코덱 가중치가 깨져서 디코딩 품질이 나쁘다"는 가설을 세우고 한동안 그 방향을 수사했다.

## 원인

**손상이 아니다. 정상 설계다.**

`compression_state_dict.bin`은 코덱 가중치를 담고 있지 않다. Hugging Face Hub의 코덱 모델을 **참조하는 포인터**이고, 그 내용은 어떤 코덱을 쓸지와 설정 몇 개뿐이다. 실제 가중치는 로드 시점에 별도로 내려온다.

```
참조 대상: facebook/encodec_32khz
로더 클래스: HFEncodecCompressionModel
```

589바이트는 그 메타데이터의 크기이고, 가중치가 거기 들어갈 이유가 없다. audiocraft는 코덱을 자체 체크포인트에 포함하는 경로(`EncodecModel` 직접 로드)와 Hub에서 가져오는 경로(`HFEncodecCompressionModel`)를 모두 지원하고, 이 체크포인트는 후자를 쓴다.

즉 **"코덱 가중치가 2.6GB 파일에도 589바이트 파일에도 없다"가 맞고, 그게 정상이다.** 코덱은 로드 중에 `facebook/encodec_32khz`에서 받아온다.

## 해결

### 1. 로드된 코덱의 실체를 확인한다

파일 크기 대신 **로드된 객체**를 본다. 크기는 설계를 말해주지 않고, 객체는 말해준다.

```python
comp = model.compression_model
print("class       :", type(comp).__name__)
print("sample_rate :", comp.sample_rate)
print("channels    :", comp.channels)
print("frame_rate  :", comp.frame_rate)

# HF 코덱을 참조하는 경우 내부 모델이 따로 들어 있다
inner = getattr(comp, "model", None)
if inner is not None:
    n = sum(p.numel() for p in inner.parameters())
    print("inner class :", type(inner).__name__)
    print("params      :", f"{n:,}")
```

`params`가 수백만~수천만으로 나오면 가중치가 실제로 메모리에 올라와 있다는 뜻이다. 589바이트 파일과 무관하게 코덱은 정상이다.

### 2. 코덱 단독으로 왕복 테스트를 돌린다

손상 여부를 추측하지 않고 측정한다. **원곡을 인코딩 후 디코딩해 지표를 비교하면 코덱의 기여를 분리할 수 있다.**

```python
import torch, librosa, numpy as np

y, sr = librosa.load(src_path, sr=model.sample_rate, mono=True)
wav = torch.from_numpy(y)[None, None].to(next(model.lm.parameters()).device)

with torch.no_grad():
    codes, scale = model.compression_model.encode(wav)
    recon = model.compression_model.decode(codes, scale)

out = recon[0].cpu()
# 지표 비교: 원곡 vs 왕복
```

이 테스트의 결과가 결정적이었다.

```
              flatness   8kHz+
원곡          0.00679    0.0579
코덱 왕복     0.00451    0.0472
```

flatness와 고역 에너지가 **왕복 후에 더 낮다**. 코덱 통과는 잡음 지표를 오히려 개선한다. 고역 성분을 깎아내기 때문이다. 따라서 코덱은 음질 저하의 원인이 아니고, 이 값이 **생성 모델이 도달할 수 있는 이론적 하한선**이 된다.

### 3. 파일 크기로 손상을 판단해야 할 때는 참조 여부를 먼저 본다

작은 바이너리를 만나면 열어서 무엇인지 확인한다. 가중치 텐서가 들어 있는지, 문자열 참조만 있는지는 바로 보인다.

```python
import torch
obj = torch.load("compression_state_dict.bin", map_location="cpu", weights_only=False)
print(type(obj))
if isinstance(obj, dict):
    for k, v in obj.items():
        kind = tuple(v.shape) if hasattr(v, "shape") else repr(v)[:80]
        print(f"  {k}: {kind}")
```

## 주의사항

위 `torch.load`에 `weights_only=False`가 필요한 경우가 있다. 이 플래그는 임의 코드 실행 위험이 있으므로 **신뢰할 수 있는 출처의 체크포인트에만** 쓴다. 내용 확인이 목적이라면 먼저 `weights_only=True`로 시도하고, 거부될 때만 출처를 확인한 뒤 끈다.

## 배운 점 / Development Way

**파일 크기는 설계를 말해주지 않는다.** 작은 파일은 손상일 수도 있고 참조일 수도 있고 설정일 수도 있다. 크기 하나로 가설을 세우면 그 가설이 틀렸을 때 어디서 틀렸는지 알기 어렵다. 판단 근거로 쓰기 전에 **파일을 열어 구조를 본다.** 비용은 몇 초이고, 틀린 가설로 수사 방향을 잃는 비용은 그보다 크다.

구성 요소의 무죄를 **추측으로 처리하지 않고 측정으로 분리한다.** "코덱은 괜찮을 것 같다"와 "코덱 왕복 flatness가 원곡보다 낮다"는 다른 종류의 진술이다. 다단 파이프라인에서 한 단계를 의심할 때는 그 단계만 단독으로 돌려 입출력을 비교하는 경로를 만든다. 생성 모델은 입력이 토큰이라 단독 실행이 어려워 보이지만, 코덱은 오디오를 받아 오디오를 내므로 **원곡을 통과시키면 그 자체로 대조 실험이 된다.**

그리고 그 측정값은 무죄 판정에만 쓰이지 않았다. 코덱 왕복 값이 **이후 모든 비교의 하한선**이 됐다. 어떤 구성 요소를 검증하려고 만든 측정값이 기준선으로 재사용되는 경우가 많으므로, 검증 실행의 결과는 버리지 않고 기준선 파일로 분리해 보관한다.

마지막으로, 오픈소스 체크포인트는 **여러 로딩 경로를 지원하는 경우가 많다**는 것을 기본 전제로 둔다. 같은 모델이 가중치를 자체 포함하기도 하고 Hub에서 받기도 한다. 어느 쪽인지는 파일 목록이 아니라 로더 클래스가 말해준다.
