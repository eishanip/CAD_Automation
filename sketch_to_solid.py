# converts FreeCAD Sketch (Sketcher) or Draft wires into 3D solids
# (pad/extrude) and saves outputs.
# sketch_to_solid.py

# Run inside FreeCAD GUI or FreeCADCmd (if running headless, skip GUI-specific calls)
import sys
import FreeCAD
import Part
from FreeCAD import Vector

def sketch_to_face_and_extrude(doc, sketch_obj, thickness):
    # sketch_obj must be a Sketcher object with closed geometry
    try:
        shp = sketch_obj.Shape
        # If sketch produces wires, get the main wire/compound
        wires = [w for w in shp.Wires if w.isClosed()]
        if not wires:
            raise Exception("No closed wires in sketch.")
        # assume the outermost wire is the first closed wire (improve by area test)
        face = Part.Face(wires[0])
        solid = face.extrude(Vector(0,0,thickness))
        part = doc.addObject("Part::Feature", f"Pad_{sketch_obj.Name}")
        part.Shape = solid
        return part
    except Exception as e:
        print("Error:", e)
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: freecadcmd sketch_to_solid.py path/to/Sketch.FCStd thickness_mm")
        return
    fcstd = sys.argv[1]
    thickness = float(sys.argv[2])
    doc = FreeCAD.openDocument(fcstd)
    # Find first sketch object
    sketches = [o for o in doc.Objects if o.TypeId.startswith("Sketcher::Sketch")]
    if not sketches:
        print("No sketches found in document.")
        return
    result = sketch_to_face_and_extrude(doc, sketches[0], thickness)
    if result:
        outpath = os.path.splitext(fcstd)[0] + "_padded.step"
        Part.export([result.Shape], outpath)
        doc.saveAs(os.path.splitext(fcstd)[0] + "_out.FCStd")
        print("Saved:", outpath)
    else:
        print("Failed to create solid.")

if __name__ == "__main__":
    main()