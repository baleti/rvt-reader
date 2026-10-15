one() { f="$1"; n=$(echo "$f" | tr / _); s=$(date +%s); timeout 1100 python3 rvt2text.py "$f" > "t2t/$n.txt" 2> "t2t/$n.err"; rc=$?; echo "$rc $(( $(date +%s) - s )) $f" >> t2t/_status.log; }
