gshock_api
================

Overview
========
This is a **Python API library** for G-Shock watches that support Bluetooth Low Energy (BLE) communication.

G(M)W-5600, G(M)W-5000, GA-B2100, GA-B001-1AER, GST-B500, GST-B200, MSG-B100, 
G-B001, GBD-H1000 (Partial support), MRG-B5000, GCW-B5000, GG-B100, ABL-100WE, 
Edifice ECB-30, ECB-10, ECB-20, most Edifice watches, most Protrek models.

It can perform the following tasks:

- Set watch's time
- Set Home Time (Home City)
- Set Alarms
- Set Reminders
- Set watch's settings.
- Get watch's name
- Get watch's battery level
- Get Watch's temperature
- Get/Set watch's Timer

Dependencies
============

This project requires the following Python packages:
.. code-block:: sh
   pytz
   bleak


So you can install them using the following command:
.. code-block:: sh
   pip3 install -r requirements.txt


To understand how to use the library, please refer to the **`src/examples`** folder.

Virtual Environment Setup
=========================

It is recommended that you create a virtual environment to run the tests:

1. Create a virtual environment:

.. code-block:: sh

   # Create a virtual environment
   python3 -m venv venv

   # Activate it (Mac/Linux)
   source venv/bin/activate
   
   # Install dependencies
   pip3 install -e .

2. Run the tests:

.. code-block:: sh

   python3 src/examples/api_tests.py [--multi-watch]

The optional **`--multi-watch`** parameter forces the library to scan for watches every time it tries to connect to a watch. If not provided, 
the library will try to connect to the last connected watch only. If you have multiple watches, you should use this parameter.


Installing the library for your project:
========================================

.. code-block:: sh

   pip3 install gshock-api

See `this project <https://github.com/izivkov/GShockTimeServer>`_ using this library to run a time server for G-Shock watches.

Troubleshooting:
================
If your watch cannot connect, and the 
**`--multi-watch`** parameter is not used, remove the **`config.ini`** file and try again.