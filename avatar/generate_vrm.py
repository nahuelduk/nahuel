#!/usr/bin/env python3
"""
Generador procedural de un avatar VRM 0.x compatible con VSeeFace.

Personaje: dragona estilo anime — pelo largo plateado, heterocromia
(ojo derecho rojo / ojo izquierdo azul), cuernos, alas blancas, cola con
fisica (spring bones), kimono blanco con obi rojo.

Convenciones VRM 0.x (glTF right-handed, Y-up):
  - El modelo mira hacia -Z; la izquierda del personaje es -X.
  - T-pose con rotaciones identidad (solo traslaciones en los nodos).

Salida: DragonaAvatar.vrm (GLB con extension VRM). Sin Blender ni Unity.
"""
import json
import math
import struct
import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------------------
# Paleta
# ----------------------------------------------------------------------------
COL_SKIN       = (1.00, 0.90, 0.84)
COL_SKIN_SHADE = (0.95, 0.76, 0.70)
COL_KIMONO     = (0.97, 0.96, 0.98)
COL_KIMONO_SH  = (0.80, 0.78, 0.88)
COL_RED        = (0.62, 0.16, 0.22)
COL_RED_SH     = (0.42, 0.10, 0.16)
COL_BLUE       = (0.25, 0.55, 0.85)
COL_BLUE_SH    = (0.15, 0.35, 0.62)
COL_HAIR       = (0.92, 0.92, 0.97)
COL_HAIR_SH    = (0.72, 0.72, 0.85)
COL_HORN       = (0.96, 0.93, 0.88)
COL_HORN_SH    = (0.80, 0.75, 0.70)
COL_WING       = (0.96, 0.97, 1.00)
COL_WING_SH    = (0.76, 0.78, 0.92)
COL_WHITE      = (1.00, 1.00, 1.00)
COL_DARK       = (0.23, 0.18, 0.25)
COL_MOUTH      = (0.55, 0.23, 0.28)

# ----------------------------------------------------------------------------
# Esqueleto: posiciones GLOBALES (rotacion identidad en todos los nodos)
# ----------------------------------------------------------------------------
BONES = {}  # name -> (parent, world_pos)

def bone(name, parent, pos):
    BONES[name] = (parent, np.array(pos, dtype=np.float64))

bone("hips",     None,    (0.0, 0.800, 0.0))
bone("spine",    "hips",  (0.0, 0.890, 0.0))
bone("chest",    "spine", (0.0, 1.000, 0.0))
bone("neck",     "chest", (0.0, 1.245, 0.0))
bone("head",     "neck",  (0.0, 1.315, 0.0))
bone("leftEye",  "head",  (-0.042, 1.435, -0.094))
bone("rightEye", "head",  ( 0.042, 1.435, -0.094))

for side, sx in (("left", -1.0), ("right", 1.0)):
    bone(side + "UpperArm", "chest",             (sx * 0.165, 1.185, 0.0))
    bone(side + "LowerArm", side + "UpperArm",   (sx * 0.390, 1.185, 0.0))
    bone(side + "Hand",     side + "LowerArm",   (sx * 0.600, 1.185, 0.0))
    bone(side + "UpperLeg", "hips",              (sx * 0.086, 0.770, 0.0))
    bone(side + "LowerLeg", side + "UpperLeg",   (sx * 0.088, 0.420, 0.0))
    bone(side + "Foot",     side + "LowerLeg",   (sx * 0.088, 0.075, 0.0))

# Cola (cadena con fisica)
TAIL_PATH = [
    (0.0, 0.780, 0.10), (0.0, 0.700, 0.30), (0.0, 0.630, 0.50),
    (0.0, 0.620, 0.68), (0.0, 0.680, 0.82), (0.0, 0.780, 0.92),
]
prev = "hips"
for i, p in enumerate(TAIL_PATH):
    bone(f"tail{i}", prev, p)
    prev = f"tail{i}"

# Alas (cadena corta por ala)
for side, sx in (("L", -1.0), ("R", 1.0)):
    bone(f"wing{side}0", "chest",        (sx * 0.055, 1.130, 0.095))
    bone(f"wing{side}1", f"wing{side}0", (sx * 0.355, 1.410, 0.165))
    bone(f"wing{side}2", f"wing{side}1", (sx * 0.705, 1.580, 0.240))

# Pelo: cadena trasera + mechones laterales (fisica)
bone("hairB0", "head",   (0.0, 1.430, 0.105))
bone("hairB1", "hairB0", (0.0, 1.100, 0.150))
bone("hairB2", "hairB1", (0.0, 0.840, 0.160))
for side, sx in (("L", -1.0), ("R", 1.0)):
    bone(f"hairS{side}0", "head",           (sx * 0.118, 1.400, -0.020))
    bone(f"hairS{side}1", f"hairS{side}0",  (sx * 0.132, 1.050, -0.005))
    bone(f"hairS{side}2", f"hairS{side}1",  (sx * 0.140, 0.840,  0.010))

BONE_NAMES = list(BONES.keys())
BONE_INDEX = {n: i for i, n in enumerate(BONE_NAMES)}   # indice de joint (skin)

def bpos(name):
    return BONES[name][1]

# ----------------------------------------------------------------------------
# Primitivas de geometria
# ----------------------------------------------------------------------------
class Prim:
    """Un primitive glTF: un material, listas de vertices e indices."""
    def __init__(self, material, double_sided=False, textured=False):
        self.material = material
        self.double_sided = double_sided
        self.textured = textured
        self.pos = []      # [(x,y,z)]
        self.uv = []       # [(u,v)] solo si textured
        self.joints = []   # [(j0,j1)]
        self.weights = []  # [(w0,w1)]
        self.tags = []     # [(tag, aux_dict)]
        self.idx = []      # indices (triangulos)

    def add_vertex(self, p, jw, tag=None, aux=None, uv=(0.0, 0.0)):
        self.pos.append(tuple(p))
        (j0, w0), (j1, w1) = jw
        self.joints.append((j0, j1))
        self.weights.append((w0, w1))
        self.tags.append((tag, aux or {}))
        self.uv.append(uv)
        return len(self.pos) - 1

    def add_tri(self, a, b, c):
        self.idx.extend((a, b, c))


def jw1(joint):
    """Peso rigido a un solo hueso."""
    return ((BONE_INDEX[joint], 1.0), (0, 0.0))


def jw2(j0, j1, w0):
    w0 = min(1.0, max(0.0, w0))
    return ((BONE_INDEX[j0], w0), (BONE_INDEX[j1], 1.0 - w0))


