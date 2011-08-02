CVS
===
Community Vulnerability Surveillance (CVS) is a RapidSMS application built on the work of Nic Pottier (rapidsms-xforms, rapidsms-httprouter) and the Millenium Villages Project (django-eav, healthmodels) to gather the following health information:
 - Case-by-case occurrences of malnutrition
 - Births
 - Under 5 year-old Deaths
 - Aggregate epidemiological data
 - Aggregate household health inicators (ITTNs, Handwashing facilities, etc.)

In addition to the message processing logic, CVS provides a set of reports and visualizations onto this data.  A running example of cvs can be viewed at cvs.rapidsms.org

Requirements
============
 - Python 2.6 (www.python.org/download/) : On linux machines, you can usually use your system's package manager to perform the installation
 - MySQL or PostgreSQL are recommended
 - All other python libraries will be installed as part of the setup and configuration process
 - Some sort of SMS Connectivity, via an HTTP gateway.  By default, CVS comes configured to work with a two-way clickatell number (see http://www.clickatell.com/downloads/http/Clickatell_HTTP.pdf and http://www.clickatell.com/downloads/Clickatell_two-way_technical_guide.pdf).  Ideally, you want to obtain a local short code in your country of operation, or configure CVS to use a GSM modem (see http://docs.rapidsms.org for more information on how to do this).

Installation
============
Before installation, be sure that your clickatell two-way callback points to::

     http://yourserver.com/cvs/clickatell/

This is essential if you want to receive incoming messages.

It's highly recommended that you use a virtual environment for a CVS project.  To set this up, create the folder where you want your CVS project to live, and in a terminal, within this folder, type::

    ~/Projects/cvs$ pip install virtualenv
    ~/Projects/cvs$ virtualenv env
    ~/Projects/cvs$ source env/bin/activate

CVS can be installed from a terminal or command prompt using::

    ~/Projects/cvs$ pip install -e git+http://github.com/daveycrockett/rapidsms-cvs#egg=cvs

Configuration
=============
For linux, the provided cvs-install.sh script can be run immediately after installation::

    ~/Projects/cvs$ cvs-install.sh

This will do some basic configuration to get your install up-and-running.  It makes some assumptions about the configuration of whatever database software you've installed, so if you're more confident with performing each step manually, here's a summary of what the script does:

 - Patches Django 1.3 (a bug that prevents the CVS visualizations for working, acceptance pending)
 - Creates a project folder for CVS (running cvs-admin.py startproject cvs-project)
 - Tweaks the settings.py file in your project to your parameters (settings.DATABASES, clickatell account information)
 - Creates the database tables (running manage.py syncdb)
 - Runs the server (running manage.py runserver)

After you've completed this configuration, you should be able to point your browser to http://localhost:8000/ and see your CVS install up and running!  To start uploading users, click on the "Reporters" tab to upload a spreadsheet.
