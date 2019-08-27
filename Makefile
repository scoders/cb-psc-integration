ALL_PY_SRCS := $(shell find src -name '*.py') app.py

SUPERVISORD_LOGSINK = /dev/null
ifeq ($(ENVIRONMENT),development)
	SUPERVISORD_LOGSINK = /dev/stderr
endif

export SUPERVISORD_LOGSINK

.PHONY: all
all:
	@echo "Run my targets individually!"

.PHONY: prep
prep:
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