def smooth_normals(prim):
    n = np.zeros((len(prim.pos), 3))
    P = np.array(prim.pos)
    tris = np.array(prim.idx).reshape(-1, 3)
    for a, b, c in tris:
        fn = np.cross(P[b] - P[a], P[c] - P[a])
        ln = np.linalg.norm(fn)
        if ln > 1e-12:
            fn = fn / ln
        n[a] += fn; n[b] += fn; n[c] += fn
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    ln[ln < 1e-9] = 1.0
    return n / ln


def lathe(prim, profile, weight_fn, segments=28, xscale=1.0, zscale=1.0,
          zoff_fn=None, cap_top=True, cap_bottom=True, tag=None):
    """Superficie de revolucion alrededor de Y. profile = [(y, r)] de abajo
    hacia arriba. weight_fn(y) -> jw. zoff_fn(y) -> desplazamiento en z."""
    rings = []
    for (y, r) in profile:
        zo = zoff_fn(y) if zoff_fn else 0.0
        ring = []
        for s in range(segments):
            th = 2.0 * math.pi * s / segments
            p = (xscale * r * math.sin(th), y, zscale * r * math.cos(th) + zo)
            ring.append(prim.add_vertex(p, weight_fn(y), tag=tag))
        rings.append(ring)
    for i in range(len(rings) - 1):
        lo, hi = rings[i], rings[i + 1]
        for s in range(segments):
            a, b = lo[s], lo[(s + 1) % segments]
            c, d = hi[(s + 1) % segments], hi[s]
            prim.add_tri(a, b, c)
            prim.add_tri(a, c, d)
    if cap_bottom and profile[0][1] > 1e-6:
        y = profile[0][0]
        zo = zoff_fn(y) if zoff_fn else 0.0
        c = prim.add_vertex((0.0, y, zo), weight_fn(y), tag=tag)
        ring = rings[0]
        for s in range(segments):
            prim.add_tri(c, ring[(s + 1) % segments], ring[s])
    if cap_top and profile[-1][1] > 1e-6:
        y = profile[-1][0]
        zo = zoff_fn(y) if zoff_fn else 0.0
        c = prim.add_vertex((0.0, y, zo), weight_fn(y), tag=tag)
        ring = rings[-1]
        for s in range(segments):
            prim.add_tri(c, ring[s], ring[(s + 1) % segments])


def tube(prim, path, radii, weight_fn, segments=12, tag=None, cap_ends=True):
    """Tubo a lo largo de un camino. weight_fn(t, point) -> jw, t en [0,1]."""
    path = [np.array(p, dtype=np.float64) for p in path]
    n = len(path)
    rings = []
    ref = np.array([0.0, 1.0, 0.0])
    for i, p in enumerate(path):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        t = t / (np.linalg.norm(t) + 1e-12)
        r = ref if abs(np.dot(t, ref)) < 0.95 else np.array([1.0, 0.0, 0.0])
        n1 = np.cross(t, r); n1 /= np.linalg.norm(n1) + 1e-12
        n2 = np.cross(t, n1)
        tt = i / (n - 1)
        ring = []
        for s in range(segments):
            ph = 2.0 * math.pi * s / segments
            q = p + radii[i] * (math.cos(ph) * n1 + math.sin(ph) * n2)
            ring.append(prim.add_vertex(q, weight_fn(tt, q), tag=tag))
        rings.append(ring)
    for i in range(n - 1):
        lo, hi = rings[i], rings[i + 1]
        for s in range(segments):
            a, b = lo[s], lo[(s + 1) % segments]
            c, d = hi[(s + 1) % segments], hi[s]
            prim.add_tri(a, c, b)
            prim.add_tri(a, d, c)
    if cap_ends:
        for (ring, p, flip) in ((rings[0], path[0], False), (rings[-1], path[-1], True)):
            tt = 0.0 if not flip else 1.0
            c = prim.add_vertex(p, weight_fn(tt, p), tag=tag)
            for s in range(segments):
                a, b = ring[s], ring[(s + 1) % segments]
                if flip:
                    prim.add_tri(c, a, b)
                else:
                    prim.add_tri(c, b, a)


def grid_quad(prim, center, w, h, nx, ny, jw, tag=None, z_normal=-1.0,
              uv_rect=None):
    """Rejilla plana en el plano XY mirando a -Z (o +Z). Devuelve ids."""
    cx, cy, cz = center
    ids = []
    for iy in range(ny + 1):
        for ix in range(nx + 1):
            fx = ix / nx
            fy = iy / ny
            p = (cx - w / 2 + w * fx, cy - h / 2 + h * fy, cz)
            uv = (fx, 1.0 - fy)
            if uv_rect:
                u0, v0, u1, v1 = uv_rect
                uv = (u0 + (u1 - u0) * fx, v0 + (v1 - v0) * (1.0 - fy))
            aux = {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "w": w, "h": h}
            ids.append(prim.add_vertex(p, jw, tag=tag, aux=aux, uv=uv))
    stride = nx + 1
    for iy in range(ny):
        for ix in range(nx):
            a = ids[iy * stride + ix]
            b = ids[iy * stride + ix + 1]
            c = ids[(iy + 1) * stride + ix + 1]
            d = ids[(iy + 1) * stride + ix]
            if z_normal < 0:
                prim.add_tri(a, c, b)
                prim.add_tri(a, d, c)
            else:
                prim.add_tri(a, b, c)
                prim.add_tri(a, c, d)
    return ids


def polygon_fan(prim, pts3d, jw_fn, tag=None, flip=False):
    """Poligono triangulado en abanico desde el centroide (doble cara la da
    el material)."""
    C = np.mean(np.array(pts3d), axis=0)
    c = prim.add_vertex(C, jw_fn(C), tag=tag)
    ids = [prim.add_vertex(p, jw_fn(np.array(p)), tag=tag) for p in pts3d]
    n = len(ids)
    for i in range(n):
        a, b = ids[i], ids[(i + 1) % n]
        if flip:
            prim.add_tri(c, b, a)
        else:
            prim.add_tri(c, a, b)


# ----------------------------------------------------------------------------
# Construccion del cuerpo
# ----------------------------------------------------------------------------
def torso_weights(y):
    if y >= 1.10:
        return jw1("chest")
    if y >= 0.97:
        return jw2("chest", "spine", (y - 0.97) / 0.13)
    if y >= 0.86:
        return jw2("spine", "hips", (y - 0.86) / 0.11)
    return jw1("hips")


