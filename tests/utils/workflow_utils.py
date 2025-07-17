"""
Workflow execution utilities for running H2K to HPXML conversions.

This module provides common functions for:
- Running the h2k2hpxml.py CLI tool
- Managing input/output paths
- Validating workflow completion
- Finding and verifying output files
"""

import subprocess
import os
import glob
from typing import Tuple, Optional, List, Dict, Any


def run_h2k_workflow(input_path: str, output_dir: str, debug: bool = True) -> Tuple[bool, str, str]:
    """
    Run the H2K to HPXML workflow using the CLI tool.
    
    Args:
        input_path: Path to the H2K input file
        output_dir: Directory for outputs
        debug: Whether to run in debug mode
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Construct the command
        cmd = [
            "python", "src/h2k_hpxml/cli/h2k2hpxml.py", "run",
            "--input_path", input_path,
            "--output_path", output_dir
        ]
        
        if debug:
            cmd.append("--debug")
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        success = result.returncode == 0
        return success, result.stdout, result.stderr
        
    except Exception as e:
        return False, "", str(e)


def find_sql_file(base_output_path: str, base_name: str) -> Optional[str]:
    """
    Find the eplusout.sql file in the output directory structure.
    
    Args:
        base_output_path: Base output directory
        base_name: Base name of the input file (without extension)
        
    Returns:
        Path to eplusout.sql file if found, None otherwise
    """
    # Common locations to search for eplusout.sql
    search_patterns = [
        os.path.join(base_output_path, base_name, "run", "eplusout.sql"),
        os.path.join(base_output_path, base_name, "eplusout.sql"),
        os.path.join(base_output_path, "run", "eplusout.sql"),
        os.path.join(base_output_path, "eplusout.sql")
    ]
    
    # Also try glob patterns for more flexible searching
    glob_patterns = [
        os.path.join(base_output_path, "**", "eplusout.sql"),
        os.path.join(base_output_path, base_name, "**", "eplusout.sql")
    ]
    
    # Check exact paths first
    for pattern in search_patterns:
        if os.path.exists(pattern):
            print(f"Found eplusout.sql at: {pattern}")
            return pattern
    
    # Try glob patterns
    for pattern in glob_patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            sql_path = matches[0]  # Take the first match
            print(f"Found eplusout.sql via glob at: {sql_path}")
            return sql_path
    
    return None


def find_hpxml_file(base_output_path: str, base_name: str) -> Optional[str]:
    """
    Find the generated HPXML file in the output directory structure.
    
    Args:
        base_output_path: Base output directory
        base_name: Base name of the input file (without extension)
        
    Returns:
        Path to HPXML file if found, None otherwise
    """
    # Common locations to search for HPXML files
    search_patterns = [
        os.path.join(base_output_path, base_name, f"{base_name}.xml"),
        os.path.join(base_output_path, base_name, "original.xml"),
        os.path.join(base_output_path, f"{base_name}.xml"),
        os.path.join(base_output_path, "original.xml")
    ]
    
    # Check exact paths first
    for pattern in search_patterns:
        if os.path.exists(pattern):
            print(f"Found HPXML file at: {pattern}")
            return pattern
    
    # Try glob patterns for more flexible searching
    glob_patterns = [
        os.path.join(base_output_path, "**", "*.xml"),
        os.path.join(base_output_path, base_name, "**", "*.xml")
    ]
    
    for pattern in glob_patterns:
        matches = glob.glob(pattern, recursive=True)
        # Filter to actual HPXML files (exclude other XML files if any)
        hpxml_matches = [m for m in matches if m.endswith('.xml')]
        if hpxml_matches:
            hpxml_path = hpxml_matches[0]  # Take the first match
            print(f"Found HPXML file via glob at: {hpxml_path}")
            return hpxml_path
    
    return None


def explore_output_directory(output_path: str, max_depth: int = 3) -> Dict[str, Any]:
    """
    Explore output directory structure for debugging.
    
    Args:
        output_path: Path to explore
        max_depth: Maximum depth to explore
        
    Returns:
        Dictionary representing the directory structure
    """
    def explore_recursive(path: str, current_depth: int = 0) -> Dict[str, Any]:
        if current_depth >= max_depth:
            return {"...": "max_depth_reached"}
        
        structure = {}
        
        try:
            if os.path.isdir(path):
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        structure[f"{item}/"] = explore_recursive(item_path, current_depth + 1)
                    else:
                        file_size = os.path.getsize(item_path)
                        structure[item] = f"{file_size} bytes"
            else:
                return f"file: {os.path.getsize(path)} bytes"
                
        except PermissionError:
            structure["error"] = "permission_denied"
        except Exception as e:
            structure["error"] = str(e)
        
        return structure
    
    return explore_recursive(output_path)


def validate_workflow_outputs(base_output_path: str, base_name: str) -> Tuple[bool, List[str]]:
    """
    Validate that all expected workflow outputs were created.
    
    Args:
        base_output_path: Base output directory
        base_name: Base name of the input file
        
    Returns:
        Tuple of (all_valid, list_of_missing_files)
    """
    expected_output_path = os.path.join(base_output_path, base_name)
    missing_files = []
    
    # Check that output directory exists
    if not os.path.exists(expected_output_path):
        missing_files.append(f"Output directory: {expected_output_path}")
        return False, missing_files
    
    # Expected files (these may vary based on the actual workflow)
    expected_files = [
        "eplusout.sql",  # Primary target
        "eplusout.err"   # Error log
    ]
    
    # Also check for HPXML file
    hpxml_file = find_hpxml_file(base_output_path, base_name)
    if not hpxml_file:
        missing_files.append("HPXML file (*.xml)")
    
    # Search for each expected file
    for expected_file in expected_files:
        found = False
        
        # Search in common locations
        search_locations = [
            os.path.join(expected_output_path, expected_file),
            os.path.join(expected_output_path, "run", expected_file),
            os.path.join(expected_output_path, "simulation", expected_file)
        ]
        
        for location in search_locations:
            if os.path.exists(location):
                found = True
                break
        
        # Also try glob search
        if not found:
            glob_pattern = os.path.join(expected_output_path, "**", expected_file)
            matches = glob.glob(glob_pattern, recursive=True)
            if matches:
                found = True
        
        if not found:
            missing_files.append(expected_file)
    
    return len(missing_files) == 0, missing_files


def get_h2k_example_files() -> List[str]:
    """Get list of H2K example files for testing."""
    examples_dir = "examples"
    if not os.path.exists(examples_dir):
        return []
    
    h2k_files = []
    for file_name in os.listdir(examples_dir):
        if file_name.endswith('.h2k') or file_name.endswith('.H2K'):
            h2k_files.append(file_name)
    
    return sorted(h2k_files)


def create_test_output_directory(base_dir: str, test_name: str) -> str:
    """
    Create a test output directory with proper naming.
    
    Args:
        base_dir: Base directory for test outputs
        test_name: Name of the test
        
    Returns:
        Path to created output directory
    """
    output_dir = os.path.join(base_dir, test_name)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def cleanup_test_outputs(output_dir: str, keep_on_failure: bool = True) -> None:
    """
    Clean up test output directory.
    
    Args:
        output_dir: Directory to clean up
        keep_on_failure: Whether to keep outputs when tests fail
    """
    # This could be implemented to clean up test outputs
    # For now, we'll keep all outputs for debugging
    pass
