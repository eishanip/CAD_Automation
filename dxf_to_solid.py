# CLI/macro that imports a 2D DXF (or reads already-imported Draft objects),
# converts closed profiles to faces, extrudes to solids, optionally exports
# STEP/STEP and .FCStd.

# dxf_to_solid.py
# Usage (inside FreeCAD): FreeCADCmd dxf_to_solid.py path/to/input.dxf path/to/output.step [thickness_mm]
import sys
import os
import FreeCAD
import Part
import Draft
import importDXF        # FreeCAD module for DXF import (typically available in FreeCAD's python env)
from FreeCAD import Vector

def import_dxf(doc, filepath):
    # insert DXF objects into the doc
    # importDXF.insert is the common entrypoint used in scripts
    importDXF.insert(filepath, doc.Name)
    return True

def collect_closed_shapes(doc):
    closed_shapes = []
    for obj in doc.Objects:
        try:
            shp = obj.Shape
        except Exception:
            continue
        # Only consider planar wires / edges that can be made into faces
        if shp.Edges:
            # If a wire or compound is closed, its projected 2D wire can make a face
            # We will attempt to convert each wire to a face when possible
            for w in shp.Wires:
                if w.isClosed():
                    closed_shapes.append(w)
    return closed_shapes

def make_solids_from_wires(doc, wires, thickness):
    created = []
    for i, w in enumerate(wires):
        try:
            face = Part.Face(w)                  # make face from closed wire
            solid = face.extrude(Vector(0,0,thickness))
            obj = doc.addObject("Part::Feature", f"Extruded_{i}")
            obj.Label = f"Extruded_{i}"
            obj.Shape = solid
            created.append(obj)
        except Exception as e:
            print("Failed to extrude wire:", e)
    return created

def export_solids(doc, objs, outpath):
    shapes = [o.Shape for o in objs]
    Part.export(shapes, outpath)
    print("Exported to", outpath)

def main():
    if len(sys.argv) < 3:
        print("Usage: freecadcmd dxf_to_solid.py input.dxf output.step [thickness_mm]")
        return
    infile = sys.argv[1]
    outfile = sys.argv[2]
    thickness = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    doc = FreeCAD.newDocument("DXFConvert")
    import_dxf(doc, infile)
    FreeCAD.ActiveDocument.recompute()
    wires = collect_closed_shapes(doc)
    if not wires:
        print("No closed wires found. Check layers and scale of DXF.")
        return
    solids = make_solids_from_wires(doc, wires, thickness)
    if solids:
        export_solids(doc, solids, outfile)
    else:
        print("No solids created.")

if __name__ == "__main__":
    main()