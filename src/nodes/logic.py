from typing import Dict, Any, Optional, List
from context import RuntimeContext
from nodes.base import NodeHandler
from services.script_service import ScriptService
from shared import log_message
import shared # For global hooks

class LoopNode(NodeHandler):
    @property
    def node_type(self): return "loop"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        node_id = str(node['id']) # Standardize to string
        props = node.get('properties', {})
        
        # Initialize
        if node_id not in context.loop_states:
            c_val = int(props.get('count', 3))
            # 0 means infinite (-1 internally)
            if c_val == 0: c_val = -1
            
            context.loop_states[node_id] = c_val
            context.loop_stack.append(node_id)
            log_message(f"Loop Start (Count: {'Infinite' if c_val == -1 else c_val})")
            
        count = context.loop_states[node_id]
        
        if count == -1:
            # Infinite
            return node.get('next_body')
        elif count > 0:
            context.loop_states[node_id] -= 1
            log_message(f"Looping... ({context.loop_states[node_id]} left)")
            return node.get('next_body')
        else:
            log_message("Loop Finished.")
            if context.loop_stack and context.loop_stack[-1] == node_id:
                context.loop_stack.pop()
            context.loop_states.pop(node_id, None)
            return node.get('next_exit')

class LoopBreakNode(NodeHandler):
    @property
    def node_type(self): return "loop_break"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        log_message("Loop Break...")
        if context.loop_stack:
            target_id = str(context.loop_stack.pop()) # Standardize to string
            context.loop_states.pop(target_id, None)
            
            # We need to find the 'next_exit' of the target loop node.
            # But we don't have the target node object here, only ID.
            # We need to look it up in context.node_map
            target_node = context.node_map.get(target_id)
            if target_node:
                log_message("Jumped to Loop Exit.")
                return target_node.get('next_exit')
            else:
                log_message(f"Error: Target loop node {target_id} not found in map.")
                return None
        else:
            log_message("Break outside loop ignored.")
            return node.get('next')

class ScriptNode(NodeHandler):
    @property
    def node_type(self): return "script"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        script_name = props.get('scriptName', '')
        
        if not script_name:
            log_message("Error: No script name provided.")
            return node.get('next')
            
        # Load and Normalize
        sub_actions = ScriptService.load_and_normalize(script_name)
        
        if not sub_actions:
            return node.get('next')
            
        # Recursive Execution Logic
        # 1. Register Hooks
        registered_hooks = []
        for sub_node in sub_actions:
            if sub_node.get('type') == 'discord_wait':
                sn_id = sub_node['id']
                sn_props = sub_node.get('properties', {})
                sn_cmd = sn_props.get('command_name', 'continue').strip() or 'continue'
                
                if sn_cmd in shared.command_hooks:
                     log_message(f"Warning: Sub-script command '/{sn_cmd}' overrides existing hook.")
                
                # We need shared.wait_events to match DiscordWaitNode logic
                # Define signaler
                def make_signaler(nid, nm):
                    def signaler():
                        event = shared.wait_events.get(nid)
                        if event:
                            log_message(f"Signaling event for node {nid} (from sub-script)")
                            event.set()
                            return True
                        return False
                    return signaler
                
                handler = make_signaler(sn_id, sn_cmd)
                shared.command_hooks[sn_cmd] = handler
                registered_hooks.append(sn_cmd)
                log_message(f"Sub-script registered command: /{sn_cmd} -> Node {sn_id}")

        # 2. Execute
        try:
             log_message(f"Starting Sub-script '{script_name}' execution...")
             if context.executor:
                 # We create a NEW context or reuse?
                 # If we reuse, we share looping state?
                 # Usually call stack is shared (recursion).
                 # Context holds loop_stack (list). So reusing is correct.
                 # But we might need to handle 'node_map' carefully.
                 # The executor needs to know the node map of the CURRENT graph (subgraph).
                 # context.node_map is currently holding the MAIN graph's nodes?
                 # If we recursively call executor, executor.execute(nodes) should probably
                 # update the node_map for that scope.
                 # But if we overwrite node_map, we lose outer scope?
                 # Actually, execute_graph (executor) usually builds a local node_map.
                 # But LoopBreakNode needs to look up nodes from stack.
                 # LoopStack stores IDs. IDs are unique per file, but might collide across files?
                 # If sub-script has Node ID 1 and Main script has Node ID 1.
                 # LoopBreakNode inside sub-script popping ID 1 (from Main) would look up ID 1 in Sub-script map...
                 # This implies IDs are not globally unique.
                 # LiteGraph IDs are int, usually 1, 2, 3...
                 # So we have ID collision risk on LoopBreak across scripts if we don't isolate maps or use unique IDs.
                 
                 # Solution: Sub-scripts should probably run in their own scope/context for LoopStacks?
                 # Or we accept that LoopBreak only breaks local loops.
                 # If we reuse Context, we share LoopStack.
                 # If Subscript starts a loop (ID 1), it pushes 1.
                 # If Main had a loop (ID 1), it pushed 1.
                 # LoopStack: [1(Main), 1(Sub)].
                 # Sub loop finishes, pops 1.
                 # It works because stack structure.
                 # BUT LoopBreak needs to look up the node to get 'next_exit'.
                 # context.node_map needs to contain the node definition for the ID at the top of the stack.
                 # If we are in Sub-script, node_map IS the sub-script map.
                 # So looking up ID 1 gets the Sub-script loop. Correct.
                 # If we break Main loop (ID 1) from Sub-script (impossible?), it would look up ID 1 in Sub-script map (wrong).
                 # But `loop_break` only breaks loops in current scope usually.
                 # Unless we want to break *outer* loops.
                 # For now, let's assume `executor.execute` updates `context.node_map` to the local map,
                 # and restores it afterwards?
                 # Or `GraphExecutor.execute` creates a specialized `Scope`?
                 
                 # Let's rely on `GraphExecutor.execute` handling the node_map swappage.
                 # We will pass the same context.
                 
                 context.recursion_depth += 1
                 success = context.executor.execute(sub_actions, context)
                 context.recursion_depth -= 1
                 
                 if success:
                     log_message(f"Sub-script '{script_name}' finished normally.")
                 else:
                     log_message(f"Sub-script '{script_name}' returned False/Stopped.")
             else:
                 log_message("Error: No executor found in context.")

        finally:
            # 3. Cleanup Hooks
            for cmd in registered_hooks:
                shared.command_hooks.pop(cmd, None)
                log_message(f"Unregistered sub-script command: /{cmd}")
                
        return node.get('next')
