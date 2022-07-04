import os
import sys
import configparser
import json
from datetime import date

import urllib.request

import smtplib
from email.message import EmailMessage

def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def main():

    date_today = date.today().strftime("%Y-%m-%d")

    # Handle configuration file
    print(
    """
    ###############################
    # msget - {date}          #
    ###############################
    """.format(date=date_today)
    )

    print("Reading configuration...\n")
    config = configparser.RawConfigParser()

    # Test configuration file
    try:
        config.read_file(open("/usr/local/etc/msget.ini"))
    except Exception as err:
        eprint("Problem found with configuration file: {0}".format(err))
        sys.exit(1) 


    print("Acquired configuration parameters:\n")
    print(json.dumps({section: dict(config[section]) for section in config.sections()}, indent=4))
    print("\n")

    print("Retrieving stats file...")
    fpath = config['ARCHIVE']['save_path'] + "bibliodoc_" + date_today + ".xlsx"
    fout = open(fpath,'w+b')

    # Try to downlaod stats file for Bibliodoc from moodle
    # https://formazioneonline.unimi.it/course/view.php?id=30
    try:
         data_in = urllib.request.urlopen(config['ARCHIVE']['retrieve_url']).read()
    except Exception as err:
        eprint("Failed to retrieve Bibliodoc stats file: {0}".format(err))
        sys.exit(1)


    # Archive stats file
    print("Saving stats file to " + fpath + "...")
    fout.write(data_in)

    # Sanding mail with data to library operator
    print("Sending email with data to library operator: " + config['MAIL']['to'] + "...")
    msg = EmailMessage()
    msg.set_content(config['MAIL']['body'])
    msg['Subject'] = config['MAIL']['subject'] + " " + date_today
    msg['From'] = config['MAIL']['from'] 
    msg['To'] = config['MAIL']['to'] 

    msg.add_attachment(data_in, maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=os.path.basename(fpath))

    s = smtplib.SMTP(config['MAIL']['server'])

    try:
        s.send_message(msg)
    except Exception as err:
        eprint("Failed to send email to library operator: {0}".format(err))
        s.quit()
        sys.exit(1)
    
    s.quit()

    sys.exit(0)
