"""
Tailor Python Sidecar Entry Point

This module initializes a vault-specific Python sidecar process with:
- Bi-directional WebSocket communication
- Event emission capabilities for plugins
- LangGraph orchestration
- Vault-specific plugin loading
"""

import argparse
import asyncio
import sys
from pathlib import Path

from websocket_server import WebSocketServer
from event_emitter import EventEmitter
from vault_brain import VaultBrain


async def run_servers(ws_server: WebSocketServer, brain: VaultBrain):
    """Run WebSocket server and tick loop concurrently."""
    await asyncio.gather(
        ws_server.start(),
        brain.tick_loop(),
    )


def main():
    """Main entry point for the sidecar process."""
    parser = argparse.ArgumentParser(description="Tailor Python Sidecar")
    parser.add_argument("--vault", required=True, help="Path to vault directory")
    parser.add_argument("--ws-port", type=int, required=True, help="WebSocket port")
    args = parser.parse_args()

    vault_path = Path(args.vault)
    
    # Validate vault exists
    if not vault_path.exists():
        print(f"Error: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Initializing sidecar for vault: {vault_path}")
    print(f"WebSocket port: {args.ws_port}")

    # Add vault's lib directory to Python path for isolated dependencies
    lib_path = vault_path / "lib"
    if lib_path.exists():
        sys.path.insert(0, str(lib_path))
        print(f"Added to PYTHONPATH: {lib_path}")

    try:
        # Initialize WebSocket server
        ws_server = WebSocketServer(port=args.ws_port)
        
        # Create event emitter for plugins
        emitter = EventEmitter(websocket_server=ws_server)
        
        # Initialize vault brain
        brain = VaultBrain(vault_path=vault_path, emitter=emitter, ws_server=ws_server)
        
        print("Sidecar initialized successfully")
        print("Starting WebSocket server and tick loop...")
        
        # Run both servers
        asyncio.run(run_servers(ws_server, brain))
        
    except KeyboardInterrupt:
        print("\nSidecar shutting down...")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
