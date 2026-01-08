import hashlib
import struct
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Your task-specific unknown bytes
UNKNOWN_FILE_OFF = 0x11E9
UNKNOWN_LEN = 8

# ELF constants (only what we need)
EI_CLASS = 4
EI_DATA = 5
ELFCLASS64 = 2
ELFDATA2LSB = 1

SHT_NOBITS = 8
SHT_NOTE = 7

NT_GNU_BUILD_ID = 3

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def u64(b, o): return struct.unpack_from("<Q", b, o)[0]

def align4(x: int) -> int:
    return (x + 3) & ~3

def print_hex_rows(data: bytes, row=16):
    for i in range(0, len(data), row):
        chunk = data[i:i+row]
        print(f"{i:08x}: " + " ".join(f"{b:02x}" for b in chunk))

@dataclass
class Ehdr64:
    e_ident: bytes
    e_type: int
    e_machine: int
    e_version: int
    e_entry: int
    e_phoff: int
    e_shoff: int
    e_flags: int
    e_ehsize: int
    e_phentsize: int
    e_phnum: int
    e_shentsize: int
    e_shnum: int
    e_shstrndx: int

    def pack_external(self, zero_phoff_shoff: bool = False) -> bytes:
        # ELF64_Ehdr layout (little-endian)
        phoff = 0 if zero_phoff_shoff else self.e_phoff
        shoff = 0 if zero_phoff_shoff else self.e_shoff
        return struct.pack(
            "<16sHHIQQQIHHHHHH",
            self.e_ident,
            self.e_type,
            self.e_machine,
            self.e_version,
            self.e_entry,
            phoff,
            shoff,
            self.e_flags,
            self.e_ehsize,
            self.e_phentsize,
            self.e_phnum,
            self.e_shentsize,
            self.e_shnum,
            self.e_shstrndx,
        )

@dataclass
class Phdr64:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int

    def pack_external(self) -> bytes:
        # ELF64_Phdr layout
        return struct.pack("<IIQQQQQQ",
            self.p_type,
            self.p_flags,
            self.p_offset,
            self.p_vaddr,
            self.p_paddr,
            self.p_filesz,
            self.p_memsz,
            self.p_align,
        )

@dataclass
class Shdr64:
    sh_name: int
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int

    def pack_external(self, zero_offset: bool = False) -> bytes:
        off = 0 if zero_offset else self.sh_offset
        # ELF64_Shdr layout
        return struct.pack("<IIQQQQIIQQ",
            self.sh_name,
            self.sh_type,
            self.sh_flags,
            self.sh_addr,
            off,
            self.sh_size,
            self.sh_link,
            self.sh_info,
            self.sh_addralign,
            self.sh_entsize,
        )

def parse_ehdr64(data: bytes) -> Ehdr64:
    if data[:4] != b"\x7fELF":
        raise ValueError("Not an ELF file")
    if data[EI_CLASS] != ELFCLASS64:
        raise ValueError("Not ELF64")
    if data[EI_DATA] != ELFDATA2LSB:
        raise ValueError("Not little-endian")

    e_ident = data[:16]
    # Offsets from ELF64 spec
    e_type      = u16(data, 0x10)
    e_machine   = u16(data, 0x12)
    e_version   = u32(data, 0x14)
    e_entry     = u64(data, 0x18)
    e_phoff     = u64(data, 0x20)
    e_shoff     = u64(data, 0x28)
    e_flags     = u32(data, 0x30)
    e_ehsize    = u16(data, 0x34)
    e_phentsize = u16(data, 0x36)
    e_phnum     = u16(data, 0x38)
    e_shentsize = u16(data, 0x3A)
    e_shnum     = u16(data, 0x3C)
    e_shstrndx  = u16(data, 0x3E)

    return Ehdr64(
        e_ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
        e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
    )

def parse_phdrs64(data: bytes, eh: Ehdr64) -> List[Phdr64]:
    phdrs = []
    for i in range(eh.e_phnum):
        off = eh.e_phoff + i * eh.e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from(
            "<IIQQQQQQ", data, off
        )
        phdrs.append(Phdr64(p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align))
    return phdrs

def parse_shdrs64(data: bytes, eh: Ehdr64) -> List[Shdr64]:
    shdrs = []
    for i in range(eh.e_shnum):
        off = eh.e_shoff + i * eh.e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack_from(
            "<IIQQQQIIQQ", data, off
        )
        shdrs.append(Shdr64(
            sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
            sh_link, sh_info, sh_addralign, sh_entsize
        ))
    return shdrs

def get_section_names(data: bytes, eh: Ehdr64, shdrs: List[Shdr64]) -> List[str]:
    # Read section header string table
    shstr = shdrs[eh.e_shstrndx]
    blob = data[shstr.sh_offset: shstr.sh_offset + shstr.sh_size]

    names = []
    for sh in shdrs:
        start = sh.sh_name
        end = blob.find(b"\x00", start)
        if end == -1:
            names.append("")
        else:
            names.append(blob[start:end].decode(errors="replace"))
    return names

