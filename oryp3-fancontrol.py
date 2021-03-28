#!/usr/bin/env python3
import sys
import os
import atexit
import time
import subprocess
import re
from threading import Thread


DEBUG = True
# interval of 5 can cause GPU to not power down
CHECK_INTERVAL = 5

SYS_PREFIX = "/sys/devices/platform/system76/hwmon/hwmon3"

CPU_TEMP_FILE = SYS_PREFIX + "/temp1_input"
CPU_PWM_ENABLE = SYS_PREFIX + "/pwm1_enable"
CPU_PWM_CONTROL = SYS_PREFIX + "/pwm1"

CPU_MIN_TEMP = 55
CPU_MIN_FAN = 0
CPU_MAX_TEMP = 75
CPU_MAX_FAN = 255

GPU_TEMP_FILE = SYS_PREFIX + "/temp2_input"
GPU_PWM_ENABLE = SYS_PREFIX + "/pwm2_enable"
GPU_PWM_CONTROL = SYS_PREFIX + "/pwm2"

GPU_MIN_TEMP = 55
GPU_MIN_FAN = 0
GPU_MAX_TEMP = 75
GPU_MAX_FAN = 255

assert os.path.exists(CPU_TEMP_FILE)
assert os.path.exists(CPU_PWM_ENABLE)
assert os.path.exists(CPU_PWM_CONTROL)
assert os.path.exists(GPU_TEMP_FILE)
assert os.path.exists(GPU_PWM_ENABLE)
assert os.path.exists(GPU_PWM_CONTROL)


def _write(file, s):
    with open(file, "w") as f:
        f.write(str(s))


def read_cpu_temp():
    with open(CPU_TEMP_FILE, "r") as f:
        s = f.read()
        return int(s) / 1000.0


def clamped_lerp(x, min_in, max_in, min_out, max_out):
    pwm_value = 255
    if x < min_in:
        pwm_value = min_out
    elif x > max_in:
        pwm_value = max_out
    else:
        p = (x - min_in) / (max_in - min_in)
        pwm_value = int(p * 255)
    return pwm_value


def read_gpu_temp_inefficient():
    proc = subprocess.Popen(["/usr/bin/nvidia-smi"], stdout=subprocess.PIPE)
    lines = list(map(lambda x: x.decode("utf-8").strip(), proc.stdout))
    line = lines[8]
    tokens = re.split(r"\s+", line)
    temp_string = tokens[2]
    assert temp_string.endswith("C")
    temp_string = temp_string[:-1]
    return int(temp_string)


def read_gpu_temp_oneshot():
    proc = subprocess.Popen(
        ["/usr/bin/nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
        stdout=subprocess.PIPE,
    )
    return int(proc.stdout.read().strip())


def start_gpu_temp_control_thread():
    proc = subprocess.Popen(
        [
            "/usr/bin/nvidia-smi",
            "-l",
            "--query-gpu=temperature.gpu",
            "--format=csv,noheader",
        ],
        stdout=subprocess.PIPE,
    )
    # the above process is persistent and returns the temperature to stdout
    # every 5 seconds or so
    for line in proc.stdout:
        gpu_temp = int(line.strip())
        pwm_value = clamped_lerp(
            gpu_temp, GPU_MIN_TEMP, GPU_MAX_TEMP, GPU_MIN_FAN, GPU_MAX_FAN
        )
        _write(GPU_PWM_CONTROL, pwm_value)
        if DEBUG:
            print("GPU: TEMP: %.02f, PWM: %.02f" % (gpu_temp, pwm_value))


def loop():
    cpu_temp = read_cpu_temp()
    pwm_value = clamped_lerp(
        cpu_temp, CPU_MIN_TEMP, CPU_MAX_TEMP, CPU_MIN_FAN, CPU_MAX_FAN
    )
    _write(CPU_PWM_CONTROL, pwm_value)
    if DEBUG:
        print("CPU: TEMP: %.02f, PWM: %.02f" % (cpu_temp, pwm_value))
    time.sleep(CHECK_INTERVAL)


def main(_args):
    print("manual fan control (write 1 > pwm*_enable")
    _write(CPU_PWM_ENABLE, "1")
    _write(GPU_PWM_ENABLE, "1")

    t = Thread(target=start_gpu_temp_control_thread, daemon=True)
    t.start()

    while True:
        loop()


def resume_auto_fan_control():
    print("resuming automatic fan control (write 2 > pwm*_enable")
    _write(CPU_PWM_ENABLE, "2")
    _write(GPU_PWM_ENABLE, "2")


if __name__ == "__main__":
    atexit.register(resume_auto_fan_control)
    main(sys.argv)
