CARGO ?= cargo
BIN_NAME ?= deejay

TARGET ?= x86_64-unknown-linux-gnu
DIST_DIR ?= dist

all: build-linux

build-linux:
TARGET=x86_64-unknown-linux-gnu $(CARGO) build --release --target x86_64-unknown-linux-gnu

build-macos:
TARGET=x86_64-apple-darwin $(CARGO) build --release --target x86_64-apple-darwin

build-windows:
TARGET=x86_64-pc-windows-gnu $(CARGO) build --release --target x86_64-pc-windows-gnu

bundle: build-linux
TARGET=$(TARGET) BIN_NAME=$(BIN_NAME) DIST_DIR=$(DIST_DIR) scripts/bundle.sh $(TARGET)

fmt:
$(CARGO) fmt

test:
$(CARGO) test

clean:
$(CARGO) clean

dist-clean:
rm -rf $(DIST_DIR)
