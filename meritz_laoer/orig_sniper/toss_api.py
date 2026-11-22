# ==========================================================
# FILE: meritz_laoer/orig_sniper/toss_api.py   (메리츠 쪽에서 만든 얇은 shim — 원작 파일 아님)
# 원작 quant_engine_core.py 가 `import toss_api` / `from toss_api import ...` 로 상수·도우미를 가져온다.
# 원작 toss_api.py 는 토스 네트워크 클라이언트라 가져오지 않고, 같은 이름을 원작 toss_api_core.py 에서 그대로 다시 내보낸다.
# 이 파일에는 로직·메리츠 코드를 넣지 않는다 (원작 업뎃 때 새 이름이 필요하면 sync_orig.py --check 가 알려준다).
# ==========================================================
import toss_api_core as _core

globals().update({k: v for k, v in vars(_core).items() if not k.startswith("__")})
