# 2026-10-31 Muse — 스나이퍼룸 iframe 거부 수정

## 증상
- 상황판 스나이퍼룸 탭은 뜨는데, 안의 그림 iframe이 "연결을 거부했습니다"로 뜸.
- 원인: 사무실 서버가 모든 페이지에 `X-Frame-Options: DENY` + CSP `frame-ancestors 'none'`을 보냄. 같은 주소 iframe도 막힘.

## 변경 파일
- `bot_office/server.py`만: `send()`에 `frame_self` 옵션 추가, `/sniper-picture`만 `SAMEORIGIN` + `frame-ancestors 'self'`로 보냄.
- 그 외 페이지(로그인·상황판·API 등)는 DENY 유지. 외부 사이트에서의 클릭재킹 차단은 그대로 유지됨.

## 확인 필요 (서버 적용 뒤)
- 상황판 스나이퍼룸 탭에서 그림이 iframe으로 보이는지.
- 그림 페이지 직접 열기도 그대로 되는지.
