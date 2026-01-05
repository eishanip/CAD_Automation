"""
DXF to 3D STEP Converter
Annotation-driven with rule-based fallback approach

Requirements:
pip install ezdxf cadquery

Usage:
    converter = DXFTo3DConverter('input_sketch.dxf')
    converter.process()
    converter.export_step('output_part.step')
"""

import ezdxf
from ezdxf.math import Vec3
import cadquery as cq
from typing import List, Dict, Tuple, Optional
import re
import math


class Profile:
    """Represents a closed 2D profile (contour)"""
    def __init__(self, edges: List, is_outer: bool = True):
        self.edges = edges
        self.is_outer = is_outer
        self.area = 0.0
        self.centroid = (0.0, 0.0)
        self.bounding_box = None
        
    def calculate_properties(self):
        """Calculate area and centroid for profile classification"""
        # Simplified calculation - in production, use proper polygon algorithms
        if not self.edges:
            return
        
        points = []
        for edge in self.edges:
            if hasattr(edge, 'dxf'):
                if edge.dxftype() == 'LINE':
                    points.append((edge.dxf.start.x, edge.dxf.start.y))
                elif edge.dxftype() == 'CIRCLE':
                    points.append((edge.dxf.center.x, edge.dxf.center.y))
        
        if len(points) >= 3:
            # Calculate approximate area using shoelace formula
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


class FeatureInfo:
    """Information about a recognized feature"""
    def __init__(self, profile: Profile, feature_type: str, 
                 operation: str = 'extrude', depth: float = 10.0):
        self.profile = profile
        self.feature_type = feature_type  # 'base', 'hole', 'pocket', 'boss'
        self.operation = operation  # 'extrude', 'cut', 'revolve'
        self.depth = depth
        self.direction = 'normal'  # 'normal' or custom vector


