# 팬딩 서버 직접 수집기 — 서버 설치·로그인·적용 초안 (vNEXT)

> 서버 적용은 **텔레그램 6. Update 승인 뒤**에만 한다. 이 문서는 초안이다.
> Claude는 서버에 아무것도 적용하지 않았다. 아래 명령은 Muse와 사용자가 실행한다.
> 비밀번호·토큰은 이 문서, 채팅, 코드 어디에도 적지 않는다. 비밀번호는 4단계에서 SSH 창에 직접 입력하고, 입력해도 화면에 보이지 않는다.

**기한:** 2026-11-13 07:50 KST 첫 실행 전까지 1~6단계를 끝내야 한다. 그날부터 PC 수집기가 표를 못 보낸다.

---

## 1단계. Playwright + Chromium 설치 (한 번만)

SSH 창에 한 덩어리로 붙여넣는다.

```bash
set -e
free -m
sudo pip3 install playwright
sudo mkdir -p /opt/ms-playwright
sudo PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright python3 -m playwright install --with-deps --only-shell chromium
sudo chmod -R a+rX /opt/ms-playwright
python3 -c "import playwright, importlib.metadata as m; print('playwright', m.version('playwright'))"
ls /opt/ms-playwright
df -h / | tail -1
```

- `--only-shell`은 화면 없는 가벼운 Chromium(headless shell)만 설치한다. 디스크는 약 200~300MB를 쓴다.
- 이 옵션에서 오류가 나면 옵션을 빼고 다시 실행한다. 버전이 낮으면 이 옵션이 없다.

## 2단계. (권장) 스왑 1GB 추가

메모리가 958MB이고 여유가 372MB뿐이다. 로컬에서 시험 페이지 하나를 열었을 때 크롬 프로세스 합계가 최대 약 414MB였다. 공유 메모리가 겹쳐 세어진 값이라 실제로는 이보다 적지만, 실제 팬딩 페이지는 더 무겁다. 봇 본체를 보호하려면 스왑을 두는 게 안전하다.

```bash
if swapon --show | grep -q .; then echo "스왑 이미 있음"; swapon --show; else
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab; fi
free -m
```

서비스 파일에 `MemoryMax=480M`이 들어 있다. 브라우저가 너무 커지면 수집기 서비스만 정리되고, 봇 본체(`bot-office-fanding.service`)는 영향을 받지 않는다.

## 3단계. 파일 배치 + 실행 사용자 맞추기

GitHub staging → main 반영 뒤, 평소 배포 방식으로 아래 파일을 서버에 둔다.

| 저장소 파일 | 서버 위치 |
|---|---|
| `bot_office/fanding_fetch_server.py` | `/opt/bot-office/fanding_fetch_server.py` |
| `systemd/bot-office-fanding-fetch.service` | `/etc/systemd/system/bot-office-fanding-fetch.service` |
| `systemd/bot-office-fanding-fetch.timer` | `/etc/systemd/system/bot-office-fanding-fetch.timer` |

systemd 파일의 저장소 경로는 기존 서비스 파일을 두는 위치에 맞춰 Muse가 정한다.

수집기는 **봇 본체와 같은 사용자**로 돌아야 한다. 그래야 inbox에 남긴 파일을 봇이 지울 수 있다. 아래 명령이 그 사용자를 자동으로 맞춘다.

```bash
U=$(systemctl show -p User --value bot-office-fanding.service); G=$(systemctl show -p Group --value bot-office-fanding.service)
echo "봇 사용자: ${U:-root} / 그룹: ${G:-없음}"
if [ -n "$U" ]; then
  sudo mkdir -p /etc/systemd/system/bot-office-fanding-fetch.service.d
  printf '[Service]\nUser=%s\n%s\n' "$U" "${G:+Group=$G}" | sudo tee /etc/systemd/system/bot-office-fanding-fetch.service.d/user.conf
fi
sudo systemctl daemon-reload
systemd-analyze calendar "*-*-* 07:50:00 Asia/Seoul" | head -3
```

## 4단계. 팬딩 로그인 (한 번만)

- 서버 전용 브라우저 프로필 `/var/lib/bot-office/fanding/server_fetch_profile`에 로그인 상태를 저장한다. PC 프로필은 복사하지 않는다.
- 참고: 새 IP(GCP)에서 로그인하게 된다. 사용자가 계정 의심은 신경 쓰지 않기로 했으므로 진행한다.

