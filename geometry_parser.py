# ============================================================================
# geometry_parser.py - DXF Parsing and Edge Extraction
# ============================================================================

import ezdxf
from ezdxf.math import Vec3
from typing import List, Tuple, Optional
import math


class GeometricEdge:
    """Wrapper for DXF entities as edges with endpoint extraction"""
    
    def __init__(self, entity, edge_type: str):
        self.entity = entity
        self.edge_type = edge_type  # 'LINE', 'ARC', 'CIRCLE', 'SPLINE', 'POLYLINE'
        self.start_point = None
        self.end_point = None
        self._extract_endpoints()
    
    def _extract_endpoints(self):
        """Extract start and end points from DXF entity"""
        if self.edge_type == 'LINE':
            self.start_point = (self.entity.dxf.start.x, self.entity.dxf.start.y)
            self.end_point = (self.entity.dxf.end.x, self.entity.dxf.end.y)
        
        elif self.edge_type == 'ARC':
            cx, cy = self.entity.dxf.center.x, self.entity.dxf.center.y
            r = self.entity.dxf.radius
            start_angle = math.radians(self.entity.dxf.start_angle)
            end_angle = math.radians(self.entity.dxf.end_angle)
            
            self.start_point = (
                cx + r * math.cos(start_angle),
                cy + r * math.sin(start_angle)
            )
            self.end_point = (
                cx + r * math.cos(end_angle),
                cy + r * math.sin(end_angle)
            )
        
        elif self.edge_type == 'SPLINE':
            # Assumption: Using control points for endpoints (may not be exact for complex splines)
            if hasattr(self.entity, 'control_points') and len(self.entity.control_points) > 0:
                self.start_point = (
                    self.entity.control_points[0][0],
                    self.entity.control_points[0][1]
                )
                self.end_point = (
                    self.entity.control_points[-1][0],
                    self.entity.control_points[-1][1]
                )
        
        elif self.edge_type == 'CIRCLE':
            # Circles don't have traditional start/end points
            cx, cy = self.entity.dxf.center.x, self.entity.dxf.center.y
            self.start_point = (cx, cy)
            self.end_point = (cx, cy)
        
        elif self.edge_type == 'POLYLINE':
            # For polylines, get first and last vertex
            points = list(self.entity.get_points())
            if points:
                self.start_point = (points[0][0], points[0][1])
                self.end_point = (points[-1][0], points[-1][1])
    
    def distance_to_point(self, point: Tuple[float, float]) -> float:
        """Calculate minimum distance from this edge to a point"""
        if self.start_point is None:
            return float('inf')
        
        dx1 = point[0] - self.start_point[0]
        dy1 = point[1] - self.start_point[1]
        dist_start = math.sqrt(dx1*dx1 + dy1*dy1)
        
        if self.end_point:
            dx2 = point[0] - self.end_point[0]
            dy2 = point[1] - self.end_point[1]
            dist_end = math.sqrt(dx2*dx2 + dy2*dy2)
            return min(dist_start, dist_end)
        
        return dist_start


class GeometryParser:
    """Handles DXF file loading and geometric entity extraction"""
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc = None
        self.msp = None
        self.geometric_edges = []
    
    def load_dxf(self) -> bool:
        """Load DXF file"""
        print("Loading DXF file...")
        try:
            self.doc = ezdxf.readfile(self.dxf_path)
            self.msp = self.doc.modelspace()
            entity_count = len(list(self.msp))
            print(f"✓ Loaded: {entity_count} entities found")
            return True
        except FileNotFoundError:
            print(f"✗ Error: DXF file not found: {self.dxf_path}")
            return False
        except Exception as e:
            print(f"✗ Error loading DXF: {e}")
            return False
    
    def extract_geometry(self) -> List[GeometricEdge]:
        """Extract all geometric entities from DXF"""
        print("\nExtracting geometry...")
        
        # Query different entity types
        lines = list(self.msp.query('LINE'))
        arcs = list(self.msp.query('ARC'))
        circles = list(self.msp.query('CIRCLE'))
        polylines = list(self.msp.query('LWPOLYLINE'))
        splines = list(self.msp.query('SPLINE'))
        
        print(f"  Lines: {len(lines)}")
        print(f"  Arcs: {len(arcs)}")
        print(f"  Circles: {len(circles)}")
        print(f"  Polylines: {len(polylines)}")
        print(f"  Splines: {len(splines)}")
        
        # Convert to GeometricEdge objects
        edges = []
        
        for line in lines:
            edges.append(GeometricEdge(line, 'LINE'))
        
        for arc in arcs:
            edges.append(GeometricEdge(arc, 'ARC'))
        
        for circle in circles:
            edges.append(GeometricEdge(circle, 'CIRCLE'))
        
        for spline in splines:
            edges.append(GeometricEdge(spline, 'SPLINE'))
        
        for pline in polylines:
            edges.append(GeometricEdge(pline, 'POLYLINE'))
        
        self.geometric_edges = edges
        print(f"✓ Created {len(edges)} geometric edges")
        return edges