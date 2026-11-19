import zipfile
from pathlib import Path

root = Path.cwd()
output = Path.home() / "Downloads" / "cloud-voting-full-v8.zip"

with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
    for folder in ["app", "migrations"]:
        for file in (root / folder).rglob("*"):
            if file.is_file():
                z.write(file, file.relative_to(root).as_posix())

    for filename in ["application.py", "Procfile", "requirements.txt"]:
        z.write(root / filename, filename)

print(f"Created: {output}")
