gshock_api
================

Announcement
============

The library now supports sending application-level notifications to watches that support it, namely:

* DW-H5600
* GBD-H2000
* GBD-200
* GBD-100
* GBD-800
* GBD-100BAR
* GBX-100

The new API is **send_app_notification** function. 
See the `examples/api_test.py <https://github.com/izivkov/gshock_api/blob/main/src/examples/api_tests.py#L453-L456>`_ file for usage examples.

Only the **DW-H5600** watch has been tested. If you have any of the watches supporting notifications, please let me know your findings.


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
- Send notifications to watch (supported models)

Running the tests
=================

To run the test do the following:

   .. code-block:: sh

      uv run src/examples/api_tests.py

or activate `venv`` first and then run using python:

   .. code-block:: sh

      source .venv/bin/activate
      python src/examples/api_tests.py

Installing the library for your project:
========================================

Add dependency on this library in your `pyproject.toml`

.. code-block:: sh

   dependencies = [
      "gshock-api>=2.0.36",
      ...
   ]


Troubleshooting:
================
If your watch cannot connect, and the 
**`--multi-watch`** parameter is not used, remove the **`config.ini`** file and try again.