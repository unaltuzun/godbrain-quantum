# GODBRAIN Nano Core (Ultra-Low Latency Engine)

Bu klasör, GODBRAIN için tasarlanan ultra-low latency C çekirdeğinin iskeletidir.

Hedefler:
- Lock-free ring buffer (SPSC)
- Branchless risk kontrolü
- rdtsc ile latency ölçümü
- SIMD placeholder (ileride gerçek veri düzeniyle)

Derleme:
  cd nano_core
  make
  ./nano_core_demo
