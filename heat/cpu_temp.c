#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>

// SMC types
typedef struct {
    UInt32 dataSize;
    UInt32 dataType;
    char dataAttributes;
} SMCKeyData_keyInfo_t;

typedef char SMCBytes_t[32];

typedef struct {
    UInt32 key;
    char vers[8];
    char pLimitData[16];
    SMCKeyData_keyInfo_t keyInfo;
    char result;
    char status;
    char data8;
    UInt32 data32;
    SMCBytes_t bytes;
} SMCKeyData_t;

typedef struct {
    UInt8 data[32];
    UInt32 dataType;
    UInt32 dataSize;
    char key[5];
} SMCVal_t;

static io_connect_t smc_conn;

UInt32 _strtoul(const char *str, int size, int base) {
    UInt32 total = 0;
    for (int i = 0; i < size; i++) {
        total += (unsigned char)(str[i]) << (size - 1 - i) * 8;
    }
    return total;
}

void _ultostr(char *str, UInt32 val) {
    str[0] = (char)(val >> 24);
    str[1] = (char)(val >> 16);
    str[2] = (char)(val >> 8);
    str[3] = (char)val;
    str[4] = '\0';
}

kern_return_t SMCOpen(void) {
    io_iterator_t iterator;
    io_object_t device;

    CFMutableDictionaryRef matchingDictionary = IOServiceMatching("AppleSMC");
    kern_return_t result = IOServiceGetMatchingServices(kIOMainPortDefault, matchingDictionary, &iterator);
    if (result != kIOReturnSuccess) return result;

    device = IOIteratorNext(iterator);
    IOObjectRelease(iterator);
    if (device == 0) return kIOReturnNotFound;

    result = IOServiceOpen(device, mach_task_self(), 0, &smc_conn);
    IOObjectRelease(device);
    return result;
}

kern_return_t SMCClose(void) {
    return IOServiceClose(smc_conn);
}

kern_return_t SMCCall(int index, SMCKeyData_t *inputStructure, SMCKeyData_t *outputStructure) {
    size_t structureInputSize = sizeof(SMCKeyData_t);
    size_t structureOutputSize = sizeof(SMCKeyData_t);
    return IOConnectCallStructMethod(smc_conn, index, inputStructure, structureInputSize,
                                     outputStructure, &structureOutputSize);
}

kern_return_t SMCReadKey(const char *key, SMCVal_t *val) {
    SMCKeyData_t inputStructure;
    SMCKeyData_t outputStructure;

    memset(&inputStructure, 0, sizeof(SMCKeyData_t));
    memset(&outputStructure, 0, sizeof(SMCKeyData_t));
    memset(val, 0, sizeof(SMCVal_t));

    inputStructure.key = _strtoul(key, 4, 16);
    inputStructure.data8 = 9;

    kern_return_t result = SMCCall(2, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess) return result;

    val->dataSize = outputStructure.keyInfo.dataSize;
    _ultostr(val->key, outputStructure.key);
    val->dataType = outputStructure.keyInfo.dataType;

    inputStructure.keyInfo.dataSize = val->dataSize;
    inputStructure.data8 = 5;

    result = SMCCall(2, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess) return result;

    memcpy(val->data, outputStructure.bytes, sizeof(outputStructure.bytes));
    return kIOReturnSuccess;
}

double SMCGetTemperature(const char *key, char *typeOut) {
    SMCVal_t val;
    kern_return_t result = SMCReadKey(key, &val);
    if (result != kIOReturnSuccess) return -1.0;

    if (typeOut) {
        _ultostr(typeOut, val.dataType);
    }

    UInt32 fltType = _strtoul("flt ", 4, 16);
    UInt32 ioftType = _strtoul("ioft", 4, 16);
    UInt32 sp78Type = _strtoul("sp78", 4, 16);
    UInt32 fpe2Type = _strtoul("fpe2", 4, 16);
    UInt32 ui16Type = _strtoul("ui16", 4, 16);
    UInt32 si16Type = _strtoul("si16", 4, 16);
    UInt32 si32Type = _strtoul("si32", 4, 16);

    // Handle 4-byte float types (flt, ioft)
    if (val.dataSize == 4 && (val.dataType == fltType || val.dataType == ioftType)) {
        // Reinterpret 4 bytes as float (little-endian on Apple Silicon)
        float f;
        memcpy(&f, val.data, sizeof(float));
        return (double)f;
    }

    // Handle si32 (signed 32-bit integer, likely in milli-degrees or similar)
    if (val.dataSize == 4 && val.dataType == si32Type) {
        int32_t intVal;
        memcpy(&intVal, val.data, sizeof(int32_t));
        // Try as direct celsius first
        if (intVal > 0 && intVal < 200) return (double)intVal;
        // Try as milli-degrees
        if (intVal > 0 && intVal < 200000) return intVal / 1000.0;
        return -1.0;
    }

    if (val.dataSize == 2) {
        int intValue = (val.data[0] << 8) | val.data[1];

        // sp78: signed 7.8 fixed point (1 sign bit, 7 integer, 8 fractional)
        if (val.dataType == sp78Type) {
            return intValue / 256.0;
        }
        // fpe2: unsigned 14.2 fixed point
        if (val.dataType == fpe2Type) {
            return intValue / 4.0;
        }
        // ui16: unsigned 16-bit
        if (val.dataType == ui16Type) {
            return intValue / 256.0;
        }
        // si16: signed 16-bit
        if (val.dataType == si16Type) {
            if (intValue > 32767) intValue -= 65536;
            return intValue / 256.0;
        }

        // Generic fallback - try first byte as temperature
        double temp = val.data[0];
        if (temp > 0 && temp < 150) return temp;
    }
    return -1.0;
}

