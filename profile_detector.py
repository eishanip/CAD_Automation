# ============================================================================
# profile_detector.py - Profile Chaining and Classification
# ============================================================================

class Profile:
    """Represents a closed 2D profile (contour)"""
    
    def __init__(self, edges: List[GeometricEdge], is_outer: bool = True):
        self.edges = edges
        self.is_outer = is_outer
        self.area = 0.0
        self.centroid = (0.0, 0.0)
        self.bounding_box = None
        self.is_closed = False
        self.closure_gap = 0.0  # Distance between first and last point
    
    def calculate_properties(self):
        """Calculate area, centroid, and closure status"""
        if not self.edges:
            return
        
        points = []
        for edge in self.edges:
            if edge.start_point:
                points.append(edge.start_point)
            if edge.end_point and edge.end_point != edge.start_point:
                points.append(edge.end_point)
        
        if len(points) >= Config.MIN_PROFILE_EDGES:
            # Calculate area using shoelace formula
            area = 0.0
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            self.area = abs(area) / 2.0
            
            # Calculate centroid
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            self.centroid = (cx, cy)
            
            # Check closure
            if len(points) > 0:
                first = points[0]
                last = points[-1]
                self.closure_gap = math.sqrt((last[0]-first[0])**2 + (last[1]-first[1])**2)
                self.is_closed = self.closure_gap < Config.PROFILE_CLOSURE_TOLERANCE
    
    def validate_closure(self) -> Tuple[bool, str]:
        """Validate if profile is properly closed"""
        if not self.edges:
            return False, "Profile has no edges"
        
        if len(self.edges) < Config.MIN_PROFILE_EDGES:
            return False, f"Profile has only {len(self.edges)} edges (minimum {Config.MIN_PROFILE_EDGES} required)"
        
        # Circles and closed polylines are always valid
        if len(self.edges) == 1:
            if self.edges[0].edge_type in ['CIRCLE', 'POLYLINE']:
                return True, "Profile is a closed entity (circle or polyline)"
        
        # Check closure gap
        if not self.is_closed:
            return False, f"Profile not closed (gap: {self.closure_gap:.3f}mm, tolerance: {Config.PROFILE_CLOSURE_TOLERANCE}mm)"
        
        return True, "Profile is valid and closed"


class ProfileDetector:
    """Handles profile detection and edge chaining"""
    
    @staticmethod
    def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    @staticmethod
    def chain_edges_into_profiles(edges: List[GeometricEdge]) -> List[Profile]:
        """Chain disconnected edges into closed profiles"""
        print("\nChaining edges into profiles...")
        
        profiles = []
        used_edges = set()
        
        # Step 1: Handle circles and closed polylines (already closed)
        for i, edge in enumerate(edges):
            if i in used_edges:
                continue
            
            if edge.edge_type in ['CIRCLE', 'POLYLINE']:
                profile = Profile([edge], is_outer=True)
                profile.is_closed = True
                profile.calculate_properties()
                profiles.append(profile)
                used_edges.add(i)
                print(f"  Found closed {edge.edge_type} profile (area={profile.area:.2f}mm²)")
        
        # Step 2: Chain remaining edges (lines, arcs, splines)
        remaining_edges = [
            (i, edge) for i, edge in enumerate(edges) 
            if i not in used_edges
        ]
        
        while remaining_edges:
            # Start a new chain
            chain = []
            idx, start_edge = remaining_edges.pop(0)
            chain.append(start_edge)
            used_edges.add(idx)
            
            # Track current endpoint for connection
            current_end = start_edge.end_point
            
            # Assumption: Limit iterations to prevent infinite loops
            max_iterations = len(remaining_edges) + 10
            iterations = 0
            
            while iterations < max_iterations:
                iterations += 1
                found_connection = False
                
                for i, (idx, edge) in enumerate(remaining_edges):
                    if idx in used_edges:
                        continue
                    
                    # Check if this edge connects to current end
                    dist_to_start = edge.distance_to_point(current_end) if edge.start_point else float('inf')
                    dist_to_end = edge.distance_to_point(current_end) if edge.end_point else float('inf')
                    
                    # Connect if within tolerance
                    if dist_to_start < Config.EDGE_CONNECTION_TOLERANCE:
                        chain.append(edge)
                        used_edges.add(idx)
                        remaining_edges.pop(i)
                        current_end = edge.end_point
                        found_connection = True
                        break
                    elif dist_to_end < Config.EDGE_CONNECTION_TOLERANCE:
                        # Assumption: Reversing edge by swapping start/end conceptually
                        chain.append(edge)
                        used_edges.add(idx)
                        remaining_edges.pop(i)
                        current_end = edge.start_point
                        found_connection = True
                        break
                
                if not found_connection:
                    break
            
            # Create profile if sufficient edges
            if len(chain) >= Config.MIN_PROFILE_EDGES:
                profile = Profile(chain, is_outer=True)
                profile.calculate_properties()
                profiles.append(profile)
                
                status = "closed" if profile.is_closed else f"open (gap={profile.closure_gap:.3f}mm)"
                print(f"  Chained profile: {len(chain)} edges, area={profile.area:.2f}mm², {status}")
        
        # Sort profiles by area (largest first = likely base feature)
        profiles.sort(key=lambda p: p.area, reverse=True)
        
        # Classify outer vs inner profiles based on area
        if profiles:
            profiles[0].is_outer = True
            for p in profiles[1:]:
                p.is_outer = False  # Assumption: Smaller profiles are holes/cuts
        
        print(f"✓ Created {len(profiles)} profiles from chained edges")
        return profiles