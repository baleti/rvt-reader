import math
from OCP.gp import gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.TopoDS import TopoDS
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.ShapeFix import ShapeFix_Solid, ShapeFix_Shell
from OCP.BRepLib import BRepLib
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

def poly_face(loops):
    def wire(pts):
        w = BRepBuilderAPI_MakePolygon()
        for p in pts: w.Add(gp_Pnt(*p))
        w.Close(); return w.Wire()
    def area(pts):
        a = 0.0; n = len(pts)
        # projected polygon area magnitude via cross sum
        sx = sy = sz = 0.0
        for i in range(n):
            p, q = pts[i], pts[(i + 1) % n]
            sx += p[1] * q[2] - p[2] * q[1]; sy += p[2] * q[0] - p[0] * q[2]; sz += p[0] * q[1] - p[1] * q[0]
        return math.sqrt(sx * sx + sy * sy + sz * sz) / 2
    ls = sorted(loops, key=lambda l: -area(l))
    f = BRepBuilderAPI_MakeFace(wire(ls[0]), True)
    for h in ls[1:]: f.Add(wire(h))
    return f.Face()

def solid_from_faces(faces3d, tol=1e-5):
    """faces3d: list of loop-lists (planar). Returns (volume, area, bbox, closed_flag)"""
    sew = BRepBuilderAPI_Sewing(tol)
    n = 0
    for loops in faces3d:
        if not loops: continue
        try: sew.Add(poly_face(loops)); n += 1
        except Exception: pass
    if n == 0: return None
    sew.Perform(); sh = sew.SewedShape()
    # shell(s)
    exp = TopExp_Explorer(sh, TopAbs_SHELL); vol = 0.0; closed = True; found = 0
    shapes = []
    while exp.More():
        shell = TopoDS.Shell(exp.Current()); found += 1
        ms = BRepBuilderAPI_MakeSolid(shell); so = ms.Solid()
        fx = ShapeFix_Solid(so); fx.Perform(); so2 = fx.Solid()
        try: BRepLib.OrientClosedSolid_s(TopoDS.Solid(so2))
        except Exception: pass
        g = GProp_GProps(); BRepGProp.VolumeProperties_s(so2, g)
        shapes.append(abs(g.Mass())); exp.Next()
    g2 = GProp_GProps(); BRepGProp.SurfaceProperties_s(sh, g2)
    b = Bnd_Box(); BRepBndLib.Add_s(sh, b)
    return {'volumes': shapes, 'area': g2.Mass(), 'shells': found, 'bbox': [b.CornerMin().X(), b.CornerMin().Y(), b.CornerMin().Z(), b.CornerMax().X(), b.CornerMax().Y(), b.CornerMax().Z()]}
