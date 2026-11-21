"""ICMP ping without admin rights.

On Windows it uses IcmpSendEcho from iphlpapi.dll (the same API that ping.exe
uses), so it needs no admin rights, opens no console window and does not depend
on the Windows language. On other systems it falls back to the `ping` command
(only for development).
"""

from __future__ import annotations

import re
import socket
import subprocess
import sys
import time

DEFAULT_TIMEOUT_MS = 1000
_PAYLOAD = b"dota-netcheck-ping-0123456789abc"  # 32 bytes, like Windows ping


def ping(ip: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> float | None:
    """Send one echo request. Returns the round-trip time in ms, or None."""
    try:
        socket.inet_aton(ip)
    except OSError:
        return None
    if sys.platform == "win32":
        return _ping_windows(ip, timeout_ms)
    return _ping_subprocess(ip, timeout_ms)


def ping_series(
    ip: str, count: int, timeout_ms: int = DEFAULT_TIMEOUT_MS, gap_s: float = 0.1
) -> list[float | None]:
    """Send `count` echo requests one after another."""
    results: list[float | None] = []
    for i in range(count):
        results.append(ping(ip, timeout_ms))
        if i < count - 1:
            time.sleep(gap_s)
    return results


# --------------------------------------------------------------------------- #
# Windows: IcmpSendEcho via ctypes
# --------------------------------------------------------------------------- #
_iphlpapi = None


def _load_iphlpapi():
    global _iphlpapi
    if _iphlpapi is not None:
        return _iphlpapi

    import ctypes
    from ctypes import wintypes

    lib = ctypes.WinDLL("iphlpapi.dll", use_last_error=True)
    lib.IcmpCreateFile.argtypes = []
    lib.IcmpCreateFile.restype = wintypes.HANDLE
    lib.IcmpSendEcho.argtypes = [
        wintypes.HANDLE,  # IcmpHandle
        ctypes.c_ulong,  # DestinationAddress (IPAddr, network byte order)
        ctypes.c_void_p,  # RequestData
        wintypes.WORD,  # RequestSize
        ctypes.c_void_p,  # RequestOptions (NULL)
        ctypes.c_void_p,  # ReplyBuffer
        wintypes.DWORD,  # ReplySize
        wintypes.DWORD,  # Timeout (ms)
    ]
    lib.IcmpSendEcho.restype = wintypes.DWORD
    lib.IcmpCloseHandle.argtypes = [wintypes.HANDLE]
    lib.IcmpCloseHandle.restype = wintypes.BOOL
    _iphlpapi = lib
    return lib


def _echo_reply_struct():
    import ctypes

    class IP_OPTION_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("Ttl", ctypes.c_ubyte),
            ("Tos", ctypes.c_ubyte),
            ("Flags", ctypes.c_ubyte),
            ("OptionsSize", ctypes.c_ubyte),
            ("OptionsData", ctypes.c_void_p),
        ]

    class ICMP_ECHO_REPLY(ctypes.Structure):
        _fields_ = [
            ("Address", ctypes.c_ulong),
            ("Status", ctypes.c_ulong),
            ("RoundTripTime", ctypes.c_ulong),
            ("DataSize", ctypes.c_ushort),
            ("Reserved", ctypes.c_ushort),
            ("Data", ctypes.c_void_p),
            ("Options", IP_OPTION_INFORMATION),
        ]

    return ICMP_ECHO_REPLY


_ECHO_REPLY = None


def _ping_windows(ip: str, timeout_ms: int) -> float | None:
    import ctypes

    global _ECHO_REPLY
    if _ECHO_REPLY is None:
        _ECHO_REPLY = _echo_reply_struct()

    lib = _load_iphlpapi()
    handle = lib.IcmpCreateFile()
    invalid = ctypes.c_void_p(-1).value
    if not handle or handle == invalid:
        return None
    try:
        request = ctypes.create_string_buffer(_PAYLOAD, len(_PAYLOAD))
        # reply struct + echoed data + 8 bytes for an ICMP error + some slack
        reply_size = ctypes.sizeof(_ECHO_REPLY) + len(_PAYLOAD) + 8 + 64
        reply_buf = ctypes.create_string_buffer(reply_size)
        # IPAddr is the 4 address bytes in network order, read as a native ULONG
        dest = int.from_bytes(socket.inet_aton(ip), "little")
        count = lib.IcmpSendEcho(
            handle, dest, request, len(_PAYLOAD), None, reply_buf, reply_size, timeout_ms
        )
        if count == 0:
            return None
        reply = _ECHO_REPLY.from_buffer(reply_buf)
        if reply.Status != 0:  # IP_SUCCESS
            return None
        return float(reply.RoundTripTime)
    finally:
        lib.IcmpCloseHandle(handle)


# --------------------------------------------------------------------------- #
# Other systems: the ping command (development only)
# --------------------------------------------------------------------------- #
_TIME_RE = re.compile(r"time[=<]\s*([\d.]+)")


def _ping_subprocess(ip: str, timeout_ms: int) -> float | None:
    secs = max(1, round(timeout_ms / 1000))
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", str(secs), ip],
            capture_output=True,
            text=True,
            timeout=secs + 2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = _TIME_RE.search(proc.stdout)
    if proc.returncode != 0 or not match:
        return None
    return float(match.group(1))
