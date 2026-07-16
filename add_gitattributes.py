from pathlib import Path
root=Path('D:/AI/GitHub/Career-Portfolio-2026-v2')
created=[]
for p in root.rglob('.gitignore'):
    g = p.parent / '.gitattributes'
    if not g.exists():
        g.write_text('')
        created.append(str(g))
if created:
    for c in created:
        print(c)
else:
    print('No new .gitattributes created')
print('CREATED_COUNT', len(created))
print('TOTAL', len(list(root.rglob('.gitattributes'))))
