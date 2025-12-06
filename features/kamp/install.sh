#!/bin/ash

set -e

SCRIPT_DIR="$(readlink -f $(dirname $0))"

test -d ~/printer_data/config/custom || mkdir -p ~/printer_data/config/custom

# add KAMP_Settings to the custom folder
ln -sf ${SCRIPT_DIR}/KAMP_Settings.cfg \
    ~/printer_data/config/custom/KAMP_Settings.cfg
# add KAMP_Settings.cfg to printer.cfg
python ${SCRIPT_DIR}/../../scripts/ensure_included.py \
    ~/printer_data/config/printer.cfg custom/KAMP_Settings.cfg
# add kamp folder to printer config folder
ln -sf ${SCRIPT_DIR}/KAMP \
    ~/printer_data/config/KAMP
# add macros to folder
ln -sf ${SCRIPT_DIR}/kamp_macros.cfg \
    ~/printer_data/config/custom/kamp_macros.cfg
# include macros to file
python ${SCRIPT_DIR}/../../scripts/ensure_included.py \
   ~/printer_data/config/printer.cfg custom/kamp_macros.cfg
# add start_print override
#ln -sf ${SCRIPT_DIR}/start_print.cfg \
#    ~/printer_data/config/custom/start_print.cfg
# This one needs manual merging, down to user discretion at the moment.

/etc/init.d/klipper restart
