"""
Image utility functions for script folder management.
"""
import os
import shutil
from typing import List, Set
from shared import log_message


def extract_image_paths_from_script(script_data: dict) -> Set[str]:
    """
    Parse all find_image / find_multi_images nodes and extract template paths.
    
    Args:
        script_data: Raw LiteGraph JSON data with 'nodes' list
        
    Returns:
        Set of image paths (relative to global images/ folder)
    """
    images = set()
    nodes = script_data.get('nodes', [])
    
    for node in nodes:
        node_type = node.get('type', '').replace('bot/', '')
        properties = node.get('properties', {})
        
        if node_type == 'find_image':
            template = properties.get('template', '')
            if template:
                images.add(template)
                
        elif node_type == 'find_multi_images':
            templates_str = properties.get('templates', '')
            # Parse comma or newline separated
            templates = [t.strip() for t in templates_str.replace('\n', ',').split(',') if t.strip()]
            images.update(templates)
    
    return images


def copy_images_to_script_folder(image_paths: Set[str], script_folder: str) -> int:
    """
    Copy images from global images/ folder to script's local images/ folder.
    
    Args:
        image_paths: Set of image paths (e.g., 'buttons/ok.png' or 'enemy.png')
        script_folder: Absolute path to script folder (e.g., 'scripts/MY_SCRIPT/')
        
    Returns:
        Number of images successfully copied
    """
    global_images_dir = 'images'
    local_images_dir = os.path.join(script_folder, 'images')
    
    # Ensure local images directory exists
    os.makedirs(local_images_dir, exist_ok=True)
    
    copied = 0
    for img_path in image_paths:
        # img_path might be 'images/subfolder/file.png' or just 'file.png'
        # Normalize: remove leading 'images/' if present
        if img_path.startswith('images/'):
            relative_path = img_path[7:]  # Remove 'images/'
        else:
            relative_path = img_path
        
        src = os.path.join(global_images_dir, relative_path)
        dst = os.path.join(local_images_dir, relative_path)
        
        if os.path.exists(src):
            # Ensure destination subdirectory exists
            dst_dir = os.path.dirname(dst)
            if dst_dir:
                os.makedirs(dst_dir, exist_ok=True)
            
            try:
                shutil.copy2(src, dst)
                log_message(f"Copied image: {relative_path}")
                copied += 1
            except Exception as e:
                log_message(f"Failed to copy {relative_path}: {e}")
        else:
            log_message(f"Image not found in global folder: {src}")
    
    return copied


def resolve_template_path(template: str, script_path: str = None) -> str:
    """
    Resolve template path, prioritizing script-local images.
    
    Args:
        template: Template path from node properties (e.g., 'images/button.png')
        script_path: Path to current script folder (e.g., 'scripts/MY_SCRIPT/')
        
    Returns:
        Resolved absolute path to the image file
    """
    # Normalize template path
    if template.startswith('images/'):
        relative_path = template[7:]
    else:
        relative_path = template
    
    # Priority 1: Script-local images folder
    if script_path:
        local_path = os.path.join(script_path, 'images', relative_path)
        if os.path.exists(local_path):
            return local_path
    
    # Priority 2: Global images folder
    global_path = os.path.join('images', relative_path)
    if os.path.exists(global_path):
        return global_path
    
    # Fallback: Return original (will fail gracefully in find_and_click)
    return template
