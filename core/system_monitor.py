from __future__ import annotations
import os
import time
import socket
import psutil
from typing import Dict, Any

START_TIME = time.time()

class SystemMonitor:
    """
    호스트 시스템 하드웨어 상태(CPU, RAM, CPU 온도, Uptime)를
    주기적으로 수집하여 웹 대시보드에 제공하는 모니터.
    """
    @staticmethod
    def get_cpu_temperature() -> float:
        """
        시스템 온도를 측정합니다. (Linux sysfs 및 psutil 지원)
        /sys/class/thermal/thermal_zone0/temp (밀리섭씨 -> 섭씨 변환)
        """
        thermal_file = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(thermal_file):
            try:
                with open(thermal_file, "r") as f:
                    temp_raw = f.read().strip()
                    return round(float(temp_raw) / 1000.0, 1)
            except Exception:
                pass
        
        # psutil sensors fallback (리눅스 일반)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return round(entries[0].current, 1)
        except Exception:
            pass

        return 0.0

    @classmethod
    def get_system_stats(cls) -> Dict[str, Any]:
        """시스템 전반의 실시간 지표 반환"""
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        uptime_seconds = int(time.time() - START_TIME)
        
        hours, rem = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours}시간 {minutes}분 {seconds}초"

        return {
            "hostname": socket.gethostname(),
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_temperature": cls.get_cpu_temperature(),
            "memory_percent": mem.percent,
            "memory_used_mb": round(mem.used / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "uptime_seconds": uptime_seconds,
            "uptime_str": uptime_str,
        }

system_monitor = SystemMonitor()
