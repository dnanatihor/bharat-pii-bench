Output "demo.gif"

Set Shell bash
Set FontSize 20
Set Width 1200
Set Height 720
Set Padding 20
Set TypingSpeed 25ms

Type "uv run bpb run --detectors regex_checksum,regex_checksum+names --task t2 --split dev --seed 42 --out /tmp/bpb-video"
Enter
Sleep 8s

Type@150ms "dir=$(ls -td /tmp/bpb-video/*/ | head -n 1)"
Enter
Sleep 300ms

Type "uv run bpb report $dir"
Enter
Sleep 6s
