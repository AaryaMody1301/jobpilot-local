from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class ProcessOwnershipError(RuntimeError):
    pass


class ManagedProcess:
    pid: int

    def poll(self) -> int | None:
        raise NotImplementedError

    def wait(self, timeout: float | None = None) -> int:
        raise NotImplementedError

    def terminate(self) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class _PosixProcess(ManagedProcess):
    process: subprocess.Popen[bytes]

    @property
    def pid(self) -> int:
        return self.process.pid

    def poll(self) -> int | None:
        return self.process.poll()

    def wait(self, timeout: float | None = None) -> int:
        return self.process.wait(timeout=timeout)

    def terminate(self) -> None:
        if self.poll() is not None:
            return
        try:
            os.killpg(self.pid, signal.SIGTERM)
        except ProcessLookupError:
            return


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    CREATE_SUSPENDED = 0x00000004
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JobObjectExtendedLimitInformation = 9
    INFINITE = 0xFFFFFFFF
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102
    STILL_ACTIVE = 259

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class _PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _kernel32.SetInformationJobObject.restype = wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _kernel32.ResumeThread.restype = wintypes.DWORD
    _kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    _kernel32.TerminateProcess.restype = wintypes.BOOL
    _kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    _kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    _kernel32.WaitForSingleObject.restype = wintypes.DWORD
    _kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CreateProcessW.restype = wintypes.BOOL
    _kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(_STARTUPINFOW),
        ctypes.POINTER(_PROCESS_INFORMATION),
    ]

    def _raise_last_error(message: str) -> None:
        code = ctypes.get_last_error()
        raise ProcessOwnershipError(f"{message}; Windows error {code}")

    @dataclass(slots=True)
    class _WindowsProcess(ManagedProcess):
        process_handle: object
        pid: int
        _closed: bool = False

        def poll(self) -> int | None:
            if self._closed:
                return 0
            code = wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(self.process_handle, ctypes.byref(code)):
                _raise_last_error("GetExitCodeProcess failed")
            return None if code.value == STILL_ACTIVE else int(code.value)

        def wait(self, timeout: float | None = None) -> int:
            milliseconds = INFINITE if timeout is None else max(0, int(timeout * 1000))
            result = _kernel32.WaitForSingleObject(self.process_handle, milliseconds)
            if result == WAIT_TIMEOUT:
                raise TimeoutError(f"process {self.pid} did not exit in time")
            if result != WAIT_OBJECT_0:
                _raise_last_error("WaitForSingleObject failed")
            return self.poll() or 0

        def terminate(self) -> None:
            if self.poll() is None and not _kernel32.TerminateProcess(self.process_handle, 1):
                _raise_last_error("TerminateProcess failed")

        def close_handle(self) -> None:
            if not self._closed:
                _kernel32.CloseHandle(self.process_handle)
                self._closed = True

    class _WindowsJob:
        def __init__(self) -> None:
            self.handle = _kernel32.CreateJobObjectW(None, None)
            if not self.handle:
                _raise_last_error("CreateJobObjectW failed")
            info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            ok = _kernel32.SetInformationJobObject(self.handle, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info))
            if not ok:
                _kernel32.CloseHandle(self.handle)
                self.handle = None
                _raise_last_error("SetInformationJobObject failed")

        def create_suspended(self, command: Sequence[str], *, cwd: Path | None, env: Mapping[str, str] | None) -> _WindowsProcess:
            if not command:
                raise ValueError("command must not be empty")
            cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(list(command)))
            env_block = None
            if env is not None:
                normalized = {str(k): str(v) for k, v in env.items()}
                block = "\0".join(f"{k}={v}" for k, v in sorted(normalized.items())) + "\0\0"
                env_block = ctypes.create_unicode_buffer(block)
            startup = _STARTUPINFOW()
            startup.cb = ctypes.sizeof(startup)
            proc_info = _PROCESS_INFORMATION()
            flags = CREATE_SUSPENDED | CREATE_NEW_PROCESS_GROUP | CREATE_UNICODE_ENVIRONMENT
            ok = _kernel32.CreateProcessW(None, cmdline, None, None, False, flags, env_block, str(cwd) if cwd is not None else None, ctypes.byref(startup), ctypes.byref(proc_info))
            if not ok:
                _raise_last_error("CreateProcessW failed")
            try:
                if not _kernel32.AssignProcessToJobObject(self.handle, proc_info.hProcess):
                    code = ctypes.get_last_error()
                    _kernel32.TerminateProcess(proc_info.hProcess, 1)
                    _kernel32.CloseHandle(proc_info.hProcess)
                    raise ProcessOwnershipError(f"AssignProcessToJobObject failed; Windows error {code}")
                if _kernel32.ResumeThread(proc_info.hThread) == 0xFFFFFFFF:
                    code = ctypes.get_last_error()
                    _kernel32.TerminateProcess(proc_info.hProcess, 1)
                    _kernel32.CloseHandle(proc_info.hProcess)
                    raise ProcessOwnershipError(f"ResumeThread failed; Windows error {code}")
                return _WindowsProcess(proc_info.hProcess, int(proc_info.dwProcessId))
            finally:
                _kernel32.CloseHandle(proc_info.hThread)

        def close(self) -> None:
            if self.handle:
                _kernel32.CloseHandle(self.handle)
                self.handle = None


class ProcessSupervisor:
    """Owns subprocesses without relying on process-name matching."""

    def __init__(self) -> None:
        self._processes: dict[int, ManagedProcess] = {}
        self._closed = False
        self._job = _WindowsJob() if os.name == "nt" else None

    def spawn(self, command: Sequence[str], *, cwd: Path | None = None, env: Mapping[str, str] | None = None) -> ManagedProcess:
        if self._closed:
            raise RuntimeError("process supervisor is closed")
        if not command:
            raise ValueError("command must not be empty")
        if os.name == "nt":
            process = self._job.create_suspended(command, cwd=cwd, env=env)  # type: ignore[union-attr]
        else:
            popen = subprocess.Popen(list(command), cwd=str(cwd) if cwd is not None else None, env=dict(env) if env is not None else None, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process = _PosixProcess(popen)
        self._processes[process.pid] = process
        return process

    def running_pids(self) -> set[int]:
        return {pid for pid, process in self._processes.items() if process.poll() is None}

    def terminate_owned(self, grace_seconds: float = 0.5) -> None:
        if self._closed:
            return
        if os.name == "nt":
            for process in self._processes.values():
                if process.poll() is None:
                    process.terminate()
            deadline = time.monotonic() + max(0.0, grace_seconds)
            for process in self._processes.values():
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining)
                except TimeoutError:
                    pass
            self._job.close()  # type: ignore[union-attr]
            for process in self._processes.values():
                if isinstance(process, _WindowsProcess):
                    process.close_handle()
        else:
            for process in self._processes.values():
                process.terminate()
            deadline = time.monotonic() + max(0.0, grace_seconds)
            for process in self._processes.values():
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        self._closed = True

    def close(self) -> None:
        self.terminate_owned()

    def __enter__(self) -> "ProcessSupervisor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
