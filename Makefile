.PHONY: all
all:
	@echo "Run my targets individually!"

.PHONY: workers
workers:
	supervisord -n

.PHONY: app
app:
	python3 app.py
