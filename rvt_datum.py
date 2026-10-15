#!/usr/bin/env python3
"""Find DatumPlane-derived elements (levels, grids, reference planes) in decoded partitions.
Anchor: Element's 8 ElementIds + 3 bools immediately precede DatumPlane.m_text (u32 len + UTF-16). m_id is validated against Global/ElemTable."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import olefile
from rvtfmt import inflate_stream
from rvt_elements import load_partitions, read_str, PR if False else None
