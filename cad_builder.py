# ============================================================================
# cad_builder.py - 3D Model Construction
# ============================================================================

import cadquery as cq


class CADBuilder:
    """Handles 3D model construction using CadQuery"""
    
    @staticmethod
    def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    @staticmethod
    def approximate_arc(arc_entity, segments: int = None) -> List[Tuple[float, float]]:
        """Approximate arc with line segments"""
        if segments is None:
            segments = Config.ARC_SEGMENTS
        
        cx, cy = arc_entity.dxf.center.x, arc_entity.dxf.center.y
        r = arc_entity.dxf.radius
        start_angle = math.radians(arc_entity.dxf.start_angle)
        end_angle = math.radians(arc_entity.dxf.end_angle)
        
        # Handle angle wrap-around
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        
        points = []
        for i in range(segments + 1):
            t = i / segments
            angle = start_angle + t * (end_angle - start_angle)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
        
        return points
    
    @staticmethod
    def approximate_spline(spline_entity, segments: int = None) -> List[Tuple[float, float]]:
        """Approximate spline with line segments"""
        if segments is None:
            segments = Config.SPLINE_SEGMENTS
        
        if not hasattr(spline_entity, 'control_points') or len(spline_entity.control_points) < 2:
            return []
        
        # Assumption: Simple linear interpolation between control points
        # Note: This is NOT a true spline approximation, just connects control points
        points = []
        control_pts = [(p[0], p[1]) for p in spline_entity.control_points]
        
        for i in range(len(control_pts) - 1):
            p1 = control_pts[i]
            p2 = control_pts[i + 1]
            
            for j in range(segments):
                t = j / segments
                x = p1[0] + t * (p2[0] - p1[0])
                y = p1[1] + t * (p2[1] - p1[1])
                points.append((x, y))
        
        points.append(control_pts[-1])
        return points
    
    @staticmethod
    def create_sketch_from_profile(profile: Profile) -> Tuple[Optional[cq.Workplane], str]:
        """
        Convert profile to CadQuery sketch
        Returns: (sketch, error_message)
        """
        try:
            # Single circle
            if len(profile.edges) == 1 and profile.edges[0].edge_type == 'CIRCLE':
                circle = profile.edges[0].entity
                cx, cy = circle.dxf.center.x, circle.dxf.center.y
                r = circle.dxf.radius
                return cq.Workplane("XY").center(cx, cy).circle(r), ""
            
            # Single polyline
            if len(profile.edges) == 1 and profile.edges[0].edge_type == 'POLYLINE':
                pline = profile.edges[0].entity
                points = [(v[0], v[1]) for v in pline.get_points()]
                if len(points) < 3:
                    return None, f"Polyline has insufficient points ({len(points)} < 3)"
                return cq.Workplane("XY").polyline(points).close(), ""
            
            # Chained edges (lines, arcs, splines)
            if len(profile.edges) > 1:
                points = []
                
                # Collect points from all edges
                for edge in profile.edges:
                    if edge.edge_type == 'LINE':
                        if not points or CADBuilder.point_distance(points[-1], edge.start_point) > Config.POINT_COINCIDENCE_TOLERANCE:
                            points.append(edge.start_point)
                        points.append(edge.end_point)
                    
                    elif edge.edge_type == 'ARC':
                        arc_points = CADBuilder.approximate_arc(edge.entity)
                        points.extend(arc_points)
                    
                    elif edge.edge_type == 'SPLINE':
                        spline_points = CADBuilder.approximate_spline(edge.entity)
                        points.extend(spline_points)
                
                # Remove duplicate consecutive points
                unique_points = []
                for p in points:
                    if not unique_points or CADBuilder.point_distance(p, unique_points[-1]) > Config.POINT_COINCIDENCE_TOLERANCE:
                        unique_points.append(p)
                
                if len(unique_points) < 3:
                    return None, f"Insufficient unique points after chaining ({len(unique_points)} < 3)"
                
                return cq.Workplane("XY").polyline(unique_points).close(), ""
            
            return None, f"Unsupported profile configuration (edges={len(profile.edges)})"
        
        except Exception as e:
            return None, f"Sketch creation failed: {str(e)}"
    
    @staticmethod
    def validate_revolve_inputs(feature: FeatureInfo) -> Tuple[bool, str]:
        """Validate inputs for revolve operation"""
        # Check profile validity
        is_valid, msg = feature.profile.validate_closure()
        if not is_valid:
            return False, f"Revolve failed: {msg}"
        
        # Validate angle
        if feature.angle <= 0 or feature.angle > 360:
            return False, f"Revolve failed: Invalid angle ({feature.angle}°), must be in range (0, 360]"
        
        # Assumption for axis: If not provided, revolve around Y-axis at origin
        # If provided, axis represents (x, y) point on the XY plane, revolve around vertical line through that point
        if feature.axis:
            ax, ay = feature.axis
            # Basic validation: axis should be reasonable values
            if abs(ax) > 10000 or abs(ay) > 10000:
                return False, f"Revolve failed: Axis values seem unreasonable ({feature.axis})"
        
        return True, ""
    
    @staticmethod
    def build_3d_model(features: List[FeatureInfo]) -> Tuple[Optional[cq.Workplane], str]:
        """
        Build complete 3D model from features
        Returns: (solid, error_message)
        """
        print("\nBuilding 3D model...")
        
        if not features:
            return None, "No features to build"
        
        base_feature = features[0]
        
        # Validate base profile closure
        is_closed, closure_msg = base_feature.profile.validate_closure()
        if not is_closed and Config.ENABLE_STRICT_VALIDATION:
            error = f"Base feature validation failed: {closure_msg}"
            print(f"✗ {error}")
            return None, error
        
        try:
            result = None
            
            # Build base feature based on operation type
            if base_feature.operation == 'extrude':
                sketch, error = CADBuilder.create_sketch_from_profile(base_feature.profile)
                if sketch is None:
                    return None, f"Extrude failed: {error}"
                
                result = sketch.extrude(base_feature.depth)
                print(f"  ✓ Extruded base: {base_feature.depth}mm")
            
            elif base_feature.operation == 'revolve':
                # Validate revolve inputs
                is_valid, error_msg = CADBuilder.validate_revolve_inputs(base_feature)
                if not is_valid:
                    print(f"✗ {error_msg}")
                    return None, error_msg
                
                sketch, error = CADBuilder.create_sketch_from_profile(base_feature.profile)
                if sketch is None:
                    return None, f"Revolve failed: {error}"
                
                # Perform revolve
                # Assumption: Revolving around Y-axis by default, or vertical axis through custom point
                if base_feature.axis:
                    ax, ay = base_feature.axis
                    # Revolve around vertical axis through (ax, ay)
                    result = sketch.revolve(base_feature.angle, (ax, ay, 0), (ax, ay, 1))
                    print(f"  ✓ Revolved base: {base_feature.angle}° around axis at ({ax}, {ay})")
                else:
                    # Default: revolve around Y-axis
                    result = sketch.revolve(base_feature.angle)
                    print(f"  ✓ Revolved base: {base_feature.angle}° around Y-axis")
            
            elif base_feature.operation == 'loft':
                error = "Loft operation not fully implemented yet. Requires multi-plane profile setup and advanced CadQuery operations."
                print(f"✗ {error}")
                return None, error
            
            elif base_feature.operation == 'sweep':
                error = "Sweep operation not fully implemented yet. Requires 3D path curve definition and advanced CadQuery operations."
                print(f"✗ {error}")
                return None, error
            
            else:
                error = f"Unknown operation: {base_feature.operation}"
                print(f"✗ {error}")
                return None, error
            
            if result is None:
                return None, "Failed to create base feature"
            
            # Apply additional features (cuts/additions)
            for i, feature in enumerate(features[1:], 1):
                try:
                    # Validate feature profile
                    is_closed, closure_msg = feature.profile.validate_closure()
                    if not is_closed and Config.ENABLE_STRICT_VALIDATION:
                        print(f"  ⚠ Skipping feature {i}: {closure_msg}")
                        continue
                    
                    if feature.operation == 'cut':
                        cut_sketch, error = CADBuilder.create_sketch_from_profile(feature.profile)
                        if cut_sketch is None:
                            print(f"  ⚠ Skipping feature {i}: {error}")
                            continue
                        
                        cut_solid = cut_sketch.extrude(feature.depth)
                        result = result.cut(cut_solid)
                        print(f"  ✓ Cut feature {i}: depth={feature.depth}mm")
                    
                    elif feature.operation == 'add':
                        add_sketch, error = CADBuilder.create_sketch_from_profile(feature.profile)
                        if add_sketch is None:
                            print(f"  ⚠ Skipping feature {i}: {error}")
                            continue
                        
                        add_solid = add_sketch.extrude(feature.depth)
                        result = result.union(add_solid)
                        print(f"  ✓ Added feature {i}: depth={feature.depth}mm")
                    
                    else:
                        print(f"  ⚠ Skipping feature {i}: Unknown operation '{feature.operation}'")
                
                except Exception as e:
                    print(f"  ⚠ Skipping feature {i}: {str(e)}")
            
            print("✓ 3D model built successfully")
            return result, ""
        
        except Exception as e:
            error = f"Model building failed: {str(e)}"
            print(f"✗ {error}")
            import traceback
            traceback.print_exc()
            return None, error

