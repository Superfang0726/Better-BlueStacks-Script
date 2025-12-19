import time
from typing import List, Dict, Any, Type, Optional
from context import RuntimeContext
from nodes.base import NodeHandler
from shared import log_message
import shared  # For checking is_running globally

# Import all nodes to register them
from nodes.basic import StartNode, ClickNode, SwipeNode, WaitNode, ClearAppsNode, HomeNode
from nodes.vision import FindImageNode, CheckPixelNode
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
        cls.register(CheckPixelNode)
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

        # Scope Management: Isolate state for this recursion level
        old_map = context.node_map
        old_loop_states = context.loop_states
        old_outputs = context.outputs
        
        context.node_map = { str(node['id']): node for node in nodes_list }
        context.loop_states = {} # Isolated loop counters
        context.outputs = {}     # Isolated data flow
        
        # Track which loops were started in THIS SCOPE
        local_loops_at_start = len(context.loop_stack)
        
        # Inject self into context so ScriptNode can recurse
        context.executor = self

        try:
            current_node = None
            if start_node_id:
                current_node = local_map.get(str(start_node_id))
                if not current_node:
                    log_message(f"Error: Start node {start_node_id} not found.")
                    return False
            else:
                # Find Start Node (or use first 'start' type)
                current_node = next((n for n in nodes_list if n.get('type') in ('start', 'bot/start')), None)
                
                if not current_node:
                    log_message("Warning: No Start node found in current flow.")
                    return False

            while current_node and shared.is_running:
                node_id = str(current_node['id'])
                raw_type = current_node.get('type', '')
                node_type = raw_type.replace('bot/', '')
                
                log_message(f"--- Executing: {node_type} (ID: {node_id}) ---")
                
                handler = NodeRegistry.get(node_type)
                
                if handler:
                    # Debug: log key fields for branching nodes
                    if node_type in ['find_image', 'check_pixel']:
                         log_message(f"  > Branch Keys: next_found={current_node.get('next_found')}, next_not_found={current_node.get('next_not_found')}")
                    
                    try:
                        next_id = handler.execute(current_node, context)
                    except Exception as e:
                        log_message(f"Error executing node {node_type} ({node_id}): {e}")
                        return False
                else:
                    log_message(f"Error: Unknown node type '{node_type}'")
                    next_id = current_node.get('next')

                # Loop Break / Return Logic
                if next_id is None:
                    if len(context.loop_stack) > local_loops_at_start:
                        loop_id = context.loop_stack[-1]
                        if str(loop_id) in context.node_map:
                             log_message(f"Auto-Loop Return to {loop_id}")
                             next_id = loop_id
                
                if next_id is not None:
                    current_node = context.node_map.get(str(next_id))
                else:
                    current_node = None
                    
                time.sleep(0.01) # Small yield

            return True

        finally:
            # Restore scope
            context.node_map = old_map
            context.loop_states = old_loop_states
            context.outputs = old_outputs
            
            # Clean up loops that were started in this scope but never finished
            while len(context.loop_stack) > local_loops_at_start:
                context.loop_stack.pop()
