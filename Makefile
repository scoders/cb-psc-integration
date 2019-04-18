.PHONY: all
all:
	@echo "Run my targets individually!"

.PHONY: serve
serve:
	supervisord -n

.PHONY: clean
clean:
	rm -f dump.rdb logs/*
