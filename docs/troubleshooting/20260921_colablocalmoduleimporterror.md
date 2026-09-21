# Colab에서 별도로 전달받은 .py 유틸 모듈을 import하지 못하는 문제

## 상황

재사용 가능한 유틸리티 함수들을 별도의 `.py` 파일로 작성해 Colab 노트북에서 `import`로 불러와 쓰려 했으나, 다음 에러가 발생했다.

## 에러

```
ModuleNotFoundError: No module named 'backup_to_drive_utils'
```

## 원인

외부 채팅/작업 도구에서 전달(다운로드)된 `.py` 파일은 사용자의 로컬 다운로드 폴더에 저장될 뿐, Colab 노트북의 실행 환경(가상 머신) 안으로 자동으로 들어가지 않는다. `import`가 성공하려면 그 모듈 파일이 실제로 Colab 노트북이 실행되는 파일시스템(예: `/content/`) 안에 물리적으로 존재해야 한다. 파일을 다운로드받는 것과 Colab에 업로드하는 것은 별개의 동작이다.

### 원인 진단 과정에서 발견한 부수 문제 — find 명령어가 비정상적으로 느림

파일이 실제로 어디 있는지 찾기 위해 아래와 같이 광범위한 `find`를 실행했는데, 응답이 매우 느렸다.

```python
subprocess.run(["find", "/content", "/root", "/tmp", "-name", "backup_to_drive_utils.py"], ...)
```

**원인**: Colab에서 Google Drive를 마운트하면 `/content/drive/MyDrive/...` 경로가 원격 파일시스템으로 연결된다. `find`가 `/content` 전체를 재귀 탐색하면서 이 마운트된 Drive 안까지 순회하려고 시도했고, Drive 안에 파일이 많을수록 이 과정 자체가 크게 느려진다.

**해결**: Drive 마운트 경로를 탐색 대상에서 제외하거나(`-not -path "*/drive/*"`), 탐색 깊이를 제한(`-maxdepth`)해서 필요한 범위만 빠르게 확인한다.

```python
result = subprocess.run(
    ["find", "/content", "-maxdepth", "2", "-name", "backup_to_drive_utils.py",
     "-not", "-path", "*/drive/*"],
    capture_output=True, text=True, timeout=10
)
```

## 최종 해결 — import 없이 단일 셀로 통합

파일을 별도로 업로드하는 절차 자체를 없애고, 함수 정의와 실제 실행 코드를 하나의 노트북 셀에 전부 포함시키는 방식으로 전환했다.

```python
import os, shutil

def backup_file(src_path, subfolder=""):
    if not os.path.exists(src_path):
        print(f"  [건너뜀] 원본 없음: {src_path}")
        return None
    dest_dir = os.path.join(BACKUP_ROOT, subfolder) if subfolder else BACKUP_ROOT
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, os.path.basename(src_path))
    shutil.copy2(src_path, dest_path)
    return dest_path

# ... 이하 함수 정의 + 바로 이어서 실제 사용 코드까지 한 셀에 작성
```

이렇게 하면 별도 파일 업로드 없이, 셀 하나를 실행하는 것만으로 함수 정의와 실행이 동시에 끝난다. 같은 커널이 살아있는 동안은 정의된 함수를 이후 셀에서도 계속 재사용할 수 있다(단, 커널을 재시작하면 이 셀을 다시 실행해야 한다).

## 요약

| 항목 | 내용 |
|---|---|
| 증상 | 별도로 전달받은 .py 파일을 import하려 하면 ModuleNotFoundError |
| 원인 | 파일이 Colab 노트북의 실행 환경에 실제로 업로드되어 있지 않았음 |
| 부수 문제 | Drive 마운트 경로까지 재귀 탐색해 find 명령이 느려짐 |
| 해결 | 별도 파일 import 대신, 함수 정의와 실행 코드를 하나의 셀로 통합 |

## 배운 점 / Development Way

노트북 기반 환경(Colab, Jupyter 등)에서 외부 도구가 만들어준 파일을 활용하려 할 때는, "그 파일이 실제로 실행 환경의 파일시스템 안에 존재하는가"를 가장 먼저 확인하는 것이 순서다. 파일이 전달(다운로드)되었다는 사실과 그 파일이 실행 가능한 위치에 놓였다는 사실은 서로 다른 단계이며, 이 둘을 혼동하면 엉뚱한 곳(예: import 문법, 모듈 경로 설정)에서 원인을 찾느라 시간을 쓰게 된다. 여러 도구/환경 사이를 오가며 작업할 때는 "이 파일이 지금 어느 파일시스템에 있는가"를 매 단계 명확히 인지하는 것이 중요하다.

또한 마운트된 원격 파일시스템(클라우드 드라이브 등)이 로컬 디렉토리 트리 안에 붙어 있는 환경에서는, 그 하위 경로를 무심코 전체 탐색하는 명령(`find`, `grep -r` 등)이 예상보다 훨씬 느려질 수 있다는 것을 기억해야 한다. 이런 환경에서는 탐색 범위를 명시적으로 좁히는 것(깊이 제한, 특정 경로 제외)을 기본 습관으로 삼는 것이 좋다. 마지막으로, 별도 모듈 파일을 만들어 재사용성을 높이려는 시도가 오히려 복잡성과 실패 지점을 늘릴 수 있는 환경이라면, 함수 정의와 실행을 한 곳에 모으는 더 단순한 방식이 실용적인 대안이 될 수 있다.
