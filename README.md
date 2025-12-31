# Tailor - Multi-Window AI Workspace

A modular AI framework that lets you stitch together models and tools into an assistant that fits you perfectly.

## Features

- **Multi-Window Vaults**: Open multiple independent vaults simultaneously
- **Isolated Sidecars**: Each vault runs its own Python process for complete isolation
- **Plugin System**: Create and share custom plugins with the community
- **Bi-Directional Events**: Plugins can emit events back to the UI
- **Portable Vaults**: Vault folders are self-contained and can be shared easily

## Architecture

- **Rust/Tauri**: Window management, process orchestration, event routing
- **Python Sidecar**: LangGraph execution, plugin loading, memory management
- **WebSocket**: Bi-directional JSON-RPC communication

## Prerequisites

- **Rust**: Install from [rustup.rs](https://rustup.rs/)
- **Node.js**: v18+ for frontend build
- **Python**: 3.10+ for sidecar execution

## Installation

### 1. Install Rust (Required)

```powershell
# Windows - Run in PowerShell
winget install --id Rustlang.Rustup
```

After installation, restart your terminal.

### 2. Install Dependencies

```powershell
# Install Node dependencies
npm install

# Install Python sidecar dependencies
cd sidecar
pip install -r requirements.txt
cd ..
```

## Development

### Run in Development Mode

```powershell
# Start Tauri development server
npm run tauri:dev
```

This will:
1. Start Vite dev server for frontend
2. Compile Rust backend
3. Launch the Tauri application

### Testing the Example Vault

1. Click "Open Vault" in the app
2. Select the `example-vault` directory
3. Watch the console for sidecar initialization
4. Observe the example plugin emit events every 15 seconds

## Project Structure

```
tailor/
├── src/                          # Frontend code
│   └── index.html
├── src-tauri/                    # Rust backend
│   ├── src/
│   │   ├── main.rs               # Entry point
│   │   ├── window_manager.rs    # Window lifecycle
│   │   ├── sidecar_manager.rs   # Process orchestration
│   │   ├── dependency_checker.rs # Auto pip install
│   │   ├── ipc_router.rs        # Command routing
│   │   └── event_bus.rs         # Event routing
│   ├── Cargo.toml
│   └── tauri.conf.json
├── sidecar/                      # Python sidecar
│   ├── main.py                   # Entry point
│   ├── event_emitter.py          # Event API
│   ├── websocket_server.py       # WebSocket server
│   ├── vault_brain.py            # LangGraph orchestrator
│   └── requirements.txt
└── example-vault/                # Example vault
    ├── .vault.json
    └── plugins/
        ├── example_plugin.py
        └── requirements.txt
```

## Creating a Vault

A vault is a self-contained directory with the following structure:

```
my-vault/
├── .vault.json              # Vault metadata
├── plugins/                 # Python plugins
│   ├── my_plugin.py
│   └── requirements.txt
├── lib/                     # Auto-managed dependencies
├── .memory/                 # Conversation history
└── config/                  # User preferences
```

### Example Plugin

```python
class Plugin:
    def __init__(self, emitter):
        """Initialize with EventEmitter."""
        self.emitter = emitter
        self.name = "my_plugin"
    
    async def on_tick(self, emitter):
        """Called every 5 seconds."""
        emitter.notify("Tick from my plugin!", severity="info")
    
    async def custom_action(self, **kwargs):
        """Custom action callable via execute_command."""
        emitter.notify("Action executed!", severity="success")
        return {"status": "ok"}
```

## Event Emission

Plugins can emit events using the EventEmitter API:

```python
# Window-scoped (default)
emitter.notify("Task complete!")

# Progress updates
emitter.progress(75, "Processing...")

# State updates
emitter.update_state("task_count", 42)

# Global events (all windows)
emitter.global_event("SYSTEM_ALERT", {"msg": "Important!"})

# Vault-scoped (all windows with same vault)
emitter.vault_event("STATE_CHANGED", {"key": "value"})
```

## Building for Production

```powershell
# Build application bundle
npm run tauri:build
```

The compiled app will be in `src-tauri/target/release/bundle/`.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT

## Documentation

For detailed architecture documentation, see:
- Architecture Overview: `.gemini/antigravity/brain/.../architecture_overview.md`
- Implementation Plan: `.gemini/antigravity/brain/.../implementation_plan.md`
- Event Bus Design: `.gemini/antigravity/brain/.../event_bus_design.md`