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
