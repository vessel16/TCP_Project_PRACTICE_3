def xor_encrypt(text, key):
    data = text.encode("utf-8")
    key_bytes = key.encode("utf-8")
    result = bytearray()
    for i in range(len(data)):
        result.append(data[i] ^ key_bytes[i % len(key_bytes)])
    return result.hex()


def xor_decrypt(data_hex, key):
    data = bytes.fromhex(data_hex)
    key_bytes = key.encode("utf-8")
    result = bytearray()
    for i in range(len(data)):
        result.append(data[i] ^ key_bytes[i % len(key_bytes)])
    return result.decode("utf-8")