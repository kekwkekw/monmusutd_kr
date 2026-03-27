import hashlib

# 몬무스 TD 전용 복호화 키
MASTER_KEY_SEED = "KYSSTMDL"

def base_key(src: str) -> bytes:
    """몬무스 전용 베이스 키 생성"""
    s2 = bytes(b ^ 0x55 for b in src.encode("ascii"))
    sha = hashlib.sha256(s2).digest()
    s4 = bytes(b ^ 0xAA for b in sha)
    return s4[::2] + s4[1::2]

def decrypt_monmusu(data: bytes) -> bytes:
    """XOR 스트림 복호화 수행"""
    first32 = base_key(MASTER_KEY_SEED)
    full64 = first32 + first32[::-1]
    
    klen = len(full64)
    key_int = int.from_bytes(full64, "little")
    out = bytearray(len(data))
    
    for i in range(0, len(data), klen):
        chunk = data[i : i + klen]
        if len(chunk) == klen:
            chunk_int = int.from_bytes(chunk, "little") ^ key_int
            out[i : i + klen] = chunk_int.to_bytes(klen, "little")
        else:
            out[i:] = bytes(b ^ full64[j] for j, b in enumerate(chunk))
    return bytes(out)