class DXFTo3DConverter:
    """Main converter class implementing the workflow"""
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc = None
        self.msp = None
        self.profiles = []
        self.features = []
        self.annotations = {}
        self.result_solid = None
        self.default_depth = 10.0  # Default extrusion depth
        
    def load_dxf(self):
        """Step 1: Load and parse DXF file using ezdxf"""
        print("Loading DXF file...")
        try:
            self.doc = ezdxf.readfile(self.dxf_path)
            self.msp = self.doc.modelspace()
            print(f"✓ Loaded: {len(list(self.msp))} entities found")
        except Exception as e:
            print(f"✗ Error loading DXF: {e}")
            raise
    
    def extract_annotations(self):
        """Step 2: Parse dimensions and text annotations (annotation-driven)"""
        print("\nExtracting annotations...")
        
        # Extract TEXT entities
        for text in self.msp.query('TEXT'):
            content = text.dxf.text.upper()
            position = (text.dxf.insert.x, text.dxf.insert.y)
            
            # Look for depth annotations like "DEPTH: 50", "D=50", "EXTRUDE 50"
            depth_match = re.search(r'(?:DEPTH|D|EXTRUDE)[\s:=]+(\d+\.?\d*)', content)
            if depth_match:
                depth_value = float(depth_match.group(1))
                self.annotations['depth'] = depth_value
                print(f"  Found depth annotation: {depth_value}mm at {position}")
            
            # Look for operation type: "CUT", "HOLE", "BOSS", "BASE"
            if 'CUT' in content or 'HOLE' in content:
                self.annotations['operation'] = 'cut'
                print(f"  Found operation: CUT")
            elif 'BOSS' in content or 'PROTRUSION' in content:
                self.annotations['operation'] = 'add'
                print(f"  Found operation: ADD")
            elif 'BASE' in content:
                self.annotations['base_feature'] = True
                print(f"  Found base feature marker")
        
        # Extract DIMENSION entities
        for dim in self.msp.query('DIMENSION'):
            if hasattr(dim.dxf, 'text') and dim.dxf.text:
                try:
                    value = float(dim.dxf.text)
                    # Store dimension values for reference
                    if 'dimensions' not in self.annotations:
                        self.annotations['dimensions'] = []
                    self.annotations['dimensions'].append(value)
                except ValueError:
                    pass
        
        print(f"✓ Extracted {len(self.annotations)} annotation entries")
    
    def extract_geometry(self):
        """Step 3: Extract geometric entities from DXF"""
        print("\nExtracting geometry...")
        
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
        
        # Store all entities for profile detection
        self.all_entities = {
            'lines': lines,
            'arcs': arcs,
            'circles': circles,
            'polylines': polylines,
            'splines': splines
        }
        
        print("✓ Geometry extracted")
    
    def identify_profiles(self):
        """Step 4: Identify closed profiles (rule-based)"""
        print("\nIdentifying closed profiles...")
        
        # Simple approach: treat each closed polyline and circle as a profile
        profiles = []
        
        # Process circles (always closed)
        for circle in self.all_entities['circles']:
            profile = Profile([circle], is_outer=True)
            profile.calculate_properties()
            profiles.append(profile)
            print(f"  Circle profile at ({circle.dxf.center.x:.2f}, {circle.dxf.center.y:.2f}), r={circle.dxf.radius:.2f}")
        
        # Process closed polylines
        for pline in self.all_entities['polylines']:
            if pline.is_closed or pline.has_arc:
                profile = Profile([pline], is_outer=True)
                profile.calculate_properties()
                profiles.append(profile)
                print(f"  Polyline profile with {len(list(pline.vertices()))} vertices")
        
        # Sort profiles by area (largest first = likely base feature)
        profiles.sort(key=lambda p: p.area, reverse=True)
        
        # Classify: largest = outer, others = inner (holes)
        if profiles:
            profiles[0].is_outer = True
            for p in profiles[1:]:
                p.is_outer = False  # Smaller profiles assumed to be holes
        
        self.profiles = profiles
        print(f"✓ Identified {len(profiles)} profiles")
    
    def detect_features(self):
        """Step 5: Detect features and determine operation sequence"""
        print("\nDetecting features...")
        
        if not self.profiles:
            print("✗ No profiles found!")
            return
        
        # Get depth from annotations or use default
        depth = self.annotations.get('depth', self.default_depth)
        
        # First profile = base feature
        base_profile = self.profiles[0]
        base_feature = FeatureInfo(
            profile=base_profile,
            feature_type='base',
            operation='extrude',
            depth=depth
        )
        self.features.append(base_feature)
        print(f"  Base feature: extrude depth={depth}mm")
        
        # Remaining profiles = holes/cuts (rule-based)
        for i, profile in enumerate(self.profiles[1:], 1):
            # Check if annotation specifies operation
            operation = self.annotations.get('operation', 'cut')
            
            feature = FeatureInfo(
                profile=profile,
                feature_type='hole' if operation == 'cut' else 'boss',
                operation=operation,
                depth=depth
            )
            self.features.append(feature)
            print(f"  Feature {i}: {feature.feature_type}, operation={operation}, depth={depth}mm")
        
        print(f"✓ Detected {len(self.features)} features")
    
    def build_cadquery_model(self):
        """Steps 6-8: Convert to CadQuery and perform 3D operations"""
        print("\nBuilding 3D model with CadQuery...")
        
        if not self.features:
            print("✗ No features to build!")
            return
        
        # Start with base feature
        base_feature = self.features[0]
        result = self.create_sketch_from_profile(base_feature.profile)
        
        if result is None:
            print("✗ Failed to create base sketch")
            return
        
        # Extrude base
        result = result.extrude(base_feature.depth)
        print(f"  ✓ Extruded base feature: {base_feature.depth}mm")
        
        # Apply additional features
        for i, feature in enumerate(self.features[1:], 1):
            try:
                feature_sketch = self.create_sketch_from_profile(feature.profile)
                
                if feature_sketch is None:
                    print(f"  ✗ Skipping feature {i}: failed to create sketch")
                    continue
                
                # Perform boolean operation
                if feature.operation == 'cut':
                    # Create cutting solid
                    cut_solid = feature_sketch.extrude(feature.depth)
                    result = result.cut(cut_solid)
                    print(f"  ✓ Cut feature {i}: depth={feature.depth}mm")
                elif feature.operation == 'add':
                    add_solid = feature_sketch.extrude(feature.depth)
                    result = result.union(add_solid)
                    print(f"  ✓ Added feature {i}: depth={feature.depth}mm")
                    
            except Exception as e:
                print(f"  ✗ Error processing feature {i}: {e}")
        
        self.result_solid = result
        print("✓ 3D model built successfully")
    
    def create_sketch_from_profile(self, profile: Profile) -> Optional[cq.Workplane]:
        """Convert DXF profile to CadQuery sketch"""
        try:
            # Handle circles
            if len(profile.edges) == 1 and profile.edges[0].dxftype() == 'CIRCLE':
                circle = profile.edges[0]
                cx, cy = circle.dxf.center.x, circle.dxf.center.y
                r = circle.dxf.radius
                
                sketch = cq.Workplane("XY").center(cx, cy).circle(r)
                return sketch
            
            # Handle polylines
            elif len(profile.edges) == 1 and profile.edges[0].dxftype() == 'LWPOLYLINE':
                pline = profile.edges[0]
                points = [(v[0], v[1]) for v in pline.get_points()]
                
                if len(points) < 3:
                    return None
                
                # Create polyline sketch
                sketch = cq.Workplane("XY").polyline(points).close()
                return sketch
            
            # For other cases, create simple rectangle as placeholder
            else:
                # Fallback: create a simple rectangle
                sketch = cq.Workplane("XY").rect(20, 20)
                return sketch
                
        except Exception as e:
            print(f"    Error creating sketch: {e}")
            return None
    
    def export_step(self, output_path: str = 'output.step'):
        """Step 9: Export to STEP file"""
        print(f"\nExporting to STEP: {output_path}")
        
        if self.result_solid is None:
            print("✗ No solid to export!")
            return False
        
        try:
            cq.exporters.export(self.result_solid, output_path)
            print(f"✓ STEP file exported successfully: {output_path}")
            return True
        except Exception as e:
            print(f"✗ Export failed: {e}")
            return False
    
    def process(self):
        """Execute the complete workflow"""
        print("="*60)
        print("DXF to 3D STEP Converter - Prototype")
        print("="*60)
        
        try:
            # Complete workflow
            self.load_dxf()
            self.extract_annotations()
            self.extract_geometry()
            self.identify_profiles()
            self.detect_features()
            self.build_cadquery_model()
            
            print("\n" + "="*60)
            print("Processing complete!")
            print("="*60)
            
        except Exception as e:
            print(f"\n✗ Processing failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Example: Process a DXF file
    converter = DXFTo3DConverter('input_sketch.dxf')
    converter.process()
    converter.export_step('output_part.step')
    
    print("\n" + "="*60)
    print("USAGE NOTES:")
    print("="*60)
    print("""
1. Create a DXF file with:
   - Closed polylines or circles for profiles
   - TEXT annotations like:
     * "DEPTH: 50" or "D=50" for extrusion depth
     * "CUT" or "HOLE" for cut operations
     * "BASE" to mark base feature
   
2. Run the converter:
   converter = DXFTo3DConverter('your_file.dxf')
   converter.process()
   converter.export_step('output.step')

3. The tool will:
   - Parse annotations (annotation-driven)
   - Detect profiles automatically (rule-based fallback)
   - Create base feature from largest profile
   - Cut smaller profiles as holes
   - Export to STEP format

4. Limitations of this prototype:
   - Supports circles and polylines only
   - Simple feature detection rules
   - Fixed extrusion direction (Z-axis)
   - No support for revolve/loft yet
   
5. Next steps for enhancement:
   - Add support for arcs, splines, lines
   - Implement advanced profile chaining
   - Add revolve/sweep operations
   - Improve feature recognition heuristics
   - Add GUI for interactive confirmation
    """)