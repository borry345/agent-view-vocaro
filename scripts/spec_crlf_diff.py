import re
S = r"C:\Users\SSAFY\Desktop\borry\agentview\agentview\SPEC.md"
Pr = r"C:\Users\SSAFY\Desktop\borry\agentview\agentview\PRD.md"
b = open(S, "rb").read()
print("before lines:", b.count(b"\n"), "CRLF:", b.count(b"\r\n"))
if b.count(b"\r\n") == 0:
    b = b.replace(b"\n", b"\r\n"); open(S, "wb").write(b)
print("after lines:", b.count(b"\n"), "CRLF:", b.count(b"\r\n"), "lone LF:", b.count(b"\n")-b.count(b"\r\n"), "CRCR:", b.count(b"\r\r"))
def ids(path):
    t = open(path, encoding="utf-8").read()
    rows = re.findall(r"^\|\s*(F\d+)\s*\|\s*([^|]+?)\s*\|", t, re.M)
    d = {}
    for k, v in rows: d.setdefault(k, v)
    return d
p, s = ids(Pr), ids(S)
print("PRD ids:", len(p), "SPEC ids:", len(s))
for k in sorted(set(p)|set(s), key=lambda x:int(x[1:])):
    if p.get(k) != s.get(k): print("DIFF", k, "| PRD:", p.get(k), "| SPEC:", s.get(k))
print("diff check done")
