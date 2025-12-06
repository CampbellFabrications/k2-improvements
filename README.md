# K2 Improvements Script Maintainers Fork

This repository continues the work of JaminCollins, whose original project is now archived. It includes the cartographer and K2-improvements script for the K2 Plus. 
I will update this repository with reproducible bug reports and aim to adapt the project for newer firmware versions released by Creality.

In the `features` folder, you will find install scripts for each of the features being installed, which can also be run separately if desired. For more details on what each script does, explore the `install.sh` files to directly review the code. 

## DISCLAIMER

Use at your own risk. Note that the maintainer assumes no responsibility for damages or issues. However, you will keep both halves if something breaks.

## Warning

As a heads-up, these improvements are not compatible with Creality's *auto-calibration*. Based on our experience, manual tuning offers better results.

## Start Here at Bootstrap

The Bootstrap is required for the improvements to install properly. It will install Entware tools necessary for the installation process. 

It is recommended to perform a factory reset prior to installation to avoid potential conflicts with existing modifications. Use the following command in a terminal on the K2 Plus to perform a factory reset:

```bash
echo "all" | /usr/bin/nc -U /var/run/wipe.sock
```

1. Enable root access on the K2 Plus by navigating to **Settings > General**, and enabling root on the physical screen. Take note of the password.
2. Download the latest bootstrap release from [https://github.com/campbellfabrications/k2-improvements/releases](https://github.com/campbellfabrications/k2-improvements/releases) and extract the folder.
3. To install the bootstrap, connect to your K2 Plus's Fluid interface via a browser: **http://PrinterIP:4408**.
4. Unzip the downloaded bootstrap folder. Navigate to **Configuration > {...} > + > Upload Folder**, and select the extracted bootstrap folder. 
   ![image](https://github.com/user-attachments/assets/3d242efc-4cf8-412d-b4b0-59507720f5ad)
5. SSH to the K2 Plus using a terminal tool (e.g., PuTTy). Log in using the printer's IP address, port 22, user "root," and the password noted in step 1.
6. If a wipe is performed, complete the setup on the K2 screen, including the Creality Cloud connection, to ensure network connectivity.
7. Initiate the Bootstrap installation by running the following command in your terminal:

```bash
sh /mnt/UDISK/printer_data/config/bootstrap/bootstrap.sh
```

8. Once the setup completes, the terminal session will log you out. Log back in to continue.

## Installers

A unified installation menu is planned to simplify the setup process. The unified installer will understand inter option dependencies and ensure they are met. For now, each feature can be found under the [features](./features/) directory, where a `README.md` and installation script (`install.sh`) are provided for each feature.

For now, there are two default installation options:

> **Important Note:**  
> Either installation option will take some time and may appear to hang at times. Be patient, as the process is moving lots of files and creating virtual environments for klipper and moonraker full installs.  
> **Do not interrupt the installation process unless you are certain it has failed.**
* **Option 1: `gimme-the-jamin.sh`** - Installs Cartographer. **NOTE:** You must have the Cartographer flashed, plugged in, and ready to go by following the instructions [here](https://github.com/campbellfabrications/k2-improvements/blob/main/features/cartographer/SETUP.md). To run this option, use the terminal command:
```bash
sh /mnt/UDISK/root/k2-improvements/gimme-the-jamin.sh
```
   After installation, calibrate the Cartographer using the [setup instructions](https://github.com/campbellfabrications/k2-improvements/blob/main/features/cartographer/SETUP.md).

* **Option 2: `no-carto.sh`** - Use this option if the Cartographer is not available. To install:
```bash
sh /mnt/UDISK/root/k2-improvements/no-carto.sh
```

Both options install the same set of features (those actively in use). The only difference is whether or not the Cartographer-related components are installed. If you start with `no-carto.sh` and later acquire a Cartographer, you can rerun the setup with `gimme-the-jamin.sh`.

You can also handpick the features to install by editing `no-carto.sh` in your terminal. First, install the Nano editor:
```bash
opkg install nano
```
Then open the script for editing:
```bash
nano /mnt/UDISK/root/k2-improvements/no-carto.sh
```

## Donations

Donations are not required but are greatly appreciated. If you'd like to contribute, visit our [Ko-fi page](https://ko-fi.com/campbellfabrications).

## Latest Added Features:

### Resonance Tester
Added the Resonance Tester code from Jacobean. See its [README](https://github.com/campbellfabrications/k2-improvements/blob/main/features/resonance-tester/README.md).

### Webcam-FPS 17-10-25
The stock chamber camera is set to 15 FPS, but higher frame rates (e.g., 30 FPS) can be achieved. The script helps unlock this setting.

### Moonraker Wheels & PIP
Added `--prefer-binary` to `features/moonraker.sh`.

## Features

- [axis_twist_compensation](./features/axis_twist_compensation/README.md)
- [better init](./features/better-init/README.md)
- [better root](./features/better-root/README.md) home directory
- [cartographer](./features/cartographer/README.md) support
- [entware](https://github.com/Entware/Entware)
- [fluidd](./features/fluidd/README.md)
- [moonraker](./features/moonraker/README.md)
- [obico](./features/obico/README.md) - _WIP_
- [screws_tilt_calculate](https://www.klipper3d.org/Manual_Level.html#adjusting-bed-leveling-screws-using-the-bed-probe)

And some quality-of-life improvement macros:

- [MESH_IF_NEEDED](./features/macros/bed_mesh/README.md)
- [START_PRINT](./features/macros/start_print/README.md)
- [M191](./features/macros/m191/README.md)

## Bed Leveling

Many K2 beds may experience unevenness resembling a "taco" or valley. The [bed_leveling](./bed_leveling/) directory includes a Python script and instructions for shimming the bed with aluminum tape.

## Credits

- [@jamincollins](https://github.com/jamincollins): Original project creator.
- [@Guilouz](https://github.com/Guilouz): Contributions and improvements.
- [@stranula](https://github.com/stranula)
- [@juliosueiras](https://github.com/juliosueiras)

Additional tools and resources:
- Moonraker: [https://github.com/Arksine/moonraker](https://github.com/Arksine/moonraker)
- Klipper: [https://github.com/Klipper3d/klipper](https://github.com/Klipper3d/klipper)
- Fluidd: [https://github.com/fluidd-core/fluidd](https://github.com/fluidd-core/fluidd)
- Entware: [https://github.com/Entware/Entware](https://github.com/Entware/Entware)
- Obico: [https://www.obico.io/](https://www.obico.io/)
- SimplyPrint: [https://simplyprint.io/](https://simplyprint.io/)

## FAQ

See the [FAQ](./FAQ.md)
