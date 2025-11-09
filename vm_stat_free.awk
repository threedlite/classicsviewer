#!/usr/bin/awk -f
# Convert macOS vm_stat output to look like Linux 'free -h'
# Usage: vm_stat | awk -f vm_stat_free.awk

BEGIN {
    page_size = 16384  # macOS page size in bytes
}

/page size of/ {
    # Extract actual page size if available
    match($0, /[0-9]+/)
    if (RLENGTH > 0) {
        page_size = substr($0, RSTART, RLENGTH)
    }
}

/Pages free:/ { free = $3 }
/Pages active:/ { active = $3 }
/Pages inactive:/ { inactive = $3 }
/Pages speculative:/ { speculative = $3 }
/Pages wired down:/ { wired = $3 }

function to_human(bytes) {
    if (bytes >= 1099511627776) {
        return sprintf("%.1fT", bytes / 1099511627776)
    } else if (bytes >= 1073741824) {
        return sprintf("%.1fG", bytes / 1073741824)
    } else if (bytes >= 1048576) {
        return sprintf("%.1fM", bytes / 1048576)
    } else if (bytes >= 1024) {
        return sprintf("%.1fK", bytes / 1024)
    } else {
        return sprintf("%dB", bytes)
    }
}

END {
    # Remove trailing dots from numbers
    gsub(/\.$/, "", free)
    gsub(/\.$/, "", active)
    gsub(/\.$/, "", inactive)
    gsub(/\.$/, "", speculative)
    gsub(/\.$/, "", wired)

    # Calculate bytes
    free_bytes = free * page_size
    active_bytes = active * page_size
    inactive_bytes = inactive * page_size
    speculative_bytes = speculative * page_size
    wired_bytes = wired * page_size

    # Total memory
    total_bytes = free_bytes + active_bytes + inactive_bytes + speculative_bytes + wired_bytes

    # Used memory (active + wired)
    used_bytes = active_bytes + wired_bytes

    # Available memory (free + inactive + speculative)
    available_bytes = free_bytes + inactive_bytes + speculative_bytes

    # Print header
    printf "%-15s %10s %10s %10s %10s\n", "", "total", "used", "free", "available"

    # Print Mem line
    printf "%-15s %10s %10s %10s %10s\n",
        "Mem:",
        to_human(total_bytes),
        to_human(used_bytes),
        to_human(free_bytes),
        to_human(available_bytes)

    # Print breakdown
    printf "\n%-15s %10s %10s %10s %10s\n",
        "Active:",
        to_human(active_bytes),
        "Inactive:",
        to_human(inactive_bytes),
        ""

    printf "%-15s %10s %10s %10s\n",
        "Wired:",
        to_human(wired_bytes),
        "Speculative:",
        to_human(speculative_bytes)
}