def build_body_prims():
    prims = {}

    def P(key, material, double_sided=False, textured=False):
        if key not in prims:
            prims[key] = Prim(material, double_sided, textured)
        return prims[key]

    skin   = P("skin", "skin")
    kimono = P("kimono", "kimono")
    red    = P("red", "red")
    hair   = P("hair", "hair")
    hair2  = P("hair2", "hair", double_sided=True)
    horn   = P("horn", "horn")
    wing   = P("wing", "wing", double_sided=True)
    tail   = P("tail", "kimono")
    tailfR = P("tailfR", "red", double_sided=True)
    tailfB = P("tailfB", "blue", double_sided=True)
    sleeve = P("sleeve", "kimono", double_sided=True)

    # ---- cabeza (lathe: menton -> coronilla) --------------------------------
    head_profile = [
        (1.305, 0.042), (1.335, 0.080), (1.365, 0.101), (1.400, 0.117),
        (1.435, 0.126), (1.470, 0.123), (1.505, 0.107), (1.535, 0.072),
        (1.552, 0.000),
    ]
    lathe(skin, head_profile,
          lambda y: jw2("head", "neck", 1.0) if y > 1.3 else jw1("head"),
          segments=30, xscale=1.0, zscale=0.94,
          zoff_fn=lambda y: -0.004, cap_bottom=True, cap_top=False)

    # ---- cuello -------------------------------------------------------------
    lathe(skin, [(1.195, 0.030), (1.340, 0.027)],
          lambda y: jw2("head", "neck", (y - 1.20) / 0.14),
          segments=16, cap_top=False, cap_bottom=False)

    # ---- torso + falda de kimono -------------------------------------------
    kimono_profile = [
        (0.240, 0.150), (0.500, 0.152), (0.760, 0.140), (0.830, 0.132),
        (0.940, 0.108), (1.020, 0.120), (1.090, 0.138), (1.150, 0.120),
        (1.215, 0.062),
    ]
    lathe(kimono, kimono_profile, torso_weights,
          segments=30, xscale=1.10, zscale=0.82,
          cap_top=True, cap_bottom=True)

    # ---- obi (faja roja) + lazo --------------------------------------------
    lathe(red, [(0.925, 0.113), (0.945, 0.116), (0.990, 0.116), (1.010, 0.112)],
          torso_weights, segments=30, xscale=1.11, zscale=0.84,
          cap_top=False, cap_bottom=False)
    # nudo del obi detras
    lathe(red, [(0.930, 0.020), (0.955, 0.052), (0.985, 0.052), (1.005, 0.020)],
          torso_weights, segments=12, xscale=1.4, zscale=0.8,
          zoff_fn=lambda y: 0.125)
    # franja roja en el borde inferior de la falda
    lathe(red, [(0.238, 0.1515), (0.300, 0.1522)], lambda y: jw1("hips"),
          segments=30, xscale=1.102, zscale=0.822,
          cap_top=False, cap_bottom=False)
    # cuello del kimono (banda roja fina)
    lathe(red, [(1.188, 0.064), (1.212, 0.060)], lambda y: jw1("chest"),
          segments=20, xscale=1.05, zscale=0.9,
          cap_top=False, cap_bottom=False)

    # ---- piernas y pies -----------------------------------------------------
    for side, sx in (("left", -1.0), ("right", 1.0)):
        ul, ll, ft = side + "UpperLeg", side + "LowerLeg", side + "Foot"
        x = sx * 0.088

        def leg_w(t, q, ll=ll, ft=ft):
            y = q[1]
            if y > 0.36:
                return jw1(ll)
            if y > 0.12:
                return jw2(ll, ft, (y - 0.12) / 0.24)
            return jw1(ft)

        tube(skin, [(x, 0.470, 0.0), (x, 0.300, 0.0), (x, 0.110, 0.0)],
             [0.048, 0.042, 0.036], leg_w, segments=14)
        # pie (tubo corto hacia -Z con sandalia)
        tube(skin, [(x, 0.050, 0.030), (x, 0.045, -0.050), (x, 0.040, -0.105)],
             [0.042, 0.040, 0.026],
             lambda t, q, ft=ft: jw1(ft), segments=12)

    # ---- brazos: mangas anchas de kimono ------------------------------------
    for side, sx in (("left", -1.0), ("right", 1.0)):
        ua, la, hd = side + "UpperArm", side + "LowerArm", side + "Hand"

        def arm_w(x, ua=ua, la=la, hd=hd):
            ax = abs(x)
            if ax < 0.34:
                return jw2(ua, la, max(0.0, min(1.0, (0.34 - ax) / 0.10)))
            if ax < 0.55:
                return jw2(la, hd, max(0.0, min(1.0, (0.55 - ax) / 0.08)))
            return jw1(hd)

        # manga como tubo horizontal que se ensancha hacia la muneca
        pathx = [0.14, 0.24, 0.34, 0.44, 0.53, 0.585]
        path = [(sx * px, 1.185, 0.0) for px in pathx]
        radii = [0.055, 0.060, 0.066, 0.078, 0.092, 0.096]
        tube(kimono, path, radii,
             lambda t, q: arm_w(q[0]), segments=16, cap_ends=True)
        # panel colgante de la manga (furisode)
        pn = grid_quad(sleeve, (sx * 0.470, 1.055, 0.0), 0.20, 0.26, 3, 3,
                       jw2(la, hd, 0.7), z_normal=-1.0)
        # puno rojo sobre la manga, antes del borde
        cuffpath = [(sx * 0.535, 1.185, 0.0), (sx * 0.568, 1.185, 0.0)]
        tube(red, cuffpath, [0.0945, 0.0965],
             lambda t, q: arm_w(q[0]), segments=16, cap_ends=False)
        # manos
        tube(skin, [(sx * 0.575, 1.185, 0.0), (sx * 0.640, 1.183, 0.0),
                    (sx * 0.665, 1.181, 0.0)],
             [0.030, 0.026, 0.012],
             lambda t, q, hd=hd: jw1(hd), segments=10)

    # ---- pelo ---------------------------------------------------------------
    # casquete (el borde frontal se eleva para despejar la frente)
    cap_profile = [
        (1.385, 0.133), (1.430, 0.137), (1.475, 0.129), (1.515, 0.109),
        (1.548, 0.071), (1.565, 0.000),
    ]
    cap_start = len(hair.pos)
    lathe(hair, cap_profile, lambda y: jw1("head"), segments=30,
          xscale=1.02, zscale=0.99, zoff_fn=lambda y: 0.008,
          cap_bottom=False, cap_top=False)
    for i in range(cap_start, len(hair.pos)):
        x, y, z = hair.pos[i]
        if z < 0.0 and y < 1.50:
            f = min(1.0, (-z) / 0.13) ** 1.6
            hair.pos[i] = (x, y + 0.062 * f * (1.50 - y) / 0.115, z)

    # flequillo: triangulos que cuelgan sobre la frente (delante del casquete)
    bang_data = [(-0.098, 0.050), (-0.064, 0.046), (-0.032, 0.042),
                 (0.0, 0.075), (0.032, 0.042), (0.064, 0.046), (0.098, 0.050)]
    for bx, blen in bang_data:
        w = 0.050
        ztop = -0.121
        zbot = -0.138
        top_l = (bx - w / 2, 1.512, ztop)
        top_r = (bx + w / 2, 1.512, ztop)
        tip   = (bx, 1.512 - blen, zbot)
        a = hair2.add_vertex(top_l, jw1("head"))
        b = hair2.add_vertex(top_r, jw1("head"))
        c = hair2.add_vertex(tip, jw1("head"))
        hair2.add_tri(a, c, b)

    # mechones laterales largos (con fisica)
    for side, sx in (("L", -1.0), ("R", 1.0)):
        s0, s1, s2 = f"hairS{side}0", f"hairS{side}1", f"hairS{side}2"

        def hw(t, q, s0=s0, s1=s1, s2=s2):
            if t < 0.35:
                return jw2(s0, s1, 1.0 - t / 0.35)
            if t < 0.7:
                return jw2(s1, s2, 1.0 - (t - 0.35) / 0.35)
            return jw1(s2)

        path = [(sx * 0.112, 1.460, -0.030), (sx * 0.125, 1.320, -0.045),
                (sx * 0.133, 1.150, -0.030), (sx * 0.138, 0.990, -0.010),
                (sx * 0.142, 0.860, 0.005), (sx * 0.140, 0.800, 0.012)]
        radii = [0.030, 0.033, 0.028, 0.022, 0.014, 0.004]
        tube(hair, path, radii, hw, segments=10)

    # melena trasera (volumen grande con fisica)
    def back_hw(t, q):
        if t < 0.3:
            return jw2("hairB0", "hairB1", 1.0 - t / 0.3)
        if t < 0.65:
            return jw2("hairB1", "hairB2", 1.0 - (t - 0.3) / 0.35)
        return jw1("hairB2")

    back_path = [(0.0, 1.470, 0.045), (0.0, 1.330, 0.105), (0.0, 1.150, 0.135),
                 (0.0, 0.980, 0.150), (0.0, 0.860, 0.150), (0.0, 0.790, 0.140)]
    back_radii = [0.115, 0.125, 0.118, 0.098, 0.070, 0.020]
    # tubo aplastado en z para que sea una melena y no un cilindro
    bp = Prim("hair")
    tube(bp, back_path, back_radii, back_hw, segments=18)
    Pz = np.array(bp.pos)
    Pz[:, 2] = 0.145 + (Pz[:, 2] - np.array([p[2] for p in back_path]).mean()) * 0.55
    # mantener el frente del tubo detras de la cabeza
    base = len(hair.pos)
    for i, p in enumerate(Pz):
        hair.pos.append(tuple(p))
        hair.joints.append(bp.joints[i])
        hair.weights.append(bp.weights[i])
        hair.tags.append(bp.tags[i])
        hair.uv.append(bp.uv[i])
    hair.idx.extend([i + base for i in bp.idx])

    # ---- cuernos ------------------------------------------------------------
    for sx in (-1.0, 1.0):
        path = [(sx * 0.055, 1.520, -0.010), (sx * 0.092, 1.585, 0.020),
                (sx * 0.125, 1.625, 0.075), (sx * 0.148, 1.635, 0.140),
                (sx * 0.158, 1.615, 0.195)]
        radii = [0.030, 0.024, 0.017, 0.010, 0.003]
        tube(horn, path, radii, lambda t, q: jw1("head"), segments=12)

    # ---- alas ---------------------------------------------------------------
    for side, sx in (("L", -1.0), ("R", 1.0)):
        w0, w1, w2 = f"wing{side}0", f"wing{side}1", f"wing{side}2"
        root = bpos(w0)

        def wing_pt(dx, dy):
            # dx: hacia afuera, dy: hacia arriba; barrido hacia atras
            return (root[0] + sx * dx,
                    root[1] + dy,
                    root[2] + dx * 0.22 + abs(dy) * 0.03)

        def wjw(p):
            dx = abs(p[0] - root[0])
            if dx < 0.22:
                return jw2(w0, w1, 1.0 - dx / 0.22)
            if dx < 0.55:
                return jw2(w1, w2, 1.0 - (dx - 0.22) / 0.33)
            return jw1(w2)

        outline = [
            wing_pt(0.00, 0.04), wing_pt(0.20, 0.26), wing_pt(0.44, 0.42),
            wing_pt(0.68, 0.50), wing_pt(0.88, 0.50),          # punta superior
            wing_pt(0.86, 0.36), wing_pt(0.74, 0.28),          # festones
            wing_pt(0.80, 0.12), wing_pt(0.62, 0.10),
            wing_pt(0.64, -0.08), wing_pt(0.46, -0.02),
            wing_pt(0.44, -0.20), wing_pt(0.28, -0.08),
            wing_pt(0.20, -0.22), wing_pt(0.10, -0.08),
            wing_pt(0.02, -0.10),
        ]
        polygon_fan(wing, outline, wjw, flip=(sx > 0))
        # borde de ataque (tubo sobre el borde superior)
        edge = [wing_pt(0.0, 0.04), wing_pt(0.20, 0.26), wing_pt(0.44, 0.42),
                wing_pt(0.68, 0.50), wing_pt(0.88, 0.50)]
        tube(horn, edge, [0.022, 0.019, 0.015, 0.011, 0.004],
             lambda t, q: wjw(q), segments=8)

    # ---- cola ---------------------------------------------------------------
    def tail_w(t, q):
        seg = t * (len(TAIL_PATH) - 1)
        i = int(min(len(TAIL_PATH) - 2, seg))
        f = seg - i
        return jw2(f"tail{i}", f"tail{i + 1}", 1.0 - f)

    tpath = [(0.0, 0.800, 0.06)] + TAIL_PATH
    tradii = [0.055, 0.052, 0.046, 0.038, 0.028, 0.018, 0.008]
    tube(tail, tpath, tradii, tail_w, segments=14)
    # abanico de la punta: media pluma roja y media azul
    tip = np.array(TAIL_PATH[-1])
    fanR = [tuple(tip), (0.035, tip[1] + 0.10, tip[2] + 0.06),
            (0.012, tip[1] + 0.13, tip[2] + 0.10)]
    fanB = [tuple(tip), (-0.035, tip[1] + 0.10, tip[2] + 0.06),
            (-0.012, tip[1] + 0.13, tip[2] + 0.10)]
    polygon_fan(tailfR, fanR, lambda p: jw1("tail5"))
    polygon_fan(tailfB, fanB, lambda p: jw1("tail5"), flip=True)

    return prims


