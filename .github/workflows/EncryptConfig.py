# coding: utf-8

import argparse
import os
from pathlib import Path

from cryptography.fernet import Fernet


def Encrypt(path: str, key: str = "") -> int:
    if key == "":
        key = Fernet.generate_key()
    else:
        key = str(key).encode()
    f = Fernet(key)

    if path == "":
        return -1
    sd = Path(path)
    if not sd.is_file():
        return -1

    new_path = (sd.parent / sd.name.replace(sd.stem, "encrypt_" + sd.stem)).absolute()
    new_key_path = (sd.parent / sd.name.replace(sd.stem, "key_" + sd.stem)).absolute()

    with open(sd, "rb") as fin:
        with open(new_path, "wb") as fout:
            token = f.encrypt(fin.read())
            fout.write(token)
    with open(new_key_path, "wb") as fout:
        fout.write(key)
    
    print("Encrypt success -> ({}, {})".format(new_path.name, new_key_path.name))
    return 0


def Decrypt(path: str, key: str):
    if path == "":
        return -1
    sd = Path(path)
    if not sd.is_file():
        return -1

    new_path = (sd.parent / sd.name.replace(sd.stem, "decrypt")).absolute()

    if key == "":
        return -1
    f = Fernet(str(key).encode())

    with open(sd, "rb") as fin:
        with open(new_path, "wb") as fout:
            token = f.decrypt(fin.read())
            fout.write(token)

    print("Decrypt success -> ({})".format(new_path.name))
    return 0


if __name__ == "__main__":
    os.chdir(Path(__file__).absolute().parent)
    arg_parser = argparse.ArgumentParser(description="Encrypt Config")
    arg_parser.add_argument("--path", help="target file", default="")
    arg_parser.add_argument("--key", help="encrypt/decrypt key", default="")
    arg_parser.add_argument("--type", help="encrypt or decrypt", default="")
    args = arg_parser.parse_args()
    
    if args.type == "encrypt":
        Encrypt(args.path, args.key)
    elif args.type == "decrypt":
        Decrypt(args.path, args.key)
    else:
        arg_parser.print_help()
