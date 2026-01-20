# CAD_Automation
The following files contain FreeCAD APIs, are FreeCAD specific, and need to be run inside in the integrated terminal of FreeCAD. They cannot be executed using system Python.

1. dxf_to_solid.py
2. sketch_to_solid.py
3. all_apis_tog.py

The following files are universal, and can be executed using system Python.

1. dxf_to_3d_v1.py
2. dxf_to_3d_v2.py
3. dxf_to_3d_FINAL.py

## Installation

1. Save the script as:

   ```bash
   dxf_to_3d_FINAL.py
   ```

2. Place your DXF file in the same directory:

   ```bash
   input_sketch.dxf
   ```

3. Run:

   ```bash
   python dxf_to_3d_FINAL.py
   ```

4. Output:

   ```bash
   output_part.step
   ```

## Open it in:

- FreeCAD
- Fusion 360
- SolidWorks
- CATIA

It is recommended to run the final file using Conda, as PythonOCC and CadQuery are open-source libraries, and not of a stable build so far. Due to this, the code may sometimes return unexpected results.

# Final Divided Scripts as per functionality:

DXF to 3D STEP Converter - Modular Architecture, Annotation-driven with a rule-based fallback approach

## Requirements:
pip install ezdxf cadquery

Project Structure:
- config.py: Configuration and tolerance settings
- geometry_parser.py: DXF parsing and edge extraction
- profile_detector.py: Profile chaining and classification
- feature_detector.py: Feature recognition and annotation parsing
- cad_builder.py: 3D model construction
- main.py: Main converter orchestration

## Usage:
    from dxf_converter import DXFTo3DConverter
    
    converter = DXFTo3DConverter('input_sketch.dxf')
    converter.process()
    converter.export_step('output_part.step')