// Check if a key is a CPU-related temperature sensor
int isCPUTempKey(const char *key) {
    // Tp* = P-cores (performance cores)
    // Te* = E-cores (efficiency cores)
    // Tg* = GPU
    // Ts* = SoC/System
    // TCMb/TCMz = CPU max
    // TPSP/TPMP = Power management
    if (key[0] == 'T' && key[1] == 'p') return 1;  // P-cores
    if (key[0] == 'T' && key[1] == 'e') return 1;  // E-cores
    if (strcmp(key, "TCMb") == 0) return 1;        // CPU max
    if (strcmp(key, "TCMz") == 0) return 1;        // CPU max zone
    if (strcmp(key, "TPSP") == 0) return 1;        // CPU power
    if (strcmp(key, "TPMP") == 0) return 1;        // CPU power
    return 0;
}

// Get a friendly name for the sensor
const char* getSensorName(const char *key) {
    if (strcmp(key, "TCMb") == 0) return "CPU Core Max";
    if (strcmp(key, "TCMz") == 0) return "CPU Die Max";
    if (strcmp(key, "TPSP") == 0) return "CPU Power Supply";
    if (strcmp(key, "TPMP") == 0) return "CPU Power Management";
    // P-core clusters (Tp0*, Tp1*, etc.)
    if (key[0] == 'T' && key[1] == 'p' && key[2] >= '0' && key[2] <= '3') {
        return "P-Core";
    }
    // E-core (Te*)
    if (key[0] == 'T' && key[1] == 'e') {
        return "E-Core";
    }
    return key;
}

// Enumerate all SMC keys and find temperature ones
int enumerateSMCKeys(int verbose, int allTemps) {
    SMCKeyData_t inputStructure;
    SMCKeyData_t outputStructure;

    // Get key count
    memset(&inputStructure, 0, sizeof(SMCKeyData_t));
    memset(&outputStructure, 0, sizeof(SMCKeyData_t));
    inputStructure.key = _strtoul("#KEY", 4, 16);
    inputStructure.data8 = 9;

    kern_return_t result = SMCCall(2, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess) return 0;

    inputStructure.keyInfo.dataSize = outputStructure.keyInfo.dataSize;
    inputStructure.data8 = 5;
    result = SMCCall(2, &inputStructure, &outputStructure);
    if (result != kIOReturnSuccess) return 0;

    UInt32 keyCount = ((UInt32)outputStructure.bytes[0] << 24) +
                      ((UInt32)outputStructure.bytes[1] << 16) +
                      ((UInt32)outputStructure.bytes[2] << 8) +
                      (UInt32)outputStructure.bytes[3];

    if (verbose) {
        printf("Found %u SMC keys, searching for temperature sensors...\n\n", keyCount);
    }

    // First pass: find max CPU temperature for summary
    double maxCPUTemp = 0;
    char maxCPUKey[5] = {0};

    for (UInt32 i = 0; i < keyCount; i++) {
        memset(&inputStructure, 0, sizeof(SMCKeyData_t));
        memset(&outputStructure, 0, sizeof(SMCKeyData_t));

        inputStructure.data8 = 8;
        inputStructure.data32 = i;

        result = SMCCall(2, &inputStructure, &outputStructure);
        if (result != kIOReturnSuccess) continue;

        char key[5];
        _ultostr(key, outputStructure.key);

        if (key[0] == 'T' && isCPUTempKey(key)) {
            double temp = SMCGetTemperature(key, NULL);
            if (temp > maxCPUTemp && temp < 150) {
                maxCPUTemp = temp;
                strncpy(maxCPUKey, key, 4);
            }
        }
    }

    int found = 0;
    int headerPrinted = 0;

    // Normal mode: show summary
    if (!verbose && !allTemps) {
        if (maxCPUTemp > 0) {
            printf("CPU Temperature: %.1f°C (%.1f°F)\n", maxCPUTemp, maxCPUTemp * 9.0/5.0 + 32.0);
            return 1;
        }
        return 0;
    }

    // All temps or verbose mode
    for (UInt32 i = 0; i < keyCount; i++) {
        memset(&inputStructure, 0, sizeof(SMCKeyData_t));
        memset(&outputStructure, 0, sizeof(SMCKeyData_t));

        inputStructure.data8 = 8;
        inputStructure.data32 = i;

        result = SMCCall(2, &inputStructure, &outputStructure);
        if (result != kIOReturnSuccess) continue;

        char key[5];
        _ultostr(key, outputStructure.key);

        if (key[0] == 'T') {
            char type[5] = {0};
            double temp = SMCGetTemperature(key, type);

            int showThis = allTemps || (verbose && temp > -100);
            if (!allTemps && !verbose) {
                showThis = isCPUTempKey(key) && temp > 0 && temp < 150;
            }

            if (showThis && temp > 0 && temp < 150) {
                if (!headerPrinted) {
                    printf("Temperature Sensors:\n");
                    printf("--------------------\n");
                    headerPrinted = 1;
                }
                if (verbose) {
                    printf("%-6s (type: %s): %5.1f°C (%5.1f°F)\n", key, type, temp, temp * 9.0/5.0 + 32.0);
                } else {
                    printf("%-6s: %5.1f°C (%5.1f°F)\n", key, temp, temp * 9.0/5.0 + 32.0);
                }
                found = 1;
            }
        }
    }

    return found;
}

