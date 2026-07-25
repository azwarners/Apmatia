# Runtime Telemetry

A stable bundled module for collecting, parsing, and summarizing telemetry from
the model runtimes used by Apmatia.

The initial telemetry adapter understands llama.cpp server logs. It exposes
structured timing, task, slot, cache, request, and runtime status data while
keeping runtime-specific parsing out of Apmatia's shared library layer.
