# ============================================================================
# feature_detector.py - Feature Recognition and Annotation Parsing
# ============================================================================

import re


class FeatureInfo:
    """Information about a recognized CAD feature"""
    
    def __init__(self, profile: Profile, feature_type: str, 
                 operation: str = 'extrude', depth: float = 10.0,
                 axis: Optional[Tuple[float, float]] = None,
                 angle: float = 360.0):
        self.profile = profile
        self.feature_type = feature_type  # 'base', 'hole', 'pocket', 'boss'
        self.operation = operation  # 'extrude', 'cut', 'revolve', 'loft', 'sweep'
        self.depth = depth
        self.direction = 'normal'
        self.axis = axis  # For revolve: (x, y) axis position
        self.angle = angle  # For revolve: rotation angle in degrees
        self.loft_profiles = []  # For loft: additional profiles
        self.path_profile = None  # For sweep: path curve


class FeatureDetector:
    """Handles annotation parsing and feature detection"""
    
    def __init__(self, msp):
        self.msp = msp
        self.annotations = {}
    
    def extract_annotations(self) -> dict:
        """Parse TEXT and DIMENSION entities for annotations"""
        print("\nExtracting annotations...")
        
        # Extract TEXT entities
        for text in self.msp.query('TEXT'):
            content = text.dxf.text.upper()
            position = (text.dxf.insert.x, text.dxf.insert.y)
            
            # Parse depth annotations: "DEPTH: 50", "D=50", "EXTRUDE 50"
            depth_match = re.search(r'(?:DEPTH|D|EXTRUDE)[\s:=]+(\d+\.?\d*)', content)
            if depth_match:
                depth_value = float(depth_match.group(1))
                self.annotations['depth'] = depth_value
                print(f"  Found depth: {depth_value}mm at {position}")
            
            # Parse operation type
            if 'REVOLVE' in content:
                self.annotations['operation'] = 'revolve'
                print(f"  Found operation: REVOLVE")
                
                # Extract revolve angle
                angle_match = re.search(r'(?:ANGLE)[\s:=]+(\d+\.?\d*)', content)
                if angle_match:
                    self.annotations['revolve_angle'] = float(angle_match.group(1))
                    print(f"    Angle: {self.annotations['revolve_angle']}°")
            
            elif 'LOFT' in content:
                self.annotations['operation'] = 'loft'
                print(f"  Found operation: LOFT")
            
            elif 'SWEEP' in content:
                self.annotations['operation'] = 'sweep'
                print(f"  Found operation: SWEEP")
            
            elif 'CUT' in content or 'HOLE' in content:
                self.annotations['operation'] = 'cut'
                print(f"  Found operation: CUT")
            
            elif 'BOSS' in content or 'PROTRUSION' in content:
                self.annotations['operation'] = 'add'
                print(f"  Found operation: ADD")
            
            elif 'BASE' in content:
                self.annotations['base_feature'] = True
                print(f"  Found: BASE feature marker")
            
            # Parse axis for revolve: "AXIS: (10, 0)"
            axis_match = re.search(r'AXIS[\s:=]+\((\d+\.?\d*),\s*(\d+\.?\d*)\)', content)
            if axis_match:
                self.annotations['axis'] = (float(axis_match.group(1)), float(axis_match.group(2)))
                print(f"  Found axis: {self.annotations['axis']}")
        
        # Extract DIMENSION entities
        for dim in self.msp.query('DIMENSION'):
            if hasattr(dim.dxf, 'text') and dim.dxf.text:
                try:
                    value = float(dim.dxf.text)
                    if 'dimensions' not in self.annotations:
                        self.annotations['dimensions'] = []
                    self.annotations['dimensions'].append(value)
                except ValueError:
                    pass
        
        print(f"✓ Extracted {len(self.annotations)} annotation entries")
        return self.annotations
    
    def detect_features(self, profiles: List[Profile]) -> List[FeatureInfo]:
        """Detect features from profiles and annotations"""
        print("\nDetecting features...")
        
        if not profiles:
            print("✗ No profiles found for feature detection!")
            return []
        
        features = []
        
        # Get parameters from annotations
        operation = self.annotations.get('operation', 'extrude')
        depth = self.annotations.get('depth', Config.DEFAULT_EXTRUDE_DEPTH)
        
        # Create base feature based on operation
        if operation == 'revolve':
            angle = self.annotations.get('revolve_angle', Config.DEFAULT_REVOLVE_ANGLE)
            axis = self.annotations.get('axis', None)
            
            base_feature = FeatureInfo(
                profile=profiles[0],
                feature_type='base',
                operation='revolve',
                depth=0,
                axis=axis,
                angle=angle
            )
            features.append(base_feature)
            print(f"  Base feature: REVOLVE (angle={angle}°, axis={axis})")
        
        elif operation == 'loft':
            if len(profiles) >= 2:
                base_feature = FeatureInfo(
                    profile=profiles[0],
                    feature_type='base',
                    operation='loft',
                    depth=depth
                )
                base_feature.loft_profiles = profiles[1:]
                features.append(base_feature)
                print(f"  Base feature: LOFT ({len(profiles)} profiles)")
            else:
                print(f"  ⚠ LOFT requires multiple profiles, found only {len(profiles)}")
                print(f"    Not falling back to extrude - please add more profiles or change operation")
                return []
        
        elif operation == 'sweep':
            if len(profiles) >= 2:
                base_feature = FeatureInfo(
                    profile=profiles[0],
                    feature_type='base',
                    operation='sweep',
                    depth=0
                )
                base_feature.path_profile = profiles[1]
                features.append(base_feature)
                print(f"  Base feature: SWEEP (cross-section + path)")
            else:
                print(f"  ⚠ SWEEP requires 2 profiles (cross-section + path), found only {len(profiles)}")
                print(f"    Not falling back to extrude - please add path profile or change operation")
                return []
        
        else:  # Default: extrude
            base_feature = FeatureInfo(
                profile=profiles[0],
                feature_type='base',
                operation='extrude',
                depth=depth
            )
            features.append(base_feature)
            print(f"  Base feature: EXTRUDE (depth={depth}mm)")
            
            # Additional profiles as cuts/additions
            for i, profile in enumerate(profiles[1:], 1):
                cut_op = self.annotations.get('operation', 'cut')
                feature = FeatureInfo(
                    profile=profile,
                    feature_type='hole' if cut_op == 'cut' else 'boss',
                    operation=cut_op,
                    depth=depth
                )
                features.append(feature)
                print(f"  Feature {i}: {cut_op.upper()} (depth={depth}mm)")
        
        print(f"✓ Detected {len(features)} features")
        return features
