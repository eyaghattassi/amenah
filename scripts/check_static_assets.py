import os
import re
import sys
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(BASE, 'templates', 'index.html')
STATIC = os.path.join(BASE, 'static')

def main() -> int:
    if not os.path.isfile(INDEX):
        print('Fichier introuvable :', INDEX)
        return 1
    text = open(INDEX, encoding='utf-8').read()
    raw = re.findall('["\\\']((?:/)?static/[^"\\\']+)["\\\']', text)
    rels = []
    for p in raw:
        p = p.lstrip('/')
        if not p.startswith('static/'):
            continue
        if p.endswith(('.js', '.css')) and '/img/' not in p:
            continue
        rels.append(p)
    missing = []
    for rel in sorted(set(rels)):
        full = os.path.join(BASE, *rel.split('/'))
        if not os.path.isfile(full):
            missing.append(rel)
    if not missing:
        print('OK : tous les assets listés existent sous static/')
        return 0
    print('Manquants (%d fichiers) — à placer sous le dossier du projet :\n' % len(missing))
    for m in missing:
        print(' ', m)
    print('\nDossier static du projet :', STATIC)
    print('Ex. fichier attendu : static/img/nike.png')
    print('         chemin :', os.path.join(STATIC, 'img', 'nike.png'))
    return 2
if __name__ == '__main__':
    sys.exit(main())
