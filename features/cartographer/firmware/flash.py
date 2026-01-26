#!/usr/bin/env python3
"""
On-device Cartographer Firmware Flasher for K2.
Supports: STM32G431 (V4), STM32F042 (V3/Survey)


Protocol based on Katapult flashtool.py by Eric Callahan
"""
from __future__ import annotations
print("Loading...", flush=True)

import sys
import os
import struct

import argparse
import hashlib
import pathlib
import subprocess
import time
from typing import Optional, Union

# ============================================================================
# Add bundled deps to path (must be before importing rich/usb)
# ============================================================================
_script_dir = os.path.dirname(os.path.abspath(__file__))
_deps_dir = os.path.join(_script_dir, 'deps')
if os.path.isdir(_deps_dir):
    sys.path.insert(0, _deps_dir)

# ============================================================================
# Rich UI Setup
# ============================================================================
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich import box
from rich.live import Live
from rich.text import Text

console = Console()

# ============================================================================
# USB support via pyusb
# ============================================================================
def _import_usb():
    """Import usb modules and configure backend."""
    import usb.core
    import usb.util
    import usb.backend.libusb1
    import ctypes
    
    # OpenWrt needs explicit backend loading
    try:
        ctypes.CDLL('/usr/lib/libusb-1.0.so.0', mode=ctypes.RTLD_GLOBAL)
        _backend = usb.backend.libusb1.get_backend(find_library=lambda x: '/usr/lib/libusb-1.0.so.0')
        _orig_find = usb.core.find
        usb.core.find = lambda *args, **kwargs: _orig_find(*args, backend=_backend, **kwargs) if 'backend' not in kwargs else _orig_find(*args, **kwargs)
    except:
        pass

try:
    _import_usb()
    import usb.core
    import usb.util
    HAS_USB = True
except ModuleNotFoundError:
    console.print("[red]ERROR:[/red] pyusb not found in deps/ folder")
    console.print("Make sure deps/ folder contains usb package")
    sys.exit(1)

def crc16_ccitt(buf: Union[bytes, bytearray]) -> int:
    crc = 0xffff
    for data in buf:
        data ^= crc & 0xff
        data ^= (data & 0x0f) << 4
        crc = ((data << 8) | (crc >> 8)) ^ (data >> 4) ^ (data << 3)
    return crc & 0xFFFF



# Katapult Defs
CMD_HEADER = b'\x01\x88'
CMD_TRAILER = b'\x99\x03'
BOOTLOADER_CMDS = {
    'CONNECT': 0x11,
    'SEND_BLOCK': 0x12,
    'SEND_EOF': 0x13,
    'REQUEST_BLOCK': 0x14,
    'COMPLETE': 0x15,
}

ACK_SUCCESS = 0xa0
ACK_ERROR = 0xf2
ACK_BUSY = 0xf3

# USB IDs
KLIPPER_VID = 0x1d50
KLIPPER_PID = 0x614e
KATAPULT_VID = 0x1d50
KATAPULT_PID = 0x6177

# CDC-ACM control requests
SET_LINE_CODING = 0x20
SET_CONTROL_LINE_STATE = 0x22

class FlashError(Exception):
    pass

# ============================================================================
# Service Management (stop Klipper access to USB device)
# ============================================================================

# Track if cartographer service exists
_cartographer_service_exists = None

