import time
from typing import List, Dict, Any, Type, Optional
from context import RuntimeContext
from nodes.base import NodeHandler
from shared import log_message
import shared  # For checking is_running globally

# Import all nodes to register them
from nodes.basic import StartNode, ClickNode, SwipeNode, WaitNode, ClearAppsNode, HomeNode
from nodes.vision import FindImageNode
from nodes.logic import LoopNode, LoopBreakNode, ScriptNode
from nodes.discord_nodes import DiscordSendNode, DiscordWaitNode, DiscordScreenshotNode

class NodeRegistry:
    _handlers: Dict[str, NodeHandler] = {}

    @classmethod
    def register(cls, handler_cls: Type[NodeHandler]):
        handler = handler_cls()
        cls._handlers[handler.node_type] = handler
        # Also register normalized names if needed, or handle in get()
        
    @classmethod
    def get(cls, node_type: str) -> NodeHandler:
        # types might come in as 'bot/click' or 'click'
        # The ScriptService normalizes them to 'click'.
        # But just in case:
        if node_type.startswith('bot/'):
            node_type = node_type.replace('bot/', '')
        
        return cls._handlers.get(node_type)

    @classmethod
    def initialize_defaults(cls):
        cls.register(StartNode)
        cls.register(ClickNode)
        cls.register(SwipeNode)
        cls.register(WaitNode)
        cls.register(FindImageNode)
        cls.register(LoopNode)
        cls.register(LoopBreakNode)
        cls.register(ScriptNode)
        cls.register(DiscordSendNode)
        cls.register(DiscordWaitNode)
        cls.register(DiscordScreenshotNode)
        cls.register(ClearAppsNode)
        cls.register(HomeNode)

class GraphExecutor:
    def __init__(self):
        NodeRegistry.initialize_defaults()

    def execute(self, nodes_list: List[Dict[str, Any]], context: RuntimeContext, start_node_id: Optional[str] = None) -> bool:
        """
        Execute a flow graph.
        Returns True if finished naturally, False if stopped/error.
        """
        if context.recursion_depth > 10:
            log_message("Error: Max recursion depth (10) reached.")
            return False

        # Check GLOBAL is_running for immediate stop
        if not shared.is_running:
            return False

        # Scope Management: Temporarily override node_map for this recursion level
        old_map = context.node_map
        local_map = { node['id']: node for node in nodes_list }
        context.node_map = local_map
        
        # Inject self into context so ScriptNode can recurse
        context.executor = self

        try:
            current_node = None
            if start_node_id:
                current_node = local_map.get(start_node_id)
                if not current_node:
                    log_message(f"Error: Start node {start_node_id} not found.")
                    return False
            else:
                # Find Start Node (or use first 'start' type)
                current_node = next((n for n in nodes_list if n.get('type') in ('start', 'bot/start')), None)
                
                if not current_node:
                    log_message("Warning: No Start node found in current flow.")
                    return False

            # Use shared.is_running for loop check to respect stop command
            while current_node and shared.is_running:
                node_id = current_node['id']
                node_type = current_node.get('type', '')
                
                handler = NodeRegistry.get(node_type)
                
                if handler:
                    try:
                        next_id = handler.execute(current_node, context)
                    except Exception as e:
                        log_message(f"Error executing node {node_type} ({node_id}): {e}")
                        return False
                else:
                    log_message(f"Error: Unknown node type '{node_type}'")
                    next_id = current_node.get('next') # Try to skip?

                # Loop Break / Return Logic
                # If next_id is None, natural end of branch.
                if next_id is None:
                    # Check loop stack for Auto-Return
                    # Loops in THIS scope or outer scope?
                    # Engine.py Logic: "If end of branch and inside a loop, go back to loop start"
                    # But which loop? The one at top of stack.
                    if context.loop_stack:
                        loop_id = context.loop_stack[-1]
                        # We must check if this loop_id belongs to CURRENT map (local loop) or outer?
                        # If we are in sub-script, and loop_stack has ID from Main.
                        # `local_map` won't have it.
                        # If we auto-return to a Main loop node, we set `current_node` to something NOT in `local_map`.
                        # Then next iteration `local_map.get(next_id)` returns None.
                        # Then loop terminates?
                        
                        # Ideally, sub-script runs until it has no next node.
                        # Then it returns to Main.
                        # Main continues.
                        
                        # Issue: If we are inside a loop in Sub-script using `loop` node.
                        # LoopStack has [SubLoopID].
                        # `end of branch` -> next_id = SubLoopID.
                        # It works.
                        
                        # What if we are in Main loop, call Sub, Sub finishes.
                        # Sub returns None.
                        # GraphExecutor returns True.
                        # Main NodeHandler (ScriptNode) gets control back.
                        # It returns `next` of ScriptNode.
                        # So we don't need to handle outer loop return HERE.
                        # We only handle return to loops defined in THIS graph.
                        
                        if loop_id in local_map:
                             log_message(f"Auto-Loop Return to {loop_id}")
                             next_id = loop_id
                        else:
                             # Reached end of sub-script, but stack implies we are in a loop from caller?
                             # Or we just finished this graph.
                             pass
                
                if next_id:
                    current_node = local_map.get(next_id)
                    if not current_node:
                         # Ensure we aren't jumping to a node in outer scope? 
                         # (Should be impossible unless handler returns ID from outer)
                         # Or simply bad ID.
                         # log_message(f"Next node {next_id} not found in current scope.")
                         pass
                else:
                    current_node = None
                    
                time.sleep(0.01) # Small yield

            return True

        finally:
            # Restore scope
            context.node_map = old_map
