ALL_PY_SRCS := $(shell find src -name '*.py') app.py

.PHONY: all
all:
	@echo "Run my targets individually!"

prep: logs
	mkdir -p logs/

.PHONY: serve
serve: prep
	supervisord -n

.PHONY: clean
clean:
	rm -f dump.rdb logs/*
	rm -rf docs/build/*
	rm -f /tmp/psc.db

.PHONY: docs
docs:
	PYTHONPATH=src/ sphinx-build -b html docs/source/ docs/build/html

.PHONY: lint
lint:
	black $(ALL_PY_SRCS)
	isort $(ALL_PY_SRCS)
	git diff --exit-code
