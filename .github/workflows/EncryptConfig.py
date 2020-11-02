# coding: utf-8

import argparse
import os
from cryptography.fernet import Fernet


def Encrypt(path):
    key = Fernet.generate_key()
    f = Fernet(key)

    dir, name = os.path.split(path)
    name_noext = os.path.splitext(os.path.basename(path))[0]
    new_name = name.replace(name_noext, "encrypt")
    new_key = name.replace(name_noext, "key")
    new_path = os.path.join(dir, new_name)
    new_key_path = os.path.join(dir, new_key)

    with open(path, "rb") as fin:
        with open(new_path, "wb") as fout:
            token = f.encrypt(fin.read())
            fout.write(token)
    with open(new_key_path, "wb") as fout:
        fout.write(key)
    return 0


def Decrypt(path, key):
    dir, name = os.path.split(path)
    name_noext = os.path.splitext(os.path.basename(path))[0]
    new_name = name.replace(name_noext, "decrypt")
    new_path = os.path.join(dir, new_name)

    f = Fernet(key)

    with open(path, "rb") as fin:
        with open(new_path, "wb") as fout:
            token = f.decrypt(fin.read())
            fout.write(token)
    return 0


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Encrypt Config")
    arg_parser.add_argument("--path", help="target file")
    arg_parser.add_argument("--key", help="encrypt/decrypt key", default="")
    args = arg_parser.parse_args()
    
    # arg_parser.print_help()

    if args.key == "":
        Encrypt(args.path)
    else:
        Decrypt(args.path, str(args.key).encode())
