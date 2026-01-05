# CAD_Automation
The following files contain FreeCAD APIs, are FreeCAD specific, and need to be run inside in the integrated terminal of FreeCAD. They cannot be executed using system Python.

1. dxf_to_solid.py
2. sketch_to_solid.py
3. all_apis_tog.py

The following files are universal, and can be executed using system Python.

1. dxf_to_3d_v1.py
2. dxf_to_3d_v2.py

## Installation

1. Save the script as:

   ```bash
   dxf_to_3d_v2.py
   ```

2. Place your DXF file in the same directory:

   ```bash
   input_sketch.dxf
   ```

3. Run:

   ```bash
   python dxf_to_3d_v2.py
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
