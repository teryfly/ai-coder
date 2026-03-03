{
    "message": str,           # Always present
    "type": str,              # Always present (StreamType constant)
    "timestamp": str,         # Always present (ISO 8601)
    "step": int,              # Present only if not None
    "total_steps": int,       # Present only if not None
    "data": dict,             # Present only if not None
}