def find_buildid_desc_by_section(data: bytes, shdrs: List[Shdr64], names: List[str]) -> Tuple[int, int]:
    """
    Find .note.gnu.build-id as a section (SHT_NOTE) and parse its notes to locate
    (file_offset_of_desc, desc_size) for NT_GNU_BUILD_ID with name "GNU".
    """
    for sh, nm in zip(shdrs, names):
        if nm != ".note.gnu.build-id":
            continue
        if sh.sh_type != SHT_NOTE:
            # still try, but normally it is SHT_NOTE
            pass
        blob = data[sh.sh_offset: sh.sh_offset + sh.sh_size]
        i = 0
        n = len(blob)
        while i + 12 <= n:
            namesz, descsz, ntype = struct.unpack_from("<III", blob, i)
            i += 12
            name_start = i
            name_end = name_start + namesz
            if name_end > n:
                break
            name = blob[name_start:name_end].rstrip(b"\x00")
            i = align4(name_end)

            desc_start = i
            desc_end = desc_start + descsz
            if desc_end > n:
                break
            i = align4(desc_end)

            if name == b"GNU" and ntype == NT_GNU_BUILD_ID:
                return sh.sh_offset + desc_start, descsz

    raise RuntimeError("Could not find NT_GNU_BUILD_ID desc inside .note.gnu.build-id section")

def read_stored_buildid(data: bytes, shdrs: List[Shdr64], names: List[str]) -> bytes:
    off, sz = find_buildid_desc_by_section(data, shdrs, names)
    return data[off:off+sz]

def get_prefix_suffix_preprocessed_like_ld(data: bytes):
    # parse ELF header, program headers, section headers, and section names
    eh = parse_ehdr64(data)
    phdrs = parse_phdrs64(data, eh)
    shdrs = parse_shdrs64(data, eh)
    names = get_section_names(data, eh, shdrs)

    prefix_parts = []
    suffix_parts = []

    # ld hashes the ELF header, but with e_phoff/e_shoff set to 0
    prefix_parts.append(eh.pack_external(zero_phoff_shoff=True))

    # then ld hashes all program headers
    for ph in phdrs:
        prefix_parts.append(ph.pack_external())

    # unknown byte range in the file: [u0, u1)
    u0 = UNKNOWN_FILE_OFF
    u1 = UNKNOWN_FILE_OFF + UNKNOWN_LEN

    # this variable indicates whether we have already passed the unknown bytes
    # in the hash input stream
    # in this task, the unknown range lies inside .text, so the switch is triggered only once
    unknown_bytes_passed = False

    # next, ld iterates over section headers and section contents
    for i, sh in enumerate(shdrs):
        sec_start = sh.sh_offset
        sec_end = sh.sh_offset + sh.sh_size

        # the section header always comes in the stream before the section contents,
        # so before the unknown bytes it goes to the prefix, and after them to the suffix
        if unknown_bytes_passed:
            suffix_parts.append(sh.pack_external(zero_offset=True))
        else:
            prefix_parts.append(sh.pack_external(zero_offset=True))

        # skip sections without file data or with zero size
        if sh.sh_type == SHT_NOBITS or sh.sh_size == 0:
            continue

        # these sections were not taken into account when reproducing ld behavior in this task
        if names[i] in (".strtab", ".shstrtab", ".symtab"):
            continue

        # the .note.gnu.build-id section is fully zeroed during hashing
        if names[i] == ".note.gnu.build-id" and sh.sh_type == SHT_NOTE:
            sec = b"\x00" * sh.sh_size
        else:
            sec = data[sec_start:sec_end]

        # split section contents if the unknown range lies inside this section:
        # bytes before the unknown go to the prefix, bytes after the unknown go to the suffix
        if sec_start <= u0 and u1 <= sec_end:
            prefix_parts.append(sec[:u0 - sec_start])     # before unknown
            suffix_parts.append(sec[u1 - sec_start:])     # after unknown
            unknown_bytes_passed = True
        else:
            # section is entirely before the unknown range
            if sec_end <= u0:
                prefix_parts.append(sec)
            # section is entirely after the unknown range
            elif sec_start >= u1:
                suffix_parts.append(sec)

    return b"".join(prefix_parts), b"".join(suffix_parts)

def brute_unknown_fast(prefix, suffix, target_hex, alphabet: bytes, unknown_len=8):
    import hashlib, itertools
    target = bytes.fromhex(target_hex)

    h_prefix = hashlib.sha1() 
    h_prefix.update(prefix)
    tested = 0
    for tup in itertools.product(alphabet, repeat=unknown_len):
        h = h_prefix.copy()
        h.update(bytes(tup))   
        h.update(suffix)
        tested += 1
        if tested % 5_000_000 == 0:
            print("tested", tested)
        if h.digest() == target:
            return bytes(tup)
    return None

def main(path: str, mode: str="", candidate: Optional[str] = None):
    raw = open(path, "rb").read()

    eh = parse_ehdr64(raw)
    shdrs = parse_shdrs64(raw, eh)
    names = get_section_names(raw, eh, shdrs)

    stored = read_stored_buildid(raw, shdrs, names)
    print("Stored Build ID (from file):", stored.hex())


    prefix, suffix = get_prefix_suffix_preprocessed_like_ld(raw)
    alphabet =b"0123456789abcdef"
    result = brute_unknown_fast(prefix, suffix, stored.hex(), alphabet, 8)
    print(result)
    return

if __name__ == "__main__":
    path = sys.argv[1]
    main(path)