def stop_services():
    """Stop services that might hold the USB device."""
    global _cartographer_service_exists
    
    try:
        result = subprocess.run(["/etc/init.d/cartographer", "stop"], 
                                capture_output=True, timeout=10)
        _cartographer_service_exists = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _cartographer_service_exists = False
    
    try:
        subprocess.run(["killall", "usb_bridge"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    time.sleep(0.5)

def start_services():
    """Restart cartographer service if it exists."""
    global _cartographer_service_exists
    
    if _cartographer_service_exists:
        try:
            subprocess.run(["/etc/init.d/cartographer", "start"], 
                          capture_output=True, timeout=10)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

def device_present(vid: int, pid: int):
    """Check if USB device with given VID:PID is present."""
    return usb.core.find(idVendor=vid, idProduct=pid)

# ============================================================================
# Direct USB Communication
# ============================================================================

class USBDevice:
    """Direct USB CDC-ACM communication - no bridge needed."""
    
    def __init__(self, dev: usb.core.Device):
        self.dev = dev
        self.ep_in = None
        self.ep_out = None
        self.read_buffer = bytearray()
        
    def setup(self):
        """Claim interfaces and find endpoints."""
        for iface in [0, 1]:
            try:
                if self.dev.is_kernel_driver_active(iface):
                    self.dev.detach_kernel_driver(iface)
            except:
                pass
        
        try:
            self.dev.set_configuration()
        except usb.core.USBError:
            pass
        
        usb.util.claim_interface(self.dev, 0)
        usb.util.claim_interface(self.dev, 1)
        
        cfg = self.dev.get_active_configuration()
        intf = cfg[(1, 0)]
        
        self.ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )
        self.ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )
        
        if not self.ep_in or not self.ep_out:
            raise FlashError("Could not find USB endpoints")
        
        # Set line coding (250000 baud, 8N1)
        line_coding = struct.pack('<IBBB', 250000, 0, 0, 8)
        self.dev.ctrl_transfer(0x21, SET_LINE_CODING, 0, 0, line_coding)
        
        # Set control line state (DTR + RTS)
        self.dev.ctrl_transfer(0x21, SET_CONTROL_LINE_STATE, 0x0003, 0, None)
    
    def write(self, data: bytes) -> int:
        """Write data to USB device."""
        return self.ep_out.write(data, timeout=5000)
    
    def read(self, size: int = 64, timeout: int = 2000) -> bytes:
        """Read data from USB device."""
        try:
            data = self.ep_in.read(size, timeout=timeout)
            return bytes(data)
        except usb.core.USBTimeoutError:
            return b''
        except usb.core.USBError as e:
            if e.errno == 110:
                return b''
            raise
    
    def read_until(self, terminator: bytes, timeout: float = 2.0) -> bytes:
        """Read until terminator is found."""
        start = time.time()
        while time.time() - start < timeout:
            chunk = self.read(64, timeout=100)
            if chunk:
                self.read_buffer.extend(chunk)
            
            pos = self.read_buffer.find(terminator)
            if pos >= 0:
                result = bytes(self.read_buffer[:pos + len(terminator)])
                self.read_buffer = self.read_buffer[pos + len(terminator):]
                return result
        
        result = bytes(self.read_buffer)
        self.read_buffer.clear()
        return result
    
    def reset(self):
        """Reset USB state - flush buffers and reinitialize CDC-ACM."""
        try:
            self.read_buffer.clear()
            for _ in range(10):
                try:
                    self.ep_in.read(64, timeout=10)
                except:
                    break
            
            self.dev.ctrl_transfer(0x21, SET_CONTROL_LINE_STATE, 0x0000, 0, None)
            time.sleep(0.1)
            self.dev.ctrl_transfer(0x21, SET_CONTROL_LINE_STATE, 0x0003, 0, None)
            time.sleep(0.1)
        except:
            pass
    
    def hard_reset(self):
        """Do a USB device reset - forces re-enumeration."""
        try:
            self.dev.reset()
            time.sleep(0.5)
        except usb.core.USBError:
            pass
    
    def close(self):
        """Release USB interfaces."""
        try:
            usb.util.release_interface(self.dev, 0)
            usb.util.release_interface(self.dev, 1)
        except:
            pass

# ============================================================================
# Flasher
# ============================================================================

