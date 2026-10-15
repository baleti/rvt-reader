"""Solids / faces rebuilt with OpenCascade (cadquery-ocp) from decoded curve geometry. Units: feet."""
import math
from OCP.gp import gp_Pnt, gp_Vec, gp_Dir, gp_Ax2, gp_Circ
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import rvt_geom as Gm

def curve_pts(c):
    """(start, end, midpoint-ish, kind) 3D points of a line or arc record"""
    p = c['m_endParams']
    if Gm.is_line(c):
        o = c['m_origin']; d = c['m_dirVec']
        pt = lambda t: tuple(o[i] + d[i] * t for i in range(3))
        return pt(p[0]), pt(p[1]), pt((p[0] + p[1]) / 2)
    ce = c['m_center']; r = c['m_radius']; x = c['m_xVec']; y = c['m_yVec']
    pt = lambda t: tuple(ce[i] + r * (math.cos(t) * x[i] + math.sin(t) * y[i]) for i in range(3))
    return pt(p[0]), pt(p[1]), pt((p[0] + p[1]) / 2)

def _close(a, b, tol=1e-4): return all(abs(a[i] - b[i]) < tol for i in range(3))

def chain_loops(curves):
    """group curves into closed loops by endpoint matching -> list of lists of (start, end, mid)"""
    segs = [curve_pts(c) for c in curves]; used = [False] * len(segs); loops = []
    for i in range(len(segs)):
        if used[i]: continue
        used[i] = True; loop = [segs[i]]; cur = segs[i][1]; start = segs[i][0]; guard = 0
        while not _close(cur, start) and guard < len(segs) + 2:
            guard += 1
            for j in range(len(segs)):
                if used[j]: continue
                a, b, m = segs[j]
                if _close(a, cur): used[j] = True; loop.append(segs[j]); cur = b; break
                if _close(b, cur): used[j] = True; loop.append((b, a, m)); cur = a; break
            else: break
        if _close(cur, start): loops.append(loop)
        else: return None
    return loops

def edge_of(seg):
    a, b, m = seg
    if _close(m, tuple((a[i] + b[i]) / 2 for i in range(3)), 1e-7):    # straight
        return BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge()
    from OCP.GC import GC_MakeArcOfCircle
    return BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(gp_Pnt(*a), gp_Pnt(*m), gp_Pnt(*b)).Value()).Edge()

def wire_of(loop):
    w = BRepBuilderAPI_MakeWire()
    for s in loop: w.Add(edge_of(s))
    return w.Wire()

def planar_face(loops):
    """loops: outer first (largest bbox area); returns TopoDS_Face with holes"""
    wires = [wire_of(l) for l in loops]
    def size(l):
        xs = [p[i] for s in l for p in s[:2] for i in range(3)]
        return 0
    f = BRepBuilderAPI_MakeFace(wires[0], True)
    from OCP.TopoDS import TopoDS
    for w in wires[1:]:
        f.Add(w)
    return f.Face()

def props_surface(shape):
    g = GProp_GProps(); BRepGProp.SurfaceProperties_s(shape, g); return g.Mass(), g.CentreOfMass()
def props_volume(shape):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, g); return g.Mass(), g.CentreOfMass()
def perimeter(loops):
    from OCP.BRepGProp import BRepGProp as B
    tot = 0.0
    for l in loops:
        for s in l:
            g = GProp_GProps(); B.LinearProperties_s(edge_of(s), g); tot += g.Mass()
    return tot
def bbox(shape):
    b = Bnd_Box(); BRepBndLib.Add_s(shape, b); return b.Get()
def extrude(face, vec):
    return BRepPrimAPI_MakePrism(face, gp_Vec(*vec)).Shape()
