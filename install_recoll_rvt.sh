#!/bin/sh
d="$1"; [ -d "$d" ] || { echo "no such dir $d"; exit 1; }
grep -q x-revit-project "$d/mimemap" 2>/dev/null || printf '.rvt = application/x-revit-project\n.rfa = application/x-revit-project\n.rte = application/x-revit-project\n.rft = application/x-revit-project\n' >> "$d/mimemap"
echo "done: $d"
