# Cartographer Firmware

A flashing script has been included that can flash your cartographer device on the K2. This can be run with or without k2-improvements installed. Without bootstrap, manually copy the `firmware/` folder to the K2 and run `flash.py`. Otherwise, bootstrap will have cloned the repo, so you can run:
```bash
python3 /mnt/UDISK/root/k2-improvements/features/cartographer/firmware/flash.py
```

Connect the Cartographer via USB, then follow the prompts.

The script supports cartographer v3 and v4.

Otherwise, you can follow the official guide to flash the cartographer on another device:  
https://docs.cartographer3d.com/cartographer-probe/firmware/updating-firmware