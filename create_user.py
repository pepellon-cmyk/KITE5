# create_user.py
# Script simples para criar/atualizar usuários locais (users.json)
import json, getpass, hashlib, os

USERS_PATH = "users.json"

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_users():
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(u):
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(u, f, indent=2)

def main():
    users = load_users()
    print("Criar/Atualizar usuário local.")
    username = input("Usuário: ").strip()
    if not username:
        print("Usuário inválido.")
        return
    pwd = getpass.getpass("Senha: ")
    pwd2 = getpass.getpass("Confirmar senha: ")
    if pwd != pwd2:
        print("Senhas não coincidem.")
        return
    users[username] = hash_pw(pwd)
    save_users(users)
    print(f"Usuário '{username}' salvo em {USERS_PATH}.")

if __name__ == "__main__":
    main()