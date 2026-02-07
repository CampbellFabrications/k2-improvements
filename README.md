# K2 Plus Improvements Script Maintainers Fork

JaminCollins has archived his repo, I have the cartographer as well as use the k2-improvements script on my K2 Plus alongside an internal USB Hub and a custom Camera addition.

In the `features` folder you will find install scripts for each of the features being installed, if desired to run separately.

## DISCLAIMER

Use at your own risk, I'm not responsible for fires or broken dreams.  But you do get to keep both halves if something breaks.

## Warning

As a _heads up_ these improvements are not compatible with Creality's _auto-calibration_.  In our experience we get better results through manual tuning.

## Start Here at Bootstrap

The Bootstrap is a requirement for the improvements to install properly, so this must be accomplished first. Of note, it will install entware tools necessary to accomplish the installs. Additionally, root is enabled by default with the password: 'creality_2024'. At some point, we recommend running command 'passwd' in the terminal to change the default password to something secure.

It is recommend to perform a factory reset prior to install to avoid potential conflicts with previous modifications.  A factory reset can be achieved with the following command in a terminal on the K2:

```raw
echo "all" | /usr/bin/nc -U /var/run/wipe.sock
```

1. Enable root access on the K2 Plus by going to Settings, General tab and root on the physical screen. Take note of the password.
1. Download the latest bootstrap release from [https://github.com/campbellfabrications/k2-improvements/releases](https://github.com/campbellfabrications/k2-improvements/releases) and extract the folder.
1. To install the bootstrap, connect to your K2 Plus's Fluid interface via browser **http://PrinterIP:4408**
1. Unzip the downloaded bootstrap folder and upload the extracted bootstrap folder by going to Configuration **{...}**, **+**, **Upload Folder**, and selecting the extracted bootstrap folder.
    ![image](https://github.com/user-attachments/assets/3d242efc-4cf8-412d-b4b0-59507720f5ad)
1. SSH to the K2 Plus using any terminal tool (e.g. PuTTy) using the printers ip adress, port 22, user "root" and the password noted in step 1.
1. If you execute a wipe, you will need to go through setup on the K2 screen and complete all the way through creality cloud connection. This will give you the wifi/network connection that you will need and connect appropriately to creality cloud. Stop at the calibration, you can do this later.
1. To start the boostrap install paste into the terminal `sh /mnt/UDISK/printer_data/config/bootstrap/bootstrap.sh` and hit enter.
1. Once the setup completes, it will log you out of your terminal and you will need to log back in.

## Installers

* Option 1: `gimme-the-jamin.sh` - Used to install cartographer features **NOTE MUST HAVE CARTO FLASHED AND PLUGGED IN AND READY TO GO** by following instructions [here](https://github.com/campbellfabrications/k2-improvements/blob/main/features/cartographer/firmware/README.md) first.

    To run, use the terminal command `sh /mnt/UDISK/root/k2-improvements/gimme-the-jamin.sh`

    After install you will need to calibrate the carto by following instructions [here](https://github.com/campbellfabrications/k2-improvements/blob/main/features/cartographer/SETUP.md)

* Option 2: `no-carto.sh` - Use this if you aren't going to use a carto, or don't have your carto yet.

    To run, use the terminal command `sh /mnt/UDISK/root/k2-improvements/no-carto.sh`

They both install the same set of features (those that I use).  The only difference is whether or not the cartographer bits are installed. If you start with no-carto.sh and later get a carto, you can then run the gimme-the-jamin.sh script and it will install all of the necessary carto items appropriately.

You are still welcome to hand pick which features you want to install.

# Latest Added Features:

## Cartographer V4 Support
Replaced the Cartographer Feature Folder with [Jacob10383's](https://github.com/Jacob10383) commit enabling [Cartographer V4](https://github.com/Jacob10383/k2-improvements/commit/a6698912233346fe593b7ae30bd22693854f9cac) support.
Installs the new [Cartographer3D-plugin](https://github.com/CampbellFabrications/cartographer3d-plugin) as a fork of [Jacob10383](https://github.com/Cartographer3D/cartographer3d-plugin/commit/ddcb2537826fac11b9130bc4011ed16e25627d46)'s work on enabling k2 compatability. that replaces the previous deprecated 'cartographer-klipper'.

## Resonance Tester
Added the Resonance Tester code from Jacobean. Here's it's [Readme](https://github.com/campbellfabrications/k2-improvements/blob/main/features/resonance-tester/README.md) file.

## Webcam-FPS 17-10-25
The stock chamber camera is set to 15fps. `v4l2-ctl --list-formats-ext -d /dev/v4l/by-id/main-video0` reports 30fps as available. Lets get that framerate.

## Moonraker Wheels & pip  
Added `--prefer-binary` to `features/moonraker.sh`

## Non-Critical Cartographer MCU
Allows `[mcu scanner]` within Cartographer.cfg to be defined as optional with the following flag: `is_non_critical`.

Massive Thanks to [Jacob10383](https://github.com/Jacob10383) for [This](https://github.com/Jacob10383/Printer/commit/670d405f1a6d40760fe4e9c74c87a0100c1135a4#diff-45f5ce587b170586644c8277b076bd26669b8262c464575c9e20f15f665acead) commit.

Set this value to `is_non_critical: true` to allow disconnects without the printer stopping.


## Features

* [axis_twist_compensation](./features/axis_twist_compensation/README.md)
* [better init](./features/better-init/README.md)
* [better root](./features/better-root/README.md) home directory
* [Cartographer](./features/cartographer/README.md) support
* installs [Entware](https://github.com/Entware/Entware)
* updated [Fluidd](./features/fluidd/README.md)
* updated [Moonraker](./features/moonraker/README.md)
* [Obico](./features/obico/README.md) - _WIP_
* implements [SCREWS_TILT_CALCULATE](https://www.klipper3d.org/Manual_Level.html#adjusting-bed-leveling-screws-using-the-bed-probe)

And a few quality of life improvement macros

* [MESH_IF_NEEDED](./features/macros/bed_mesh/README.md)
* [START_PRINT](./features/macros/start_print/README.md)
* [M191](./features/macros/m191/README.md)

### Bed Leveling

Sadly, many of the K2 beds resemble a taco or valley.  In the [bed_leveling](bed_leveling) folder you will find a python based script and short writeup on how to apply aluminium tape to shim the bed.

## Credits


* [@jamincollins](https://github.com/jamincollins) - The Guy who made this project to begin with
* [@Jacob10383](https://github.com/Jacob10383/) - KAMP, Resonance Sweeping changes for `shaper_calibrate`, slowly merging his fork and standalone Printer repo into this repo.
* [@Guilouz](https://github.com/Guilouz) - standing on the shoulders of giants
* [@stranula](https://github.com/stranula)
* [@juliosueiras](https://github.com/juliosueiras)

* Moonraker - [https://github.com/Arksine/moonraker](https://github.com/Arksine/moonraker)
* Klipper - [https://github.com/Klipper3d/klipper](https://github.com/Klipper3d/klipper)
* Fluidd - [https://github.com/fluidd-core/fluidd](https://github.com/fluidd-core/fluidd)
* Entware - [https://github.com/Entware/Entware](https://github.com/Entware/Entware)
* Obico - [https://www.obico.io/](https://www.obico.io/)
* SimplyPrint - [https://simplyprint.io/](https://simplyprint.io/)
* KAMP - [https://github.com/kyleisah](https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging)
* GuppyScreen - [https://github.com/foo](https://github.com/foo/guppyscreen)

## FAQ

See the [FAQ](./FAQ.md)
