export daemon_name="han4384tubot"
export BITHUMB_ACCESS_KEY="087c3dcb1d1c58321a841784a1368ea0220a494d12e6c8"
export BITHUMB_SECRET_KEY="MmNlYzBiMjAzZTFlMWEwNTM2YzkxNTE3NWIzMTY5ZjQxMThhYWEzNDhkYTUyYzAzNGI0YTEzZWJjM2ZjMw=="
export TELEGRAM_BOT_TOKEN="8675822514:AAH7G51_fpRv6iQOLFwttFerS6eJI4-noPw"
export TELEGRAM_CHAT_ID="6979340028"
alias bot_save='cp /home/gieokkim/bithumb_laoeo_bot/main.py /home/gieokkim/bithumb_laoeo_bot/main.bak && cp /home/gieokkim/toss_dca_bot/main.py /home/gieokkim/toss_dca_bot/main.bak && echo "✅ [백업 완료] 두 봇의 현재 정상 상태가 안전하게 저장되었습니다!"'
alias bot_undo='cp /home/gieokkim/bithumb_laoeo_bot/main.bak /home/gieokkim/bithumb_laoeo_bot/main.py && cp /home/gieokkim/toss_dca_bot/main.bak /home/gieokkim/toss_dca_bot/main.py && sudo systemctl restart bithumb_bot toss_dca && echo "🔄 [복구 완료] 이전 정상 버전으로 즉시 되돌렸습니다!"'
source ~/bot_guard.sh
