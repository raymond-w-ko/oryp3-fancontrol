#!/usr/bin/env python3
import atexit
import sys
import time
import subprocess
import re


DEBUG = True
CHECK_INTERVAL = 5

CPU_TEMP_FILE = "/sys/devices/platform/system76/hwmon/hwmon1/temp1_input"
CPU_PWM_ENABLE = "/sys/devices/platform/system76/hwmon/hwmon1/pwm1_enable"
CPU_PWM_CONTROL = "/sys/devices/platform/system76/hwmon/hwmon1/pwm1"

CPU_MIN_TEMP = 45
CPU_MIN_FAN = 0
CPU_MAX_TEMP = 75
CPU_MAX_FAN = 255

GPU_TEMP_FILE = "/sys/devices/platform/system76/hwmon/hwmon1/temp2_input"
GPU_PWM_ENABLE = "/sys/devices/platform/system76/hwmon/hwmon1/pwm2_enable"
GPU_PWM_CONTROL = "/sys/devices/platform/system76/hwmon/hwmon1/pwm2"

GPU_MIN_TEMP = 40
GPU_MIN_FAN = 0
GPU_MAX_TEMP = 75
GPU_MAX_FAN = 255


def _write(file, s):
    with open(file, "w") as f:
        f.write(str(s))


def read_cpu_temp():
    with open(CPU_TEMP_FILE, "r") as f:
        s = f.read()
        return int(s) / 1000.0


def read_gpu_temp():
    proc = subprocess.Popen(["/usr/bin/nvidia-smi"], stdout=subprocess.PIPE)
    lines = list(map(lambda x: x.decode("utf-8").strip(), proc.stdout))
    line = lines[8]
    tokens = re.split(r"\s+", line)
    temp_string = tokens[2]
    assert temp_string.endswith("C")
    temp_string = temp_string[:-1]
    return int(temp_string)


def loop():
    cpu_temp = read_cpu_temp()
    if DEBUG:
        print("CPU TEMP: %f" % (cpu_temp))
    pwm_value = 255
    if cpu_temp < CPU_MIN_TEMP:
        pwm_value = CPU_MIN_FAN
    elif cpu_temp > CPU_MAX_TEMP:
        pwm_value = CPU_MAX_FAN
    else:
        p = (cpu_temp - CPU_MIN_TEMP) / (CPU_MAX_TEMP - CPU_MIN_TEMP)
        pwm_value = int(p * 255)
    _write(CPU_PWM_CONTROL, pwm_value)
    if DEBUG:
        print("CPU PWM: %f" % (pwm_value))

    gpu_temp = read_gpu_temp()
    if DEBUG:
        print("GPU TEMP: %f" % (gpu_temp))
    pwm_value = 255
    if gpu_temp < GPU_MIN_TEMP:
        pwm_value = GPU_MIN_FAN
    elif gpu_temp > GPU_MAX_TEMP:
        pwm_value = GPU_MAX_FAN
    else:
        p = (gpu_temp - GPU_MIN_TEMP) / (GPU_MAX_TEMP - GPU_MIN_TEMP)
        pwm_value = int(p * 255)
    _write(GPU_PWM_CONTROL, pwm_value)
    if DEBUG:
        print("GPU PWM: %f" % (pwm_value))

    if DEBUG:
        print("")
    time.sleep(CHECK_INTERVAL)


def main(args):
    _write(CPU_PWM_ENABLE, "1")
    _write(GPU_PWM_ENABLE, "1")
    while True:
        loop()


def resume_auto_fan_control():
    print("resuming automatic fan control (write 2 > pwm*_enable")
    _write(CPU_PWM_ENABLE, "2")
    _write(GPU_PWM_ENABLE, "2")


if __name__ == "__main__":
    atexit.register(resume_auto_fan_control)
    main(sys.argv)
