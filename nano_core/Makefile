CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -march=native
INCLUDE = -Iinclude

SRC = src/main.c src/orderbook_simd.c
OBJ = $(SRC:.c=.o)
TARGET = nano_core_demo

all: $(TARGET)

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) $(INCLUDE) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all clean
