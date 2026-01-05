import FreeCAD, Part, importDXF
from FreeCAD import Vector

doc = FreeCAD.newDocument("Convert")

# 1) Import DXF
importDXF.insert("input.dxf", "Convert")
doc.recompute()

# 2) Collect closed wires
wires = []
for obj in doc.Objects:
    if hasattr(obj, "Shape"):
        for w in obj.Shape.Wires:
            if w.isClosed():
                wires.append(w)

# 3) Convert wire → face → solid
solids = []
for w in wires:
    face = Part.Face(w)
    solid = face.extrude(Vector(0,0,10))
    pf = doc.addObject("Part::Feature", "Extrusion")
    pf.Shape = solid
    solids.append(pf)

doc.recompute()

# 4) Export
Part.export([s.Shape for s in solids], "output.step")
doc.saveAs("output.FCStd")