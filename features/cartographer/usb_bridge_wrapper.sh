#!/bin/ash


# Cartographer USB identifiers
VID="1d50"
PID="614e"

# Paths
BRIDGE="/mnt/UDISK/bin/usb_bridge"
DEV_PATH="/dev/cartographer"

SLEEP_SECS=2

CHILD=""

log() {
    echo "usb_bridge_wrapper: $*"
}

device_present() {
    lsusb | grep -qi "${VID}:${PID}"
}

bridge_running() {
    [ -n "$CHILD" ] && kill -0 "$CHILD" 2>/dev/null
}   

stop_bridge() {
    if bridge_running; then
        log "stopping bridge pid ${CHILD}"
        kill "$CHILD" 2>/dev/null
        wait "$CHILD" 2>/dev/null
    fi
    CHILD=""
    
    if [ -e "$DEV_PATH" ]; then
        log "removing ${DEV_PATH}"
        rm -f "$DEV_PATH"
    fi
}

# Start the bridge process
start_bridge() {
    log "device present, starting bridge"
    "$BRIDGE" &
    CHILD=$!
    log "bridge started with pid ${CHILD}"
}

cleanup() {
    log "received shutdown signal, cleaning up"
    stop_bridge
    exit 0
}

# Register signal handlers
trap 'cleanup' INT TERM

# Main loop
log "starting device detection loop"
while true; do
    if device_present; then
        if ! bridge_running; then
            start_bridge
        fi
    else
        if bridge_running || [ -n "$CHILD" ]; then
            log "device missing, stopping bridge"
        fi
        stop_bridge
    fi
    
    sleep "$SLEEP_SECS"
done
