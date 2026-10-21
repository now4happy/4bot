bot_save() {
  cp /home/gieokkim/bithumb_laoeo_bot/*.py /home/gieokkim/bithumb_laoeo_bot/backup/ 2>/dev/null
  cp /home/gieokkim/toss_dca_bot/*.py /home/gieokkim/toss_dca_bot/backup/ 2>/dev/null
  echo "✅ [백업 완료] 두 봇의 모든 모듈이 안전 금고(backup)에 저장되었습니다!"
}
bot_undo() {
  cp /home/gieokkim/bithumb_laoeo_bot/backup/*.py /home/gieokkim/bithumb_laoeo_bot/ 2>/dev/null
  cp /home/gieokkim/toss_dca_bot/backup/*.py /home/gieokkim/toss_dca_bot/ 2>/dev/null
  sudo systemctl restart bithumb_bot toss_dca
  echo "🔄 [1초 복구 완료] 직전 정상 상태로 완벽히 되돌렸습니다!"
}
