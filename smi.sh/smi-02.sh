#!/bin/bash
################################################################################
# scripts/smi.sh - GPU/VRAM monitoring script
#
# ARCHITECTURE.MD §1 - Initialization:
# "The system runs scripts/check_health.py and scripts/smi.sh to verify CUDA"
#
# ARCHITECTURE.MD §4 - Pre-flight Health Checks:
# "scripts/smi.sh executed at startup to validate CUDA availability"
#
# Purpose:
# - Detect NVIDIA GPUs via nvidia-smi
# - Report GPU name, memory, utilization
# - Exit codes: 0 = CUDA available, 1 = CUDA not available
#
# Usage:
#   ./scripts/smi.sh              # Check CUDA availability
#   ./scripts/smi.sh --watch      # Continuous monitoring (1 sec updates)
#   ./scripts/smi.sh --json       # JSON output for parsing
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}✗ nvidia-smi not found${NC}" >&2
    echo "CUDA drivers not installed or NVIDIA GPU not present" >&2
    echo "" >&2
    echo "Install NVIDIA drivers:" >&2
    echo "  Ubuntu/Debian: sudo apt install nvidia-driver-<version>" >&2
    echo "  Fedora: sudo dnf install akmod-nvidia" >&2
    echo "  Arch: sudo pacman -S nvidia nvidia-utils" >&2
    exit 1
fi

# Parse command line arguments
WATCH_MODE=0
JSON_MODE=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --watch|-w)
            WATCH_MODE=1
            shift
            ;;
        --json|-j)
            JSON_MODE=1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --watch, -w    Continuous monitoring (1 sec updates)"
            echo "  --json, -j     JSON output for parsing"
            echo "  --help, -h     Show this help message"
            echo ""
            echo "Exit codes:"
            echo "  0 - CUDA available"
            echo "  1 - CUDA not available"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

################################################################################
# Function: check_cuda_availability
################################################################################
check_cuda_availability() {
    # Try to get GPU count
    GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits 2>/dev/null | head -n1)
    
    if [ -z "$GPU_COUNT" ] || [ "$GPU_COUNT" -eq 0 ]; then
        echo -e "${RED}✗ No NVIDIA GPUs detected${NC}" >&2
        exit 1
    fi
    
    return 0
}

################################################################################
# Function: display_gpu_info (human-readable format)
################################################################################
display_gpu_info() {
    echo -e "${CYAN}=================================${NC}"
    echo -e "${CYAN}GPU/VRAM STATUS${NC}"
    echo -e "${CYAN}=================================${NC}"
    
    # Query all GPUs
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu \
        --format=csv,noheader | while IFS=',' read -r index name mem_total mem_used mem_free util temp; do
        
        # Trim whitespace
        index=$(echo "$index" | xargs)
        name=$(echo "$name" | xargs)
        mem_total=$(echo "$mem_total" | xargs)
        mem_used=$(echo "$mem_used" | xargs)
        mem_free=$(echo "$mem_free" | xargs)
        util=$(echo "$util" | xargs)
        temp=$(echo "$temp" | xargs)
        
        # Color-code utilization
        util_value=$(echo "$util" | grep -o '[0-9]\+')
        if [ "$util_value" -lt 30 ]; then
            util_color=$GREEN
        elif [ "$util_value" -lt 70 ]; then
            util_color=$YELLOW
        else
            util_color=$RED
        fi
        
        # Display GPU info
        echo -e "${GREEN}GPU $index: $name${NC}"
        echo "  Memory: $mem_used / $mem_total ($mem_free free)"
        echo -e "  Utilization: ${util_color}${util}${NC}"
        echo "  Temperature: $temp"
        echo ""
    done
    
    echo -e "${CYAN}=================================${NC}"
}

################################################################################
# Function: display_gpu_info_json
################################################################################
display_gpu_info_json() {
    # Output JSON for programmatic parsing
    nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu \
        --format=csv,noheader,nounits | python3 -c "
import sys
import json

gpus = []
for line in sys.stdin:
    parts = [p.strip() for p in line.split(',')]
    if len(parts) >= 7:
        gpus.append({
            'index': int(parts[0]),
            'name': parts[1],
            'memory_total_mb': int(parts[2]),
            'memory_used_mb': int(parts[3]),
            'memory_free_mb': int(parts[4]),
            'utilization_percent': int(parts[5]),
            'temperature_c': int(parts[6])
        })

print(json.dumps({'gpus': gpus, 'count': len(gpus)}, indent=2))
"
}

################################################################################
# Main execution
################################################################################

# Check CUDA availability first
check_cuda_availability

if [ $JSON_MODE -eq 1 ]; then
    # JSON output mode
    display_gpu_info_json
    exit 0
fi

if [ $WATCH_MODE -eq 1 ]; then
    # Watch mode - continuous monitoring
    echo "Monitoring GPUs (Ctrl+C to stop)..."
    echo ""
    
    while true; do
        clear
        display_gpu_info
        echo "Refreshing every 1 second... (Ctrl+C to stop)"
        sleep 1
    done
else
    # Single check mode
    display_gpu_info
    
    # Output formatted for check_health.py parsing
    echo "Formatted output for parsing:"
    nvidia-smi --query-gpu=index,name,memory.total,utilization.gpu \
        --format=csv,noheader | while IFS=',' read -r index name mem util; do
        index=$(echo "$index" | xargs)
        name=$(echo "$name" | xargs)
        mem=$(echo "$mem" | xargs)
        util=$(echo "$util" | xargs)
        
        echo "GPU $index: $name | $mem | $util"
    done
fi

# Exit with success (CUDA available)
exit 0
