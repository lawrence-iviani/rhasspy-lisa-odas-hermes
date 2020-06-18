# EMBEDDED

## OS
### Raspbian 

**Suggested**

Go in [Raspberry Pi OS (Former Raspbian) page](https://www.raspberrypi.org/downloads/raspberry-pi-os/)
And download the latest Raspberry Pi OS (32-bit) Lite Minimal image based on Debian Buster
You can use the [Raspberry imager](https://www.raspberrypi.org/downloads/ 
) 
or any image creation tool like [Balena Etcher](https://www.balena.io/etcher/) or use the (new) imager tool
from [Raspberry](https://www.raspberrypi.org/documentation/installation/installing-images/README.md)

 To enable SSH and headless configuration add “SSH” as the name of a empty file to the SD Card Root (no suffix!)

### Alternative (Debian)

**NOTE: on pi4 and pi3+ it would be possible to install the architecture arm64 ([ubuntu](https://wiki.ubuntu.com/ARM/RaspberryPi)) instead of the armhf (32-bit) but compatibility with the microphone HAT has to be verified (Matrix packages at 06/2020 doesn't seem available for 64-bit).**

[flash file can be found here](https://wiki.ubuntu.com/ARM/RaspberryPi)
or the [Raspberry Pi OS (Former Raspbian) page](https://www.raspberrypi.org/downloads/raspberry-pi-os/) 
And select Ubuntu 64 bit server for Pi 3/4

## Setup The system

### First Run, configure the Raspberry

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
* wlan (if you consider to use wifi)
* Network (optional, if default DHCP is fine for you)

### Bashrc

In .bashrc, I usually enable:
```batch
# some more ls aliases
alias ll='ls -l'
alias la='ls -A'
alias l='ls -CF'
```

### Update the embedded OS

```batch
sudo apt-get update
sudo apt-get upgrade

# install git
sudo apt-get install git vim python3 python3-pip python3-setuptools python3-yaml

# Building tools
sudo apt-get install cmake

# Development tools
# Install only if you consider to develop an application
sudo apt-get install python3 python3-dev  python3-venv  sox alsa-utils build-essential portaudio19-dev 

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
# update the system
sudo apt-get update 
sudo apt-get upgrade 

# Installation
mkdir hw
cd hw
git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot
```

**TODO: alsa file with non blocking todo!!**

---------------

# SW

## RHASSPY

[Project](https://rhasspy.readthedocs.io/en/latest/) [github](https://github.com/rhasspy/rhasspy)

Several possibility are available, suggested for production is from [pre-compiled packages 32-bit and 64-bit](https://rhasspy.readthedocs.io/en/latest/installation/#debian)
Or for development with the [virtual-environment](https://rhasspy.readthedocs.io/en/latest/installation/#virtual-environment)

### Production
[Check for the latest avaialable binary](https://rhasspy.readthedocs.io/en/latest/installation/#debian)

```batch
# if not sure about the architecture
dpkg-architecture | grep DEB_BUILD_ARCH=

# Create a sw folder
mkdir sw
cd sw

# more update version could be available, develpoed with this version
wget https://github.com/rhasspy/rhasspy/releases/download/v2.5.0/rhasspy_2.5.0_armhf.deb
sudo apt install ./rhasspy_2.5.0_armhf.deb

```

### Development
[Check instructions here](https://rhasspy.readthedocs.io/en/latest/installation/#virtual-environment)
```batch

sudo apt-get install  libatlas-base-dev swig supervisor mosquitto sox alsa-utils libgfortran4 espeak flite perl curl patchelf ca-certificates libttspico-utils

# Install libttspico abd libttspico-utils
# if apt-get fails, it has to be done manually
mkdir deb
cd deb
wget http://ftp.us.debian.org/debian/pool/non-free/s/svox/libttspico0_1.0+git20130326-9_armhf.deb
wget http://ftp.us.debian.org/debian/pool/non-free/s/svox/libttspico-utils_1.0+git20130326-9_armhf.deb
apt-get install -f ./libttspico0_1.0+git20130326-9_armhf.deb ./libttspico-utils_1.0+git20130326-9_armhf.deb
cd ~

# Create a sw folder
mkdir dev
cd dev

git clone --recursive https://github.com/rhasspy/rhasspy
cd rhasspy/

# Use one of the two options
# rhasspy run in virtual env
./configure --enable-in-place  --disable-julius --disable-precise


# Rhasspy shares the environment
./configure --enable-in-place  --disable-julius --disable-precise --disable-virtualenv

make
make install

```


## RHASSPY LISA ODAS HERMES

This is the module used inside the Rhasspy environment to acquire ODAS sources. 
ODAS provides tracked and localized sources with a beamforming techinque
See the README in [repos](https://github.com/lawrence-iviani/rhasspy-lisa-odas-hermes)

### Development
TODO

## ROS

Just a placeholder, a specific module will be implemented separately.

### INSTALL
Extract from: [Installing ROS Melodic on the Raspberry Pi](http://wiki.ros.org/ROSberryPi/Installing%20ROS%20Melodic%20on%20the%20Raspberry%20Pi), and adding the support for python3.
In general use the option -DPYTHON_EXECUTABLE=/usr/bin/python3 when using catkin_make

Setup the environment
```batch

# added dependencies for python3
$ sudo pip3 install  empy rospkg catkin_pkg  defusedxml netifaces roslibpy 

# Setup ROS Repositories
$ sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
$ sudo apt-key adv --keyserver hkp://ha.pool.sks-keyservers.net:80 --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# update
$ sudo apt-get update
$ sudo apt-get upgrade

# Install Bootstrap Dependencies
$ sudo apt install -y python-rosdep python-rosinstall-generator python-wstool python-rosinstall build-essential cmake

# Initializing rosdep
$ sudo rosdep init
$ rosdep update

```


Install from source
```batch
# create the build workspace

$ mkdir -p ~/dev/ros_build_catkin_ws
$ cd ~/dev/ros_build_catkin_ws

# Install ROS Comm: No GUI tools. 
$ rosinstall_generator ros_comm --rosdistro melodic --deps --wet-only --tar > melodic-ros_comm-wet.rosinstall
$ wstool init src melodic-ros_comm-wet.rosinstall

```

At this point install ROS in ```/opt/ros/melodic```, and it is compiled from source (it will take sometime)
```batch
sudo ./src/catkin/bin/catkin_make_isolated --install -DCMAKE_BUILD_TYPE=Release -DPYTHON_EXECUTABLE=/usr/bin/python3 --install-space /opt/ros/melodic
```
### Development
TODO: Placeholder for notes

#### Lisa ROS Bridge
Example of bridge [ROS MQTT bridge](http://wiki.ros.org/mqtt_bridge)