class DirectFlasher:
    def __init__(self, usb_dev: USBDevice, fw_path: Optional[pathlib.Path]):
        self.usb = usb_dev
        self.firmware_path = fw_path
        self.fw_sha = hashlib.sha1()
        self.primed = False
        self.file_size = 0
        self.block_size = 64
        self.block_count = 0
        self.app_start_addr = 0
        self.mcu_type = "unknown"

    def _build_command(self, cmd: int, payload: bytes = b'') -> bytes:
        word_cnt = (len(payload) // 4) & 0xFF
        out_cmd = bytearray(CMD_HEADER)
        out_cmd.append(cmd)
        out_cmd.append(word_cnt)
        if payload:
            out_cmd.extend(payload)
        crc = crc16_ccitt(out_cmd[2:])
        out_cmd.extend(struct.pack("<H", crc))
        out_cmd.extend(CMD_TRAILER)
        return bytes(out_cmd)

    def prime(self):
        """Prime double-buffered USB with invalid command."""
        msg = self._build_command(0x90, b"")
        self.usb.write(msg)
        self.primed = True
        time.sleep(0.2)
        self.usb.read(256, timeout=500)

    def send_command(self, cmdname: str, payload: bytes = b'', tries: int = 5, timeout: float = 2.0) -> bytearray:
        cmd = BOOTLOADER_CMDS[cmdname]
        out_cmd = self._build_command(cmd, payload)
        
        for attempt in range(tries):
            self.usb.read_buffer.clear()
            while self.usb.read(64, timeout=5):
                pass
            
            self.usb.write(out_cmd)
            
            data = bytearray()
            start = time.time()
            while time.time() - start < timeout:
                chunk = self.usb.read(64, timeout=200)
                if chunk:
                    data.extend(chunk)
                    
                    result = self._try_parse_response(data, cmd)
                    if result is not None:
                        time.sleep(0.002)
                        while self.usb.read(64, timeout=5):
                            pass
                        return result
                elif len(data) > 0:
                    time.sleep(0.05)
                    continue
            
            time.sleep(0.3)
        
        raise FlashError(f"Command {cmdname} failed after {tries} attempts")
    
    def _try_parse_response(self, data: bytearray, expected_cmd: int) -> Optional[bytearray]:
        """Try to parse a valid response for the expected command from data."""
        pos = 0
        while pos <= len(data) - 8:
            if data[pos:pos+2] != CMD_HEADER:
                pos += 1
                continue
            
            recd_ack = data[pos + 2]
            recd_len = data[pos + 3] * 4
            expected_size = 8 + recd_len
            
            if pos + expected_size > len(data):
                return None
            
            trailer = data[pos + expected_size - 2:pos + expected_size]
            if trailer != CMD_TRAILER:
                pos += 1
                continue
            
            recd_crc, = struct.unpack("<H", data[pos + expected_size - 4:pos + expected_size - 2])
            calc_crc = crc16_ccitt(data[pos + 2:pos + expected_size - 4])
            if recd_crc != calc_crc:
                pos += 1
                continue
            
            if self.primed and recd_ack == ACK_ERROR:
                self.primed = False
                pos += expected_size
                continue
            
            if recd_len >= 4:
                cmd_response, = struct.unpack("<I", data[pos + 4:pos + 8])
                if cmd_response != expected_cmd:
                    pos += expected_size
                    continue
            
            if recd_ack == ACK_BUSY:
                return None
            
            if recd_ack != ACK_SUCCESS:
                return None
            
            if recd_len <= 4:
                return bytearray()
            return bytearray(data[pos + 8:pos + 4 + recd_len])
        
        return None

    def connect(self):
        ret = self.send_command('CONNECT')
        
        if len(ret) < 12:
            raise FlashError("Invalid CONNECT response")
        
        ver_bytes, start_addr, self.block_size = struct.unpack("<4sII", ret[:12])
        self.app_start_addr = start_addr
        proto_version = tuple([v for v in reversed(ver_bytes[:3])])
        proto_str = ".".join([str(v) for v in proto_version])
        
        mcu_info = ret[12:].rstrip(b'\x00')
        if proto_version >= (1, 1, 0):
            parts = mcu_info.split(b'\x00', maxsplit=1)
            self.mcu_type = parts[0].decode()
        else:
            self.mcu_type = mcu_info.decode()
        
        return proto_str

    def flash(self):
        """Flash firmware with Rich progress bar."""
        with open(self.firmware_path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            self.file_size = f.tell()
            f.seek(0)
            
            flash_addr = self.app_start_addr
            total_blocks = (self.file_size + self.block_size - 1) // self.block_size
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]Flashing"),
                BarColumn(bar_width=30),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("flash", total=total_blocks)
                
                while True:
                    buf = f.read(self.block_size)
                    if not buf:
                        break
                    if len(buf) < self.block_size:
                        buf += b'\xFF' * (self.block_size - len(buf))
                    
                    self.fw_sha.update(buf)
                    prefix = struct.pack('<I', flash_addr)
                    
                    for retry in range(3):
                        try:
                            resp = self.send_command('SEND_BLOCK', prefix + buf, tries=3, timeout=5.0)
                            recd_addr, = struct.unpack('<I', resp[:4])
                            if recd_addr == flash_addr:
                                break
                        except FlashError:
                            if retry == 2:
                                raise FlashError(f"Flash failed at 0x{flash_addr:X}")
                        time.sleep(0.1)
                    else:
                        raise FlashError(f"Flash failed at 0x{flash_addr:X}")
                    
                    flash_addr += self.block_size
                    self.block_count += 1
                    progress.update(task, completed=self.block_count)
        
        resp = self.send_command('SEND_EOF')
        pages, = struct.unpack('<I', resp[:4])
        console.print(f"[green]✓[/green] Write complete: {pages} pages")

    def verify(self):
        """Verify firmware with Rich progress bar."""
        ver_sha = hashlib.sha1()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Verifying"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("verify", total=self.block_count)
            
            for i in range(self.block_count):
                addr = i * self.block_size + self.app_start_addr
                resp = self.send_command('REQUEST_BLOCK', struct.pack('<I', addr))
                ver_sha.update(resp[4:])
                progress.update(task, completed=i + 1)
        
        if ver_sha.hexdigest() != self.fw_sha.hexdigest():
            raise FlashError("Verification failed!")
        console.print(f"[green]✓[/green] Verified: [dim]{self.fw_sha.hexdigest()[:16]}...[/dim]")

    def finish(self):
        self.send_command('COMPLETE')

# ============================================================================
# Firmware Selection
# ============================================================================

def _print_unsupported_device(detected_mcu: Optional[str] = None):
    """Print error message for unsupported devices."""
    console.print()
    if detected_mcu:
        console.print(f"[red]ERROR:[/red] Unsupported device detected: [yellow]{detected_mcu}[/yellow]")
    else:
        console.print("[red]ERROR:[/red] No supported device found")
    console.print()
    console.print("This tool only supports:")
    console.print("  [cyan]•[/cyan] Cartographer V4 (STM32G431)")
    console.print("  [cyan]•[/cyan] Cartographer V3 / Survey (STM32F042)")
    console.print()

def prompt_firmware(mcu: str, proto_str: str, fw_version: Optional[str] = None) -> Optional[pathlib.Path]:
    """Display firmware selection menu."""
    script_dir = pathlib.Path(__file__).parent.resolve()
    
    # Determine MCU info
    if mcu == "stm32g431xx":
        device_name = "Cartographer V4"
        device_chip = "STM32G431"
        options = [
            ("1", "V4 6.0.0 Lite", "Recommended for K2", 
             script_dir / "firmware" / "CartographerV4_6.0.0_USB_lite_8kib_offset.bin"),
            ("2", "V4 6.0.0 Full", "2x sampling rate",
             script_dir / "firmware" / "CartographerV4_6.0.0_USB_full_8kib_offset.bin"),
            ("3", "Abort", "Exit bootloader mode", None),
        ]
    elif mcu == "stm32f042x6":
        device_name = "Cartographer V3 / Survey"
        device_chip = "STM32F042"
        options = [
            ("1", "K1 5.1.0 (Lite)", "Recommended for K2",
             script_dir / "firmware" / "Survey_Cartographer_K1_USB_8kib_offset.bin"),
            ("2", "5.1.0 (Full)", "2x sampling rate",
             script_dir / "firmware" / "Survey_Cartographer_USB_8kib_offset.bin"),
            ("3", "Abort", "Exit bootloader mode", None),
        ]
    else:
        _print_unsupported_device(mcu)
        return None
    
    # Build info panel
    info_text = Text()
    info_text.append("Device: ", style="dim")
    info_text.append(f"{device_name} ({device_chip})\n", style="cyan")
    info_text.append("Protocol: ", style="dim")
    info_text.append(f"{proto_str}")
    if fw_version:
        info_text.append("\n")
        info_text.append("Current Firmware: ", style="dim")
        info_text.append(fw_version, style="bold")
    
    console.print()
    console.print(Panel(info_text, title="[bold]Connected[/bold]", border_style="green", padding=(0, 1)))
    
    # Build menu table
    table = Table(box=box.ROUNDED, show_header=False, border_style="dim", padding=(0, 1))
    table.add_column("Key", style="bold yellow", width=3)
    table.add_column("Name", style="bold")
    table.add_column("Description", style="dim")
    
    for key, name, desc, path in options:
        table.add_row(key, name, desc)
    
    console.print()
    console.print("[bold yellow]Select Firmware to Flash[/bold yellow]")
    console.print(table)
    
    # Get default option name (strip Rich markup)
    import re
    default_name = re.sub(r'\[/?[^\]]+\]', '', options[0][1])
    
    # Two-part beginner-friendly prompt
    console.print()
    console.print(f"[dim]Default:[/dim] [bold]{default_name}[/bold]", highlight=False)
    choice = Prompt.ask(
        "Press Enter to flash default, or type 2 or 3 then Enter",
        choices=["", "1", "2", "3"],
        default="",
        show_choices=False,
        show_default=False
    )
    
    # Empty string or "1" means default
    if choice == "" or choice == "1":
        choice = "1"
    
    # Get selected option
    for key, name, _, path in options:
        if key == choice:
            if path is None:
                return "ABORT"
            if not path.is_file():
                console.print(f"[red]✗[/red] Firmware not found: [yellow]{path.name}[/yellow]")
                return None
            clean_name = re.sub(r'\[/?[^\]]+\]', '', name)
            console.print(f"[green]✓[/green] Selected: [bold]{clean_name}[/bold]")
            return path
    
    return None

# ============================================================================
# Version Detection
# ============================================================================


def scan_flash_for_version(flasher, mcu_type: str = ""):
    """
    Quick check for Klipper data dictionary at known offsets.
    
    Offsets are ordered by MCU type for faster detection:
    - V3 (stm32f042x6): 0x4C50 first
    - V4 (stm32g431xx): 0x5B98 (6.0.0) first, then 0x5B38 (5.1)
    """
    import zlib
    import json
    
    # Order offsets by MCU type for faster detection
    if mcu_type == "stm32f042x6":  # V3
        offsets = [0x4C50, 0x5B98, 0x5B38]
    elif mcu_type == "stm32g431xx":  # V4
        offsets = [0x5B98, 0x5B38, 0x4C50]  # Try 6.0.0 first, then 5.1
    else:
        offsets = [0x5B98, 0x5B38, 0x4C50]  # Default: newest first
    
    ZLIB_SIGNATURES = [b'\x78\x9c', b'\x78\xda', b'\x78\x01']
    
    block_size = flasher.block_size
    base_addr = flasher.app_start_addr
    
    for offset in offsets:
        try:
            start_block = offset // block_size
            data = bytearray()
            
            for i in range(64):
                addr = base_addr + ((start_block + i) * block_size)
                try:
                    resp = flasher.send_command('REQUEST_BLOCK', struct.pack('<I', addr), tries=2, timeout=0.5)
                    if resp and len(resp) > 4:
                        data.extend(resp[4:])
                except:
                    break
            
            if not data:
                continue
            
            data_start_offset = start_block * block_size
            local_offset = offset - data_start_offset
            
            for sig in ZLIB_SIGNATURES:
                for check_offset in range(max(0, local_offset - 16), min(len(data) - 100, local_offset + 16)):
                    if data[check_offset:check_offset + 2] == sig:
                        for end in range(200, min(len(data) - check_offset, 6000), 100):
                            try:
                                decompressed = zlib.decompress(bytes(data[check_offset:check_offset + end]))
                                info = json.loads(decompressed)
                                if isinstance(info, dict) and ('version' in info or 'build_versions' in info):
                                    return info
                            except:
                                continue
        except:
            continue
    
    return None


# ============================================================================
# Bootloader Entry
# ============================================================================

def enter_bootloader(dev) -> bool:
    """Send 1200 baud reset to enter Katapult."""
    try:
        # Detach kernel driver first if active
        for iface in [0, 1]:
            try:
                if dev.is_kernel_driver_active(iface):
                    dev.detach_kernel_driver(iface)
            except:
                pass
        
        dev.ctrl_transfer(0x21, SET_CONTROL_LINE_STATE, 0x0001, 0, None)
        dev.ctrl_transfer(0x21, SET_LINE_CODING, 0, 0, struct.pack('<IBBB', 1200, 0, 0, 8))
        try:
            dev.ctrl_transfer(0x21, SET_CONTROL_LINE_STATE, 0x0000, 0, None)
        except usb.core.USBError:
            pass
        return True
    except usb.core.USBError as e:
        console.print(f"[red]✗[/red] USB error: {e}")
        return False

# ============================================================================
# Main
# ============================================================================

def show_banner():
    """Display the application banner."""
    console.print()
    console.print(Panel.fit(
        "[bold]Cartographer Flasher[/bold]",
        border_style="cyan",
        padding=(0, 2)
    ))
    console.print()

def wait_for_exit():
    """Wait for user to press Enter before exiting alternate screen."""
    console.print()
    console.print("[dim]Press Enter to exit...[/dim]")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        pass

def main():
    parser = argparse.ArgumentParser(description="Cartographer Flasher (Direct USB)")
    parser.add_argument("-f", "--firmware", help="Firmware file path")
    args = parser.parse_args()
    
    # Enter alternate screen buffer (like nano/vim)
    print("\033[?1049h", end="", flush=True)
    
    try:
        return _main_inner(args)
    finally:
        # Exit alternate screen buffer - restores previous terminal view
        print("\033[?1049l", end="", flush=True)
        # Clear the "Loading..." line
        print("\033[1A\033[2K", end="", flush=True)

def _main_inner(args):
    """Main logic, runs inside alternate screen buffer."""
    show_banner()
    
    # Check device state
    already_in_katapult = False
    dev = device_present(KATAPULT_VID, KATAPULT_PID)
    if dev:
        already_in_katapult = True
        console.print("[yellow]●[/yellow] Device in Katapult bootloader mode")
    else:
        dev = device_present(KLIPPER_VID, KLIPPER_PID)
        if not dev:
            _print_unsupported_device()
            return 1
        
        console.print("[green]●[/green] Device running Klipper")
        
        with console.status("[bold blue]Stopping services...") as status:
            stop_services()
        
        dev = device_present(KLIPPER_VID, KLIPPER_PID)
        if not dev:
            console.print("[red]✗[/red] Device disappeared!")
            start_services()
            return 1
        
        with console.status("[bold blue]Entering bootloader...") as status:
            if not enter_bootloader(dev):
                start_services()
                return 1
            
            # Wait for Katapult
            for i in range(20):
                time.sleep(0.5)
                status.update(f"[bold blue]Waiting for bootloader{'.' * (i % 4 + 1)}")
                dev = device_present(KATAPULT_VID, KATAPULT_PID)
                if dev:
                    break
            else:
                console.print("[red]✗[/red] Bootloader timeout!")
                start_services()
                return 1
        
        console.print("[green]✓[/green] Bootloader ready")
        

    
    # Open USB device directly
    usb_dev = USBDevice(dev)
    flasher = None
    try:
        usb_dev.setup()
        
        # If device was already in Katapult (from a previous interrupted session),
        # do a hard USB reset to recover from weird state
        if already_in_katapult:
            with console.status("[bold blue]Resetting device..."):
                usb_dev.hard_reset()
                usb_dev.close()
                
                time.sleep(1)
                dev = device_present(KATAPULT_VID, KATAPULT_PID)
                if not dev:
                    for _ in range(10):
                        time.sleep(0.5)
                        dev = device_present(KATAPULT_VID, KATAPULT_PID)
                        if dev:
                            break
                    if not dev:
                        console.print("[red]✗[/red] Device not found after reset!")
                        return 1
                
                usb_dev = USBDevice(dev)
                usb_dev.setup()
        
        flasher = DirectFlasher(usb_dev, None)
        flasher.prime()
        
        with console.status("[bold blue]Getting device info..."):
            proto_str = flasher.connect()
            
            # Try to get firmware version
            fw_version = None
            try:
                version_info = scan_flash_for_version(flasher, flasher.mcu_type)
                if version_info and 'version' in version_info:
                    fw_version = version_info['version']
            except:
                pass
        
        console.print("[green]✓[/green] Device info retrieved")
        
        # Firmware selection
        if args.firmware:
            fw_path = pathlib.Path(args.firmware)
            console.print(f"[green]✓[/green] Using: [bold]{fw_path.name}[/bold]")
        else:
            fw_path = prompt_firmware(flasher.mcu_type, proto_str, fw_version)
        
        if fw_path == "ABORT":
            console.print("[yellow]●[/yellow] Aborting...")
            flasher.finish()
            console.print("[green]✓[/green] Device returned to normal mode")
            wait_for_exit()
            return 0
        
        if not fw_path:
            return 1
        
        flasher.firmware_path = fw_path
        

        console.print()
        flasher.flash()
        flasher.verify()
        flasher.finish()
        
        console.print()
        console.print(Panel.fit(
            "[bold green]✓ Programming Complete![/bold green]",
            border_style="green",
            padding=(0, 2)
        ))
        wait_for_exit()
        return 0
    
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]⚠[/yellow] [bold]Interrupted![/bold]")
        try:
            if flasher is not None:
                try:
                    flasher.finish()
                    console.print("[green]✓[/green] Device returned to normal mode")
                except:
                    console.print("[yellow]⚠[/yellow] Could not exit bootloader cleanly")
        except:
            pass
        return 130
        
    except FlashError as e:
        console.print(f"\n[red]✗[/red] [bold red]ERROR:[/bold red] {e}")
        return 1
    finally:
        usb_dev.close()
        time.sleep(1)
        start_services()

if __name__ == '__main__':
    sys.exit(main())