# ----------------------------------------------------------------------------
# Cara (malla con morph targets)
# ----------------------------------------------------------------------------
MORPHS = ["a", "i", "u", "e", "o", "blink_l", "blink_r",
          "smile", "frown", "brow_angry", "brow_sad", "brow_up"]

EYE_Y = 1.437
EYE_W = 0.058
EYE_H = 0.050
EYE_X = 0.049
FACE_Z = -0.112       # plano de la cara (delante de la malla de la cabeza)


def build_face_prims():
    prims = {}

    def P(key, material, double_sided=False, textured=False):
        if key not in prims:
            prims[key] = Prim(material, double_sided, textured)
        return prims[key]

    sclera = P("sclera", "sclera")
    irisL  = P("irisL", "irisL", textured=True)
    irisR  = P("irisR", "irisR", textured=True)
    lid    = P("lid", "skin")
    dark   = P("dark", "dark", double_sided=True)
    mouth  = P("mouth", "mouth", double_sided=True)

    for side, sx, iris, eb in (("l", -1.0, irisL, "leftEye"),
                               ("r", 1.0, irisR, "rightEye")):
        cx = sx * EYE_X
        # blanco del ojo (esquinas recogidas para redondear)
        sc_start = len(sclera.pos)
        grid_quad(sclera, (cx, EYE_Y, FACE_Z - 0.001), EYE_W, EYE_H, 2, 2,
                  jw1("head"), tag=f"eye_{side}")
        for vi in range(sc_start, len(sclera.pos)):
            tg, aux = sclera.tags[vi]
            if aux.get("fx") in (0.0, 1.0) and aux.get("fy") in (0.0, 1.0):
                x, y, z = sclera.pos[vi]
                sclera.pos[vi] = (x, y + (EYE_Y - y) * 0.45, z)
        # iris (skinneado al hueso del ojo para el lookAt)
        grid_quad(iris, (cx, EYE_Y - 0.002, FACE_Z - 0.0022), 0.041, 0.047,
                  1, 1, jw1(eb), tag=f"iris_{side}", uv_rect=(0, 0, 1, 1))
        # pestana superior (linea oscura fija)
        grid_quad(dark, (cx, EYE_Y + EYE_H / 2 + 0.0015, FACE_Z - 0.0030),
                  EYE_W + 0.012, 0.0075, 2, 1, jw1("head"), tag=f"lash_{side}")
        # parpado (piel) colapsado arriba; baja con blink
        grid_quad(lid, (cx, EYE_Y + EYE_H / 2 + 0.0008, FACE_Z - 0.0038),
                  EYE_W + 0.014, 0.0016, 2, 1, jw1("head"), tag=f"lid_{side}")
        # borde del parpado (linea que baja con el blink)
        grid_quad(dark, (cx, EYE_Y + EYE_H / 2 - 0.0002, FACE_Z - 0.0040),
                  EYE_W + 0.014, 0.0028, 2, 1, jw1("head"), tag=f"lidline_{side}")
        # ceja (delante del flequillo, curvada siguiendo la cabeza)
        br_start = len(dark.pos)
        grid_quad(dark, (cx, EYE_Y + 0.041, -0.135), 0.055, 0.010,
                  4, 1, jw1("head"), tag=f"brow_{side}")
        for vi in range(br_start, len(dark.pos)):
            x, y, z = dark.pos[vi]
            # delante del flequillo en el centro, plegada hacia la cara afuera
            zz = -0.1365 + max(0.0, abs(x) - 0.055) * 1.9
            dark.pos[vi] = (x, y, zz)

    # boca (rejilla para poder deformarla)
    grid_quad(mouth, (0.0, 1.356, -0.1045), 0.028, 0.006, 8, 2,
              jw1("head"), tag="mouth")

    return prims


