from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import threading

@dataclass
class RuntimeContext:
    """
    Holds the state for a single script execution.
    取代 shared.py 的角色，讓每次執行都有獨立的 Context
    """
    bot: Any  # BlueStacksBot instance
    discord_client: Any = None
    discord_loop: Any = None
    executor: Any = None
    is_running: bool = True
    
    # Execution State
    node_map: Dict[str, Any] = field(default_factory=dict)
    
    # Loop Management
    loop_states: Dict[str, int] = field(default_factory=dict) # {node_id: counter}
    loop_stack: List[str] = field(default_factory=list)       # [node_id, node_id]
    
    # Data Flow (Outputs from nodes)
    # { node_id: { slot_index: value } }
    outputs: Dict[str, Dict[int, Any]] = field(default_factory=dict)
    
    # Wait Events (for Discord waiting)
    wait_events: Dict[str, threading.Event] = field(default_factory=dict)
    
    # Recursion Control
    recursion_depth: int = 0
    
    # Script Path (for local image resolution)
    script_path: str = None
    
    def stop(self):
        self.is_running = False
        # Set all wait events to unblock threads
        for evt in self.wait_events.values():
            evt.set()

    def get_output(self, node_id: str, slot: int) -> Any:
        return self.outputs.get(node_id, {}).get(slot)

    def set_output(self, node_id: str, slot: int, value: Any):
        if node_id not in self.outputs:
            self.outputs[node_id] = {}
        self.outputs[node_id][slot] = value
