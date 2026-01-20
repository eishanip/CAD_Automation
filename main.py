# ============================================================================
# main.py - Main Converter Orchestration
# ============================================================================

class DXFTo3DConverter:
    """Main orchestrator for DXF to 3D STEP conversion"""
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.parser = None
        self.profiles = []
        self.features = []
        self.result_solid = None
        self.error_log = []
    
    def process(self) -> bool:
        """Execute complete conversion workflow"""
        print("="*60)
        print("DXF to 3D STEP Converter - Modular Architecture")
        print("="*60)
        
        try:
            # Step 1: Parse DXF geometry
            self.parser = GeometryParser(self.dxf_path)
            if not self.parser.load_dxf():
                self.error_log.append("Failed to load DXF file")
                return False
            
            geometric_edges = self.parser.extract_geometry()
            if not geometric_edges:
                self.error_log.append("No geometric entities found in DXF")
                return False
            
            # Step 2: Detect profiles
            self.profiles = ProfileDetector.chain_edges_into_profiles(geometric_edges)
            if not self.profiles:
                self.error_log.append("No valid profiles detected")
                return False
            
            # Step 3: Extract annotations and detect features
            feature_detector = FeatureDetector(self.parser.msp)
            annotations = feature_detector.extract_annotations()
            self.features = feature_detector.detect_features(self.profiles)
            
            if not self.features:
                self.error_log.append("No features detected. Check annotations or add more profiles.")
                return False
            
            # Step 4: Build 3D model
            self.result_solid, error_msg = CADBuilder.build_3d_model(self.features)
            
            if self.result_solid is None:
                self.error_log.append(f"3D model building failed: {error_msg}")
                return False
            
            print("\n" + "="*60)
            print("Processing complete!")
            print("="*60)
            return True
        
        except Exception as e:
            error = f"Unexpected error during processing: {str(e)}"
            print(f"\n✗ {error}")
            self.error_log.append(error)
            import traceback
            traceback.print_exc()
            return False
    
    def export_step(self, output_path: str = 'output.step') -> bool:
        """Export result to STEP file"""
        print(f"\nExporting to STEP: {output_path}")
        
        if self.result_solid is None:
            print("✗ No solid to export! Run process() first.")
            return False
        
        try:
            cq.exporters.export(self.result_solid, output_path)
            print(f"✓ STEP file exported successfully: {output_path}")
            return True
        except Exception as e:
            error = f"Export failed: {str(e)}"
            print(f"✗ {error}")
            self.error_log.append(error)
            return False
    
    def get_error_log(self) -> List[str]:
        """Get list of all errors encountered"""
        return self.error_log
    
    def print_summary(self):
        """Print processing summary"""
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Profiles detected: {len(self.profiles)}")
        print(f"Features created: {len(self.features)}")
        
        if self.profiles:
            print("\nProfile Details:")
            for i, profile in enumerate(self.profiles):
                status = "✓ Closed" if profile.is_closed else f"✗ Open (gap={profile.closure_gap:.3f}mm)"
                print(f"  {i+1}. {len(profile.edges)} edges, area={profile.area:.2f}mm² - {status}")
        
        if self.features:
            print("\nFeature Details:")
            for i, feature in enumerate(self.features):
                print(f"  {i+1}. {feature.feature_type.upper()}: {feature.operation} (depth={feature.depth}mm)")
        
        if self.error_log:
            print("\nErrors Encountered:")
            for i, error in enumerate(self.error_log, 1):
                print(f"  {i}. {error}")
        
        print("="*60)


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Basic usage
    converter = DXFTo3DConverter('input_sketch.dxf')
    
    if converter.process():
        converter.export_step('output_part.step')
        converter.print_summary()
    else:
        print("\n✗ Conversion failed!")
        converter.print_summary()
    
    print("\n" + "="*60)
    print("USAGE GUIDE")
    print("="*60)
    print("""
📋 CONFIGURATION (config.py):
   - EDGE_CONNECTION_TOLERANCE = 0.1mm (edge chaining)
   - PROFILE_CLOSURE_TOLERANCE = 0.01mm (closure check)
   - DEFAULT_EXTRUDE_DEPTH = 10.0mm
   - DEFAULT_REVOLVE_ANGLE = 360°
   
✏️ DXF ANNOTATION FORMAT:

   EXTRUDE:
     "DEPTH: 50" or "D=50"
     
   REVOLVE:
     "REVOLVE"
     "ANGLE: 270" (optional, default 360°)
     "AXIS: (10, 0)" (optional, default Y-axis at origin)
     
   LOFT:
     "LOFT"
     (requires multiple profiles - NOT YET IMPLEMENTED)
     
   SWEEP:
     "SWEEP"
     (requires path profile - NOT YET IMPLEMENTED)
     
   CUT/ADD:
     "CUT" or "HOLE" (for cuts)
     "BOSS" or "ADD" (for additions)

🔧 VALIDATION:
   - All profiles checked for closure before 3D operations
   - Clear error messages for:
     * Non-closed profiles
     * Missing required inputs
     * Invalid parameters
   - Strict validation can be disabled: Config.ENABLE_STRICT_VALIDATION = False

⚙️ ARCHITECTURE:
   - config.py: All tolerances in one place
   - geometry_parser.py: DXF loading and edge extraction
   - profile_detector.py: Edge chaining and profile detection
   - feature_detector.py: Annotation parsing and feature recognition
   - cad_builder.py: 3D model construction
   - main.py: Workflow orchestration

✅ SUPPORTED:
   - Lines, Arcs, Circles, Polylines, Splines
   - Edge chaining from disconnected segments
   - EXTRUDE with cuts/additions
   - REVOLVE around axes
   
⚠️ NOT YET IMPLEMENTED:
   - LOFT (multi-profile blending)
   - SWEEP (path-based extrusion)
   - These require advanced CadQuery multi-plane operations

📝 ASSUMPTIONS:
   - Spline approximation uses linear interpolation (not true B-spline)
   - Smaller profiles by area are assumed to be holes/cuts
   - Revolve axis is vertical (Z-direction) through specified XY point
   - Edge reversal for chaining assumes conceptual start/end swap
   
🎯 EXAMPLE:
   
   converter = DXFTo3DConverter('part.dxf')
   if converter.process():
       converter.export_step('part.step')
       converter.print_summary()
   else:
       print("Errors:", converter.get_error_log())
    """)