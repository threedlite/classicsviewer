# cpu_temp - macOS CPU Temperature Reader

A C program that reads CPU temperature from the Mac's SMC (System Management Controller).

## Building

```bash
clang -o cpu_temp cpu_temp.c -framework IOKit -framework CoreFoundation
```

## Usage

```
./cpu_temp         # Shows max CPU temperature
./cpu_temp -a      # Shows all temperature sensors
./cpu_temp -v      # Verbose: shows all sensors with type info
./cpu_temp -h      # Show help
```

## Example Output

Default:
```
CPU Temperature: 102.7°C (216.8°F)
```

With `-a` flag:
```
Temperature Sensors:
--------------------
Tp00  :  80.5°C (176.9°F)
Tp01  :  87.6°C (189.7°F)
Te04  :  70.1°C (158.3°F)
...
```

## How It Works

1. Opens a connection to the AppleSMC driver via IOKit
2. Enumerates all SMC keys and finds temperature sensors (keys starting with 'T')
3. Parses the float data types (`flt`, `ioft`) used by Apple Silicon Macs
4. Shows the maximum CPU core temperature by default

## Sensor Key Reference

| Prefix | Description |
|--------|-------------|
| Tp*    | P-cores (Performance cores) |
| Te*    | E-cores (Efficiency cores) |
| Tg*    | GPU temperatures |
| Ts*    | SoC/System temperatures |
| TCMb   | CPU Core Max |
| TCMz   | CPU Die Max |
| TB*    | Battery temperatures |
| TH*    | Heat sink temperatures |

## Notes

- Works on both Intel and Apple Silicon Macs
- Apple Silicon Macs use `flt` (float) data types for temperature values
- Intel Macs typically use `sp78` (signed 7.8 fixed point) format
- CPU throttling typically begins around 105-108°C on Apple Silicon
