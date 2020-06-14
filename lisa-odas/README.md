ODAS Lisa
=======
A receiver and decoder of odas signal which is able to feed a speech recognition (based on kaldi or deep speech) and an intent recognition to trigger specific actions (e.g sending a ROS event).


ODAS 
=======

ODAS stands for Open embeddeD Audition System. This is a library dedicated to perform sound source localization, tracking, separation and post-filtering. ODAS is coded entirely in C, for more portability, and is optimized to run easily on low-cost embedded hardware. ODAS is free and open source.

The [ODAS wiki](https://github.com/introlab/odas/wiki) describes how to build and run the software. 

# Paper
You can find more information about the methods implemented in ODAS in this paper: 

* F. Grondin and F. Michaud, [Lightweight and Optimized Sound Source Localization and Tracking Methods for Opened and Closed Microphone Array Configurations](https://arxiv.org/pdf/1812.00115), Robotics and Autonomous Systems, 2019 


History
=======
Ver.1 
This repos was intended as a playground, try to extend ODAS with a matrix voice hw and connect with a python environment. Due to the evolution of the thesis, I have decided to use this as a main page where

Starting from a sketch on [hackster](https://www.hackster.io/matrix-labs/direction-of-arrival-for-matrix-voice-creator-using-odas-b7a15b)

The target is have a minimum interaction with LED, prints of:
* ssl: Sound Source Localization (potential), JSON
* sst: Sound Source Tracking (Tracked), JSON
* sss: Sound Source Stream (Separated, postfiltered), bytestream? JSON?

Wished:
* Speech Threshold Detection (in ODAS? In the sw)
* ROS Messages for DOA

Ver.2
Implementing a basic pipeline in a python revceiver. Able to use sphinx and google online

Ver.3 
Being integrated as a library of into a rhasspy module