int trySMC(int verbose, int allTemps) {
    kern_return_t result = SMCOpen();
    if (result != kIOReturnSuccess) {
        if (verbose) {
            printf("Could not open SMC connection (error %d)\n", result);
        }
        return 0;
    }

    int found = enumerateSMCKeys(verbose, allTemps);
    SMCClose();
    return found;
}

// Try to read from IOHIDEventSystem temperature sensors
int tryIOHIDSensors(void) {
    io_iterator_t iterator;
    io_service_t service;
    int found = 0;
    int headerPrinted = 0;

    // Try various service classes that might have temperature
    const char *classes[] = {
        "AppleSMCTemperatureSensor",
        "IOHIDEventService",
        "IOHIDSensor",
        NULL
    };

    for (int c = 0; classes[c] != NULL; c++) {
        CFMutableDictionaryRef matching = IOServiceMatching(classes[c]);
        if (!matching) continue;

        kern_return_t result = IOServiceGetMatchingServices(kIOMainPortDefault, matching, &iterator);
        if (result != kIOReturnSuccess) continue;

        while ((service = IOIteratorNext(iterator)) != 0) {
            // Check for temperature property
            CFNumberRef tempRef = IORegistryEntryCreateCFProperty(
                service, CFSTR("CurrentValue"), kCFAllocatorDefault, 0);

            if (!tempRef) {
                tempRef = IORegistryEntryCreateCFProperty(
                    service, CFSTR("Temperature"), kCFAllocatorDefault, 0);
            }

            if (tempRef && CFGetTypeID(tempRef) == CFNumberGetTypeID()) {
                double temp = 0;
                CFNumberGetValue(tempRef, kCFNumberDoubleType, &temp);

                // Get sensor name
                CFStringRef nameRef = IORegistryEntryCreateCFProperty(
                    service, CFSTR("Product"), kCFAllocatorDefault, 0);
                if (!nameRef) {
                    nameRef = IORegistryEntryCreateCFProperty(
                        service, CFSTR("IOName"), kCFAllocatorDefault, 0);
                }

                char name[128] = "Unknown";
                if (nameRef && CFGetTypeID(nameRef) == CFStringGetTypeID()) {
                    CFStringGetCString(nameRef, name, sizeof(name), kCFStringEncodingUTF8);
                    CFRelease(nameRef);
                }

                if (temp > 0 && temp < 200) {
                    if (!headerPrinted) {
                        printf("Temperature Sensors:\n");
                        printf("-------------------\n");
                        headerPrinted = 1;
                    }
                    printf("%-30s: %5.1f°C (%5.1f°F)\n", name, temp, temp * 9.0/5.0 + 32.0);
                    found = 1;
                }
            }

            if (tempRef) CFRelease(tempRef);
            IOObjectRelease(service);
        }
        IOObjectRelease(iterator);
    }

    return found;
}

void printUsage(const char *prog) {
    printf("Usage: %s [options]\n", prog);
    printf("Options:\n");
    printf("  -a    Show all temperature sensors\n");
    printf("  -v    Verbose: show all sensors with type info\n");
    printf("  -h    Show this help\n");
    printf("\nBy default, shows only the maximum CPU temperature.\n");
}

int main(int argc, char *argv[]) {
    int verbose = 0;
    int allTemps = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-v") == 0) {
            verbose = 1;
        } else if (strcmp(argv[i], "-a") == 0) {
            allTemps = 1;
        } else if (strcmp(argv[i], "-h") == 0) {
            printUsage(argv[0]);
            return 0;
        }
    }

    // Try SMC
    if (trySMC(verbose, allTemps)) {
        return 0;
    }

    // Try IOHIDSensors
    if (tryIOHIDSensors()) {
        return 0;
    }

    printf("Could not read CPU temperature.\n");
    return 1;
}
