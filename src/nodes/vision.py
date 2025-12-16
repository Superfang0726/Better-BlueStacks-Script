from typing import Dict, Any, Optional
from context import RuntimeContext
from nodes.base import NodeHandler
from shared import log_message

class FindImageNode(NodeHandler):
    @property
    def node_type(self): return "find_image"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        node_id = node['id']
        template = props.get('template', '')
        algorithm = props.get('algorithm', 'auto')
        
        if template:
            log_message(f"Checking: {template} (Algo: {algorithm})")
            center = context.bot.find_and_click(template, click_target=False, method=algorithm)
            
            if center:
                log_message(f"Found {template} at {center}")
                context.set_output(node_id, 2, center[0]) # Slot 2: X
                context.set_output(node_id, 3, center[1]) # Slot 3: Y
                
                return node.get('next_found')
            else:
                log_message(f"Not found: {template}")
                return node.get('next_not_found')
        else:
            return node.get('next_not_found')
