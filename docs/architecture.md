# Architecture Overview

## Principles of Architecture
- **Modular processes**  
  The system is split into small, stateless Python modules. Each module can be swapped or replaced without impacting others.  
- **Event-driven communication**  
  Modules communicate only via local [ZeroMQ](https://zeromq.org/) PUB/SUB events. No shared state.  
- **Orchestration with Supervisor**  
  [supervisord](http://supervisord.org/) manages lifecycle, restarts, and logging of all processes. A lightweight web UI is available for monitoring.  
- **Replaceability & simplicity**  
  Modules are designed to be plug-and-play: single-purpose, self-contained, and without external dependencies beyond the shared virtualenv.  
- **Local-first**  
  Runs entirely on a Raspberry Pi, no external infrastructure required.

## Focus
- **Flexibility**: Each module can be replaced with a different implementation.
- **Resilience**: Each process runs independently. Failures are contained, supervisor auto-restarts modules.  
- **Maintainability**: Clear contracts between modules (events + topics). Minimal coupling.  
- **Lightweight footprint**: Optimized for Raspberry Pi hardware. Avoids heavy brokers/databases.  
- **Transparency**: Logs for each module go to separate files for easier debugging and audit.  

## Known Issues / Limitations
- **Message delivery**: ZeroMQ PUB/SUB is best-effort. Messages can be dropped under backpressure or if a subscriber is late to join.  
- **No persistence**: Events are not stored or replayed. If a module is offline, it misses messages.  
- **Observability gaps**: Logs are split per file and stored locally (risk of SD card wear). No centralized metrics or tracing yet.  
- **Supervisor limitations**: supervisord is not a full init system. It’s run under systemd but lacks per-process resource isolation.  