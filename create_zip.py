# create_zip.py
# Cria kite_for_life_app.zip contendo os arquivos do projeto na pasta atual.
import zipfile, os

files_to_include = [
    "app.py",
    "create_user.py",
    "create_zip.py",
    "users.json",
    "weights.json",
    "requirements.txt",
    "README.md"
]

zip_name = "kite_for_life_app.zip"

with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files_to_include:
        if os.path.exists(f):
            z.write(f)
            print(f"Adicionado: {f}")
        else:
            print(f"Aviso: arquivo não encontrado e não será adicionado: {f}")

print(f"ZIP criado: {zip_name}")