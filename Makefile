.PHONY: start stop status logs

PID_FILE:=/tmp/veripay_v2.pid
LOG_FILE:=/tmp/veripay_v2.log

start:
	@pkill -f "python3 .*bot_v2/main.py" || true
	@echo "Starting bot_v2..."
	@env PYTHONPATH="$(PWD)" BOT_TOKEN="$(BOT_TOKEN)" SUPER_ADMIN_ID="$(SUPER_ADMIN_ID)" DATABASE_URL="$(DATABASE_URL)" GOOGLE_APPLICATION_CREDENTIALS="$(GOOGLE_APPLICATION_CREDENTIALS)" LEGACY_UI="1" USE_WEBHOOK="$(USE_WEBHOOK)" PUBLIC_URL="$(PUBLIC_URL)" PORT="$(PORT)" WEBHOOK_PATH="$(WEBHOOK_PATH)" nohup python3 bot_v2/main.py > $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE)
	@sleep 1; tail -n 30 $(LOG_FILE) | cat

stop:
	@if [ -f $(PID_FILE) ]; then kill `cat $(PID_FILE)` || true; rm -f $(PID_FILE); fi
	@pkill -f "python3 .*bot_v2/main.py" || true

status:
	@ps aux | grep -E "python3 .*bot_v2/main.py" | grep -v grep || true

logs:
	@tail -n 100 -f $(LOG_FILE)
