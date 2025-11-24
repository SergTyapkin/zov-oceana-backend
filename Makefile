-include .env


info:
	@echo "------------------------------------------------------------------------------------------------------" && \
	echo "| You runs make command with no targets. You must specify target after 'make'. For example 'make all' |" && \
	echo "| Available targets: all; update; build; run; down; logs; backup; make-dirs; setup-ci; install-docker-if-not-exists; set-docker-not-sudo; setup-env-file." && \
	echo "------------------------------------------------------------------------------------------------------"

build:
	@echo "[Make]: Running 'build' target in Makefile..." && \
    bash ./docker-deploy/scripts/build.sh
run:
	@echo "[Make]: Running 'run' target in Makefile..." && \
	bash ./docker-deploy/scripts/run.sh
down:
	@echo "[Make]: Running 'down' target in Makefile..." && \
    bash ./docker-deploy/scripts/down.sh
logs:
	@echo "[Make]: Running 'logs' target in Makefile..." && \
    bash ./docker-deploy/scripts/logs.sh


update:
	@echo "[Make]: Running 'update' target in Makefile..." && \
    bash ./docker-deploy/scripts/update-deploy.sh

setup-ci:
	@echo "[Make]: Running 'setup-ci' target in Makefile..." && \
    bash ./docker-deploy/scripts/setup-ci.sh
	bash ./docker-deploy/scripts/show-variables-to-github-ci.sh

install-docker-if-not-exists:
	@echo "[Make]: Running 'install-docker-if-not-exists' target in Makefile..." && \
    bash ./docker-deploy/scripts/install-docker-if-not-exists.sh

set-docker-not-sudo:
	@echo "[Make]: Running 'set-docker-not-sudo' target in Makefile..." && \
    bash ./docker-deploy/scripts/set-docker-not-sudo.sh

make-dirs:
	@mkdir -p ./docker-deploy/images_data && \
	mkdir -p ./docker-deploy/pg_data

setup-env-file:
	@echo "[Make]: Running 'setup-env-file' target in Makefile..." && \
    bash ./docker-deploy/scripts/setup-env-file.sh

backup:
	@echo "[Make]: Running 'backup' target in Makefile..." && \
	bash ./docker-deploy/scripts/backup.sh

all:
	@echo "[Make]: Running 'all' target in Makefile..." && \
	make setup-env-file
	make make-dirs
	make setup-ci
	make update
