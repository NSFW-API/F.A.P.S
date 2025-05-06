import hashlib
import json
from typing import Dict, Any


def hash_params(params: Dict[str, Any]) -> str:
    """
    Create a deterministic hash for a parameter combination.
    
    This function creates a SHA1 hash of the canonicalized JSON representation
    of the parameters. It ignores any keys that start with an underscore.
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        SHA1 hash as a hex string
    """
    # Create a clean copy without any keys starting with underscore
    clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
    
    # Sort keys for deterministic ordering
    canonical_json = json.dumps(clean_params, sort_keys=True)
    
    # Create SHA1 hash
    hash_obj = hashlib.sha1(canonical_json.encode('utf-8'))
    return hash_obj.hexdigest()
