#!/usr/bin/env bash
cd "$(dirname "$0")/.." || exit 1
T=$(mktemp -d)
chk(){ if "${@:2}" >/dev/null 2>&1; then echo "  OK     $1"; else echo "  FALLA  $1"; fi; }

printf '@startuml\n!include <C4/C4_Container>\nPerson(u,"U")\nSystem(s,"S")\nRel(u,s,"Usa","HTTPS")\n@enduml\n' > $T/t.puml
echo 'a -> b: hola' > $T/t.d2
printf 'Table a {\n  id int [pk]\n}\nTable b {\n  id int [pk]\n  a_id int\n}\nRef: b.a_id > a.id\n' > $T/t.dbml
cat > $T/t.py <<PY
import diagrams.azure.network as m
from diagrams import Diagram
cls = next(getattr(m, n) for n in dir(m) if "Gateway" in n)
with Diagram("s", filename="$T/smoke", outformat="svg", show=False):
    cls("ok")
PY

chk "graphviz"              dot -V
chk "java"                  java -version
chk "plantuml + C4 -> svg"  bash -c "java -jar tools/plantuml.jar -tsvg $T/t.puml && test -s $T/t.svg"
chk "python diagrams (Azure)" bash -c "python $T/t.py && test -s $T/smoke.svg"
chk "d2 con ELK -> svg"     bash -c "d2 --layout=elk $T/t.d2 $T/t_d2.svg && test -s $T/t_d2.svg"
chk "dbml2sql"              bash -c "dbml2sql $T/t.dbml | grep -qi 'create table'"
chk "dbml-renderer -> svg"  bash -c "dbml-renderer -i $T/t.dbml -o $T/t_db.svg && test -s $T/t_db.svg"
chk "pandoc"                pandoc --version
echo "Archivos de prueba en: $T"
