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

class CheckPixelNode(NodeHandler):
    @property
    def node_type(self): return "check_pixel"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        x = int(props.get('x', 0))
        y = int(props.get('y', 0))
        expected_hex = props.get('expected_color', '#FFFFFF').lstrip('#')
        tolerance = int(props.get('tolerance', 10))
        
        # Convert hex to RGB
        try:
            expected_rgb = tuple(int(expected_hex[i:i+2], 16) for i in (0, 2, 4))
        except:
            log_message(f"Invalid Hex color: {expected_hex}")
            return node.get('next_not_found')

        log_message(f"Checking pixel at ({x}, {y}) for color #{expected_hex}")
        actual_bgr = context.bot.get_pixel_color(x, y)
        
        if actual_bgr:
            # actual_bgr is (B, G, R)
            actual_rgb = (actual_bgr[2], actual_bgr[1], actual_bgr[0])
            log_message(f"Actual color: RGB{actual_rgb}")
            
            # Compare with tolerance
            diff = sum(abs(a - b) for a, b in zip(actual_rgb, expected_rgb))
            if diff <= tolerance * 3: # Simple Manhattan distance check
                log_message("Color matches!")
                return node.get('next_found')
            else:
                log_message(f"Color mismatch (Diff: {diff})")
                return node.get('next_not_found')
        else:
            log_message("Failed to get pixel color.")
            return node.get('next_not_found')

class FindMultiImagesNode(NodeHandler):
    @property
    def node_type(self): return "find_multi_images"
    
    def execute(self, node: Dict[str, Any], context: RuntimeContext) -> Optional[str]:
        props = node.get('properties', {})
        node_id = node['id']
        templates_str = props.get('templates', '')
        algorithm = props.get('algorithm', 'auto')
        
        # Parse templates: support comma-separated or newline-separated
        templates = [t.strip() for t in templates_str.replace('\n', ',').split(',') if t.strip()]
        
        if not templates:
            log_message("No templates specified for multi-image search.")
            return node.get('next_not_found')
        
        log_message(f"Searching {len(templates)} images: {', '.join(templates)}")
        
        for template in templates:
            log_message(f"Checking: {template} (Algo: {algorithm})")
            center = context.bot.find_and_click(template, click_target=False, method=algorithm, timeout=1)
            
            if center:
                log_message(f"✓ Found: {template} at ({center[0]}, {center[1]})")
                context.set_output(node_id, 2, center[0])  # Slot 2: X
                context.set_output(node_id, 3, center[1])  # Slot 3: Y
                return node.get('next_found')
        
        log_message(f"✗ None of {len(templates)} images found.")
        return node.get('next_not_found')
