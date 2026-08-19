# 2026-08-14 Colab 리소스 그래프가 GPU 미사용으로 오인되게 표시됨

## 상황

MusicGen medium 모델로 15초 트랙 생성 테스트를 진행하던 중, 화면 상단의 Colab 리소스 그래프(System RAM, GPU RAM, Disk)를 확인했다.

## 문제

System RAM은 올라가는데 GPU RAM이 0.0 / 15.0 GB로 계속 표시되어, 모델이 GPU가 아니라 CPU에서 돌고 있는 것으로 의심되었다.

## 원인

실제로는 GPU가 정상적으로 사용되고 있었다. Colab 화면의 리소스 그래프 위젯이 실시간 상태를 즉시 반영하지 못하고 갱신이 지연되는 경우가 있었다.

## 해결

화면 그래프 대신 아래 두 가지로 직접 확인했다.

```python
print(next(model.lm.parameters()).device)  # cuda:0 확인
!nvidia-smi  # 실제 프로세스별 GPU 메모리 사용량 확인
```

`nvidia-smi` 결과 `/usr/bin/python3` 프로세스가 GPU 메모리 약 5.5GB를 사용 중인 것으로 확인되어, GPU가 정상적으로 쓰이고 있었음을 확인했다.

## 배운 점

Colab 화면 상단의 리소스 그래프는 참고용으로만 보고, GPU 사용 여부처럼 확실한 확인이 필요할 때는 항상 `nvidia-smi`나 `next(model.parameters()).device`처럼 직접 조회하는 방법을 우선한다.

GPU-Util이 0%로 보여도 GPU 메모리가 할당되어 있다면 이는 모델이 GPU에 올라가 있고 마침 그 순간 연산이 쉬고 있다는 뜻이지, GPU 미사용을 의미하지 않는다.
