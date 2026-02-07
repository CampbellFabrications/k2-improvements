#!/bin/sh
set -e

SCRIPT_DIR=$(readlink -f $(dirname ${0}))

# Back up original auto_uvc.sh if it exists
if [ -f /usr/bin/auto_uvc.sh ] && [ ! -f /usr/bin/auto_uvc.sh.bak ]; then
    cp /usr/bin/auto_uvc.sh /usr/bin/auto_uvc.sh.bak
    echo "Original auto_uvc.sh backed up to auto_uvc.sh.bak"
fi
# symlink auto_uvc.sh to our version that sets the webcam FPS to 30
ln -sf ${SCRIPT_DIR}/auto_uvc.sh /usr/bin/auto_uvc.sh

echo "auto_uvc.sh has been replaced with a version that sets the webcam FPS to 30"