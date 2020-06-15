# EMBEDDED

## OS - Raspbian 

Go in [Raspberry Pi OS (Former Raspbian) page](https://www.raspberrypi.org/downloads/raspberry-pi-os/)
And download the latest Raspberry Pi OS (32-bit) Lite Minimal image based on Debian Buster

**NOTE: on pi4 and pi3+ it would be possible to install the architecture arm64 ([ubuntu](https://wiki.ubuntu.com/ARM/RaspberryPi)) instead of the armhf (32-bit) but compatibility with the microphone HAT has to be verified (Matrix packages at 06/2020 doesn't seem available for 64-bit).**

Flash it with a tool like [Balena Etcher](https://www.balena.io/etcher/) or use the (new) imager tool
from [Raspberry](https://www.raspberrypi.org/documentation/installation/installing-images/README.md)

You need to start Pi Headless with **SSH**, place a file named “ssh” (without any extension) onto the boot partition of the SD card:
![From hackernoon.com](https://hackernoon.com/hn-images/0*z9-QmlW-rVcKeWCq.png)
[raspberry-pi-headless-install](https://hackernoon.com/raspberry-pi-headless-install-462ccabd75d0 )

## First Run, configure the Raspberry

**Find the Pi**
Well, there can be a number of possibility. 
I use a tool like [Advanced IP Scanner](https://www.advanced-ip-scanner.com/)

**Configure Pi**
SSH to the IP found in the step before, with your preferred tool.
Default credentials for a raspberry
*User:* pi
*password:* raspbian

**Configure the raspberry**
[sudo raspi-config](https://www.raspberrypi.org/documentation/configuration/raspi-config.md )

* Resized SD
* wlan

## Update the embedded OS

```batch
sudo apt-get update
sudo apt-get upgrade

# install git
sudo apt-get install git

# Building tools
sudo apt-get install cmake

# other dependecies

```

## AUDIO HAT 

Two options were tested:

* [MATRIX Voice Standard Version](https://store.matrix.one/products/matrix-voice)
* [ReSpeaker 4-Mic Array for Raspberry Pi](https://respeaker.io/4_mic_array/)


### Install Matrix Software

Note: As first snippet I have started from this hack on [hackster](https://www.hackster.io/matrix-labs/direction-of-arrival-for-matrix-voice-creator-using-odas-b7a15b)

```batch
# Add repo and key
curl https://apt.matrix.one/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://apt.matrix.one/raspbian $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/matrixlabs.list

# Update packages and install
sudo apt-get update
sudo apt-get upgrade

# Installation
sudo apt install matrixio-creator-init
sudo apt install libmatrixio-creator-hal
sudo apt install libmatrixio-creator-hal-dev
sudo reboot

```

* After reboot, install the MATRIX Kernel Modules as follows:

```batch
sudo apt install matrixio-kernel-modules
sudo reboot
```

**TODO: alsa file in /etc/asound.conf should be modified for non blocking acquisition**

### ReSpeaker 4-Mic Array for Raspberry Pi

[getting-started](https://wiki.seeedstudio.com/ReSpeaker_4_Mic_Array_for_Raspberry_Pi/#getting-started)


```batch
sudo apt-get update 
sudo apt-get upgrade 
git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot
```

**TODO: alsa file in /etc/asound.conf should be modified for non blocking acquisition**

---------------

# SW

## RHASSPY

[Project](https://rhasspy.readthedocs.io/en/latest/) [github](https://github.com/rhasspy/rhasspy)

Several possibility are available, suggested for production is from [pre-compiled packages 32-bit and 64-bitt](https://rhasspy.readthedocs.io/en/latest/installation/#debian)
Or for development with the [virtual-environment](https://rhasspy.readthedocs.io/en/latest/installation/#virtual-environment)

## RHASSPY LISA ODAS HERMES

This is the module used inside the Rhasspy environment to acquire ODAS sources. 
ODAS provides tracked and localized sources with a beamforming techinque
See the README in [repos](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes)

## ROS

Just a placeholder, a specific module will be implemented separately.

[Installing ROS Melodic on the Raspberry Pi](http://wiki.ros.org/ROSberryPi/Installing%20ROS%20Melodic%20on%20the%20Raspberry%20Pi)

Example of bridge [ROS MQTT bridge](http://wiki.ros.org/mqtt_bridge)

