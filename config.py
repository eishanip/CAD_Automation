# ============================================================================
# config.py - Configuration and Constants
# ============================================================================

class Config:
    """Global configuration for DXF to 3D conversion"""
    
    # Tolerance Settings
    EDGE_CONNECTION_TOLERANCE = 0.1  # mm - for chaining disconnected edges
    PROFILE_CLOSURE_TOLERANCE = 0.01  # mm - to check if profile is closed
    POINT_COINCIDENCE_TOLERANCE = 0.01  # mm - to check if two points are same
    
    # Approximation Settings
    ARC_SEGMENTS = 16  # Number of segments to approximate arcs
    SPLINE_SEGMENTS = 20  # Number of segments to approximate splines
    
    # Default Values
    DEFAULT_EXTRUDE_DEPTH = 10.0  # mm
    DEFAULT_REVOLVE_ANGLE = 360.0  # degrees
    
    # Feature Detection
    MIN_PROFILE_EDGES = 3  # Minimum edges to form a valid profile
    
    # Validation Settings
    ENABLE_STRICT_VALIDATION = True  # Fail fast on invalid geometry