def clamp(v, a, b):
    return max(a, min(b, v))


def face_morph_delta(morph, tag, aux, pos):
    """Devuelve (dx, dy, dz) para un vertice de la cara en un morph."""
    x, y, z = pos
    d = (0.0, 0.0, 0.0)
    if tag == "mouth":
        fx, fy = aux["fx"], aux["fy"]
        mx = x - aux["cx"]
        t = 2.0 * fx - 1.0
        if morph == "a":
            return (mx * -0.10, (-0.034 if fy < 0.01 else (-0.016 if fy < 0.6 else 0.004)) , 0.0)
        if morph == "i":
            return (mx * 0.60, (fy - 0.5) * 0.004, 0.0)
        if morph == "u":
            return (mx * -0.45, -0.013 if fy < 0.01 else (0.005 if fy > 0.9 else -0.004), 0.0)
        if morph == "e":
            return (mx * 0.30, -0.018 if fy < 0.01 else 0.002, 0.0)
        if morph == "o":
            return (mx * -0.32, -0.026 if fy < 0.01 else (0.006 if fy > 0.9 else -0.010), 0.0)
        if morph == "smile":
            return (mx * 0.18, 0.017 * t * t - (0.005 * (1.0 - t * t) if fy < 0.01 else 0.0), 0.0)
        if morph == "frown":
            return (mx * -0.05, -0.013 * t * t, 0.0)
        return d
    if tag == "lid_l" and morph == "blink_l" or tag == "lid_r" and morph == "blink_r":
        # cortina de piel: el borde inferior baja, el superior queda fijo
        if aux["fy"] < 0.5:
            return (0.0, -(EYE_H + 0.004), 0.0)
        return (0.0, -0.0012, 0.0)
    if tag == "lidline_l" and morph == "blink_l" or tag == "lidline_r" and morph == "blink_r":
        # la linea oscura del parpado viaja entera hacia abajo
        return (0.0, -(EYE_H + 0.002), 0.0)
    if tag and tag.startswith("brow_"):
        side = tag[-1]
        fx = aux["fx"]
        # "interior" = lado hacia la nariz
        inner = fx if side == "l" else (1.0 - fx)
        # brow_l esta en x<0: fx=1 es el lado interior (hacia x=0)?
        # grid va de -w/2 a +w/2 en x: para el ojo izquierdo (x<0),
        # el interior (cerca de la nariz) es fx=1; para el derecho, fx=0.
        if morph == "brow_angry":
            return (0.0, -0.020 * inner + 0.004 * (1.0 - inner), 0.0)
        if morph == "brow_sad":
            return (0.0, 0.016 * inner - 0.003 * (1.0 - inner), 0.0)
        if morph == "brow_up":
            return (0.0, 0.012, 0.0)
    return d