```bash
U=$(systemctl show -p User --value bot-office-fanding.service); RUNAS=${U:-root}
sudo -H -u "$RUNAS" env PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright python3 /opt/bot-office/fanding_fetch_server.py login
```

- 화면에 `팬딩 아이디(이메일):`이 나오면 아이디를 입력한다.
- 이어서 `비밀번호`가 나오면 비밀번호를 입력한다. 화면에 안 보이는 게 정상이고, 어디에도 저장되지 않는다.
- `로그인 확인됨: 글 N개 보임`이 나오면 성공이다.
- `로그인 입력칸을 못 찾음`이 나오면, 팬딩 계정이 카카오·구글 같은 소셜 로그인일 수 있다. 이때는 아래 대안을 쓰고, 그래도 안 되면 멈추고 Muse·Claude에게 화면 파일(`server_fetch_debug.png`)을 보여 준다.

**대안: 쿠키로 로그인**

로그인된 브라우저에서 fanding.kr 쿠키를 JSON으로 내보낸 뒤, 그 파일을 서버로 옮긴다(예: `/tmp/fanding_cookies.json`). 옮기는 방법은 보안 방식으로 한다. 파일은 가져오기가 끝나면 자동으로 지워진다.

```bash
U=$(systemctl show -p User --value bot-office-fanding.service); RUNAS=${U:-root}
sudo chown "$RUNAS" /tmp/fanding_cookies.json
sudo -H -u "$RUNAS" env PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright python3 /opt/bot-office/fanding_fetch_server.py login-cookies /tmp/fanding_cookies.json
```

## 5단계. 시험 조회 + 기준 글 기록 (업로드 없음)

```bash
U=$(systemctl show -p User --value bot-office-fanding.service); RUNAS=${U:-root}
F="sudo -H -u $RUNAS env PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright python3 /opt/bot-office/fanding_fetch_server.py"
$F check
$F init
$F status
free -m
```

`check` 결과에서 볼 것:
- `찾은 글 N개, 최신 글 …` 주소가 오늘 아침 가격표 글이어야 한다.
- `이미지: OK …바이트`가 나와야 한다.
- 글을 못 찾으면 `author_links`에 실제 글 주소 모양이 나온다. 이때는 `/etc/bot-office/fanding.json`에 아래처럼 `post_regex`를 맞춘다. 마지막 괄호가 글 번호(숫자)다.
  ```json
  "server_fetch": {"post_regex": "^https?://(?:www\\.)?fanding\\.kr/@laofus/post/(\\d+)"}
  ```
- `json_api`에는 페이지가 부른 JSON 주소가 나온다. 이 결과를 VERIFY의 'JSON API 확인' 항목에 적는다.

`init`은 지금 최신 글(오늘 11-12 아침 표)을 '이미 처리한 글'로 기록한다. 그래서 내일은 이 글보다 새 글만 올린다. **반드시 07:50 전에 실행한다.**

## 6단계. 매일 아침 타이머 켜기

```bash
sudo systemctl enable --now bot-office-fanding-fetch.timer
systemctl list-timers | grep fanding-fetch
```

## 7단계. 내일(11-13) 아침 지켜보기

```bash
journalctl -u bot-office-fanding-fetch --since "today 07:45" --no-pager | tail -40
```

- 정상 흐름: `업로드 완료 … expected=2026-11-12` → `결과: sent`. 그 뒤로는 기존 봇이 판독 → state.json → 텔레그램 흐름을 그대로 처리한다.
- 문제가 생기면 수집기가 inbox note로 비서 봇에 알린다. 로그인 풀림, 1차 실패, 자동 중단이 이에 해당한다.
- 자동으로 중단된 뒤 원인을 고쳤으면, 아래 명령으로 중단을 풀어야 다음 날부터 다시 수집한다. 로그인 풀림으로 멈춘 경우는 `login`이 성공하면 자동으로 풀린다.
  ```bash
  U=$(systemctl show -p User --value bot-office-fanding.service); sudo -H -u "${U:-root}" python3 /opt/bot-office/fanding_fetch_server.py reset
  ```

## 끄는 법 (되돌리기)

```bash
sudo systemctl disable --now bot-office-fanding-fetch.timer
```

수집기는 추가 기능이다. 끄면 원래대로 PC 수집기만 남고, 기존 코드는 바뀐 것이 없다.