# ----------------------------------------------------------------------------
# Texturas (iris con heterocromia)
# ----------------------------------------------------------------------------
def make_iris_png(base_rgb, size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = cy = size / 2
    R = size * 0.46
    br, bg, bb = [int(c * 255) for c in base_rgb]
    # anillo exterior oscuro -> centro claro
    steps = 60
    for i in range(steps, 0, -1):
        f = i / steps
        rr = R * f
        k = 0.35 + 0.65 * (1.0 - f) ** 1.2
        col = (int(br * k), int(bg * k), int(bb * k), 255)
        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
    # destellos radiales suaves
    hi = (min(255, br + 70), min(255, bg + 70), min(255, bb + 70), 90)
    for a in range(0, 360, 20):
        x2 = cx + R * 0.9 * math.cos(math.radians(a))
        y2 = cy + R * 0.9 * math.sin(math.radians(a))
        dr.line([cx, cy, x2, y2], fill=hi, width=3)
    # pupila
    pr = R * 0.34
    dr.ellipse([cx - pr, cy - pr * 1.25, cx + pr, cy + pr * 1.25],
               fill=(20, 12, 22, 255))
    # sombra superior (parpado)
    sh = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    ds.ellipse([cx - R, cy - R, cx + R, cy - R * 0.15], fill=(10, 5, 15, 110))
    img = Image.alpha_composite(img, sh)
    # brillo principal y secundario
    gr = R * 0.30
    dr = ImageDraw.Draw(img)
    dr.ellipse([cx - R * 0.55 - gr / 2, cy - R * 0.5 - gr / 2,
                cx - R * 0.55 + gr / 2, cy - R * 0.5 + gr / 2],
               fill=(255, 255, 255, 235))
    gr2 = R * 0.16
    dr.ellipse([cx + R * 0.35 - gr2 / 2, cy + R * 0.35 - gr2 / 2,
                cx + R * 0.35 + gr2 / 2, cy + R * 0.35 + gr2 / 2],
               fill=(255, 255, 255, 170))
    img = img.filter(ImageFilter.GaussianSmooth if hasattr(ImageFilter, 'GaussianSmooth') else ImageFilter.SMOOTH)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Materiales
# ----------------------------------------------------------------------------
def material_defs():
    """(nombre, color, shade, doubleSided, texture_key, cutout)"""
    return [
        ("skin",   COL_SKIN,   COL_SKIN_SHADE, False, None,    False),
        ("kimono", COL_KIMONO, COL_KIMONO_SH,  False, None,    False),
        ("red",    COL_RED,    COL_RED_SH,     True,  None,    False),
        ("blue",   COL_BLUE,   COL_BLUE_SH,    True,  None,    False),
        ("hair",   COL_HAIR,   COL_HAIR_SH,    True,  None,    False),
        ("horn",   COL_HORN,   COL_HORN_SH,    False, None,    False),
        ("wing",   COL_WING,   COL_WING_SH,    True,  None,    False),
        ("sclera", COL_WHITE,  (0.85, 0.85, 0.9), False, None, False),
        ("irisL",  COL_WHITE,  (0.7, 0.7, 0.8), False, "irisL", True),
        ("irisR",  COL_WHITE,  (0.7, 0.7, 0.8), False, "irisR", True),
        ("dark",   COL_DARK,   (0.12, 0.09, 0.14), True, None,  False),
        ("mouth",  COL_MOUTH,  (0.35, 0.14, 0.18), True, None,  False),
    ]


# ----------------------------------------------------------------------------
# Ensamblado glTF / GLB
# ----------------------------------------------------------------------------
class GltfBuilder:
    def __init__(self):
        self.blob = bytearray()
        self.bufferViews = []
        self.accessors = []

    def _pad(self, align=4):
        while len(self.blob) % align:
            self.blob.append(0)

    def add_view(self, data, target=None):
        self._pad()
        off = len(self.blob)
        self.blob.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bufferViews.append(v)
        return len(self.bufferViews) - 1

    def add_accessor(self, arr, comp, ctype, target, minmax=False):
        data = arr.astype(comp).tobytes()
        view = self.add_view(data, target)
        ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[ctype]
        count = arr.size // ncomp
        acc = {"bufferView": view, "byteOffset": 0, "count": count,
               "type": ctype,
               "componentType": {np.float32: 5126, np.uint16: 5123,
                                 np.uint32: 5125}[comp]}
        if minmax:
            a2 = arr.reshape(-1, ncomp)
            acc["min"] = [float(x) for x in a2.min(axis=0)]
            acc["max"] = [float(x) for x in a2.max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1


def build():
    body_prims = build_body_prims()
    face_prims = build_face_prims()

    mats = material_defs()
    mat_index = {m[0]: i for i, m in enumerate(mats)}

    g = GltfBuilder()

    # --- texturas ---
    iris_l_png = make_iris_png(COL_BLUE)    # ojo izquierdo azul
    iris_r_png = make_iris_png((0.85, 0.30, 0.18))  # ojo derecho rojo ambar
    images = []
    tex_index = {}
    for key, png in (("irisL", iris_l_png), ("irisR", iris_r_png)):
        view = g.add_view(png)
        images.append({"bufferView": view, "mimeType": "image/png",
                       "name": key})
        tex_index[key] = len(images) - 1

    samplers = [{"magFilter": 9729, "minFilter": 9987,
                 "wrapS": 33071, "wrapT": 33071}]
    textures = [{"sampler": 0, "source": tex_index["irisL"], "name": "irisL"},
                {"sampler": 0, "source": tex_index["irisR"], "name": "irisR"}]
    tex_slot = {"irisL": 0, "irisR": 1}

    # --- materiales glTF + MToon ---
    materials = []
    material_properties = []
    for (name, col, shade, dbl, tex, cutout) in mats:
        m = {"name": name, "doubleSided": dbl,
             "pbrMetallicRoughness": {
                 "baseColorFactor": [col[0], col[1], col[2], 1.0],
                 "metallicFactor": 0.0, "roughnessFactor": 0.9}}
        if tex:
            m["pbrMetallicRoughness"]["baseColorTexture"] = {
                "index": tex_slot[tex]}
        if cutout:
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = 0.5
        materials.append(m)

        fp = {"_Cutoff": 0.5 if cutout else 0.0, "_BumpScale": 1.0,
              "_ReceiveShadowRate": 1.0, "_ShadingGradeRate": 1.0,
              "_ShadeShift": 0.0, "_ShadeToony": 0.92,
              "_LightColorAttenuation": 0.0, "_IndirectLightIntensity": 0.1,
              "_RimLightingMix": 0.2, "_RimFresnelPower": 5.0, "_RimLift": 0.0,
              "_OutlineWidth": 0.0, "_OutlineScaledMaxDistance": 1.0,
              "_OutlineLightingMix": 1.0, "_DebugMode": 0.0,
              "_BlendMode": 1.0 if cutout else 0.0,
              "_OutlineWidthMode": 0.0, "_OutlineColorMode": 0.0,
              "_CullMode": 0.0 if dbl else 2.0, "_OutlineCullMode": 1.0,
              "_SrcBlend": 1.0, "_DstBlend": 0.0, "_ZWrite": 1.0}
        vp = {"_Color": [col[0], col[1], col[2], 1.0],
              "_ShadeColor": [shade[0], shade[1], shade[2], 1.0],
              "_EmissionColor": [0.0, 0.0, 0.0, 1.0],
              "_OutlineColor": [0.0, 0.0, 0.0, 1.0],
              "_RimColor": [0.12, 0.12, 0.18, 1.0]}
        tp = {}
        if tex:
            tp["_MainTex"] = tex_slot[tex]
        kw = {}
        tag = {"RenderType": "Opaque"}
        if cutout:
            kw["_ALPHATEST_ON"] = True
            tag["RenderType"] = "TransparentCutout"
        material_properties.append({
            "name": name, "shader": "VRM/MToon",
            "renderQueue": 2450 if cutout else 2000,
            "floatProperties": fp, "vectorProperties": vp,
            "textureProperties": tp, "keywordMap": kw, "tagMap": tag})

    # --- nodos ---
    nodes = []
    name_to_node = {}
    for n in BONE_NAMES:
        parent, wp = BONES[n]
        local = wp - (BONES[parent][1] if parent else np.zeros(3))
        nodes.append({"name": n, "translation": [float(x) for x in local],
                      "children": []})
        name_to_node[n] = len(nodes) - 1
    for n in BONE_NAMES:
        parent = BONES[n][0]
        if parent:
            nodes[name_to_node[parent]]["children"].append(name_to_node[n])

    # --- skin ---
    ibms = np.zeros((len(BONE_NAMES), 16), dtype=np.float32)
    for i, n in enumerate(BONE_NAMES):
        wp = BONES[n][1]
        m = np.identity(4)
        m[3, 0], m[3, 1], m[3, 2] = -wp[0], -wp[1], -wp[2]  # column-major
        ibms[i] = m.flatten()
    ibm_acc = g.add_accessor(ibms.flatten(), np.float32, "MAT4", None)

    # --- mallas ---
    def emit_mesh(prim_dict, with_morphs):
        primitives = []
        prim_list = list(prim_dict.values())
        for prim in prim_list:
            P = np.array(prim.pos, dtype=np.float32)
            N = smooth_normals(prim).astype(np.float32)
            J = np.zeros((len(prim.pos), 4), dtype=np.uint16)
            W = np.zeros((len(prim.pos), 4), dtype=np.float32)
            for i, ((j0, j1), (w0, w1)) in enumerate(zip(prim.joints,
                                                          prim.weights)):
                J[i, 0], J[i, 1] = j0, j1
                W[i, 0], W[i, 1] = w0, w1
            attrs = {
                "POSITION": g.add_accessor(P.flatten(), np.float32, "VEC3",
                                           34962, minmax=True),
                "NORMAL": g.add_accessor(N.flatten(), np.float32, "VEC3",
                                         34962),
                "JOINTS_0": g.add_accessor(J.flatten(), np.uint16, "VEC4",
                                           34962),
                "WEIGHTS_0": g.add_accessor(W.flatten(), np.float32, "VEC4",
                                            34962),
            }
            if prim.textured:
                UV = np.array(prim.uv, dtype=np.float32)
                attrs["TEXCOORD_0"] = g.add_accessor(UV.flatten(), np.float32,
                                                     "VEC2", 34962)
            idx = np.array(prim.idx, dtype=np.uint32)
            p = {"attributes": attrs,
                 "indices": g.add_accessor(idx, np.uint32, "SCALAR", 34963),
                 "material": prim.material_index, "mode": 4}
            if with_morphs:
                targets = []
                for morph in MORPHS:
                    D = np.zeros((len(prim.pos), 3), dtype=np.float32)
                    for i, (tag, aux) in enumerate(prim.tags):
                        D[i] = face_morph_delta(morph, tag, aux, prim.pos[i])
                    targets.append({"POSITION": g.add_accessor(
                        D.flatten(), np.float32, "VEC3", 34962, minmax=True)})
                p["targets"] = targets
            primitives.append(p)
        mesh = {"primitives": primitives}
        if with_morphs:
            mesh["weights"] = [0.0] * len(MORPHS)
            mesh["extras"] = {"targetNames": MORPHS}
        return mesh

    for prim in list(body_prims.values()) + list(face_prims.values()):
        prim.material_index = mat_index[prim.material]

    meshes = [emit_mesh(body_prims, False), emit_mesh(face_prims, True)]

    # nodos de malla + raiz
    body_node = len(nodes)
    nodes.append({"name": "Body", "mesh": 0, "skin": 0})
    face_node = len(nodes)
    nodes.append({"name": "Face", "mesh": 1, "skin": 0})
    root_node = len(nodes)
    nodes.append({"name": "Root",
                  "children": [name_to_node["hips"], body_node, face_node]})

    skins = [{"inverseBindMatrices": ibm_acc,
              "skeleton": name_to_node["hips"],
              "joints": [name_to_node[n] for n in BONE_NAMES]}]

    # --- VRM: huesos humanoides ---
    HUMAN_MAP = [
        ("hips", "hips"), ("spine", "spine"), ("chest", "chest"),
        ("neck", "neck"), ("head", "head"),
        ("leftEye", "leftEye"), ("rightEye", "rightEye"),
        ("leftUpperArm", "leftUpperArm"), ("leftLowerArm", "leftLowerArm"),
        ("leftHand", "leftHand"),
        ("rightUpperArm", "rightUpperArm"), ("rightLowerArm", "rightLowerArm"),
        ("rightHand", "rightHand"),
        ("leftUpperLeg", "leftUpperLeg"), ("leftLowerLeg", "leftLowerLeg"),
        ("leftFoot", "leftFoot"),
        ("rightUpperLeg", "rightUpperLeg"), ("rightLowerLeg", "rightLowerLeg"),
        ("rightFoot", "rightFoot"),
    ]
    human_bones = [{"bone": hb, "node": name_to_node[n],
                    "useDefaultValues": True} for hb, n in HUMAN_MAP]

    # --- VRM: blendshapes ---
    def binds(*pairs):
        return [{"mesh": 1, "index": MORPHS.index(m), "weight": w}
                for m, w in pairs]

    blend_groups = [
        {"name": "Neutral", "presetName": "neutral", "binds": [],
         "materialValues": []},
        {"name": "A", "presetName": "a", "binds": binds(("a", 100)),
         "materialValues": []},
        {"name": "I", "presetName": "i", "binds": binds(("i", 100)),
         "materialValues": []},
        {"name": "U", "presetName": "u", "binds": binds(("u", 100)),
         "materialValues": []},
        {"name": "E", "presetName": "e", "binds": binds(("e", 100)),
         "materialValues": []},
        {"name": "O", "presetName": "o", "binds": binds(("o", 100)),
         "materialValues": []},
        {"name": "Blink", "presetName": "blink",
         "binds": binds(("blink_l", 100), ("blink_r", 100)),
         "materialValues": []},
        {"name": "Blink_L", "presetName": "blink_l",
         "binds": binds(("blink_l", 100)), "materialValues": []},
        {"name": "Blink_R", "presetName": "blink_r",
         "binds": binds(("blink_r", 100)), "materialValues": []},
        {"name": "Joy", "presetName": "joy",
         "binds": binds(("smile", 100), ("blink_l", 100), ("blink_r", 100)),
         "materialValues": []},
        {"name": "Angry", "presetName": "angry",
         "binds": binds(("brow_angry", 100), ("frown", 100)),
         "materialValues": []},
        {"name": "Sorrow", "presetName": "sorrow",
         "binds": binds(("brow_sad", 100), ("frown", 70)),
         "materialValues": []},
        {"name": "Fun", "presetName": "fun",
         "binds": binds(("smile", 70), ("brow_up", 100)),
         "materialValues": []},
        {"name": "LookUp", "presetName": "lookup", "binds": [],
         "materialValues": []},
        {"name": "LookDown", "presetName": "lookdown", "binds": [],
         "materialValues": []},
        {"name": "LookLeft", "presetName": "lookleft", "binds": [],
         "materialValues": []},
        {"name": "LookRight", "presetName": "lookright", "binds": [],
         "materialValues": []},
    ]

    # --- VRM: fisica (spring bones) ---
    collider_groups = [
        {"node": name_to_node["head"],
         "colliders": [{"offset": {"x": 0.0, "y": 0.11, "z": 0.0},
                        "radius": 0.13}]},
        {"node": name_to_node["chest"],
         "colliders": [{"offset": {"x": 0.0, "y": 0.08, "z": 0.0},
                        "radius": 0.13}]},
    ]
    bone_groups = [
        {"comment": "hair", "stiffiness": 0.62, "gravityPower": 0.03,
         "gravityDir": {"x": 0.0, "y": -1.0, "z": 0.0}, "dragForce": 0.42,
         "center": -1, "hitRadius": 0.025,
         "bones": [name_to_node["hairB0"], name_to_node["hairSL0"],
                   name_to_node["hairSR0"]],
         "colliderGroups": [0, 1]},
        {"comment": "tail", "stiffiness": 0.42, "gravityPower": 0.08,
         "gravityDir": {"x": 0.0, "y": -1.0, "z": 0.0}, "dragForce": 0.38,
         "center": -1, "hitRadius": 0.04,
         "bones": [name_to_node["tail0"]], "colliderGroups": []},
        {"comment": "wings", "stiffiness": 0.88, "gravityPower": 0.0,
         "gravityDir": {"x": 0.0, "y": -1.0, "z": 0.0}, "dragForce": 0.6,
         "center": -1, "hitRadius": 0.03,
         "bones": [name_to_node["wingL0"], name_to_node["wingR0"]],
         "colliderGroups": []},
    ]

    vrm = {
        "exporterVersion": "dragona-vrm-generator-1.0",
        "specVersion": "0.0",
        "meta": {
            "title": "Dragona Cosmica",
            "version": "1.0",
            "author": "nahuel",
            "contactInformation": "",
            "reference": "",
            "texture": -1,
            "allowedUserName": "OnlyAuthor",
            "violentUssageName": "Disallow",
            "sexualUssageName": "Disallow",
            "commercialUssageName": "Disallow",
            "otherPermissionUrl": "",
            "licenseName": "Other",
            "otherLicenseUrl": "",
        },
        "humanoid": {
            "humanBones": human_bones,
            "armStretch": 0.05, "legStretch": 0.05,
            "upperArmTwist": 0.5, "lowerArmTwist": 0.5,
            "upperLegTwist": 0.5, "lowerLegTwist": 0.5,
            "feetSpacing": 0.0, "hasTranslationDoF": False,
        },
        "firstPerson": {
            "firstPersonBone": name_to_node["head"],
            "firstPersonBoneOffset": {"x": 0.0, "y": 0.06, "z": 0.0},
            "meshAnnotations": [],
            "lookAtTypeName": "Bone",
            "lookAtHorizontalInner": {"curve": [0, 0, 0, 1, 1, 1, 1, 0],
                                      "xRange": 90.0, "yRange": 8.0},
            "lookAtHorizontalOuter": {"curve": [0, 0, 0, 1, 1, 1, 1, 0],
                                      "xRange": 90.0, "yRange": 12.0},
            "lookAtVerticalDown": {"curve": [0, 0, 0, 1, 1, 1, 1, 0],
                                   "xRange": 90.0, "yRange": 10.0},
            "lookAtVerticalUp": {"curve": [0, 0, 0, 1, 1, 1, 1, 0],
                                 "xRange": 90.0, "yRange": 10.0},
        },
        "blendShapeMaster": {"blendShapeGroups": blend_groups},
        "secondaryAnimation": {"boneGroups": bone_groups,
                               "colliderGroups": collider_groups},
        "materialProperties": material_properties,
    }

    gltf = {
        "asset": {"version": "2.0", "generator": "dragona-vrm-generator"},
        "scene": 0,
        "scenes": [{"nodes": [root_node]}],
        "nodes": nodes,
        "meshes": meshes,
        "skins": skins,
        "materials": materials,
        "images": images,
        "samplers": samplers,
        "textures": textures,
        "buffers": [{"byteLength": 0}],
        "bufferViews": g.bufferViews,
        "accessors": g.accessors,
        "extensionsUsed": ["VRM"],
        "extensions": {"VRM": vrm},
    }

    g._pad()
    gltf["buffers"][0]["byteLength"] = len(g.blob)

    js = json.dumps(gltf, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    bin_chunk = bytes(g.blob)
    total = 12 + 8 + len(js) + 8 + len(bin_chunk)
    out = bytearray()
    out += struct.pack("<III", 0x46546C67, 2, total)
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(bin_chunk), 0x004E4942) + bin_chunk
    return bytes(out)


if __name__ == "__main__":
    data = build()
    out = "DragonaAvatar.vrm"
    with open(out, "wb") as f:
        f.write(data)
    print(f"OK -> {out} ({len(data) / 1024:.1f} KiB)")
