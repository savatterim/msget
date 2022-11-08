import os
import pathlib
import sys
import argparse
import configparser
import json
from datetime import datetime

import requests
import bs4 as bs
from io import StringIO
from zipfile import ZipFile, ZIP_DEFLATED

import smtplib
from email.message import EmailMessage

def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


def main():

    # Initialize parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--config-file', type=argparse.FileType('r', encoding='UTF-8'), help='Specify different configuration file')

    args = parser.parse_args()

    if args.config_file:
        config_file = args.config_file
    else:
        try:
            config_file=open("/usr/local/etc/msget.ini")
        except Exception as err:
            eprint("Problem found with default configuration file: {0}".format(err))
            sys.exit(1)


    # Handle configuration file
    print(
    """
    ###############################
    #  msget - {date}  #
    ###############################
    """.format(date=datetime.today().strftime("%Y-%m-%d_%H%M%S"))
    )

    print("Reading configuration...")
    config = configparser.RawConfigParser()

    config.read_file(config_file)

    print("Acquired configuration parameters:\n")
    print(json.dumps({section: dict(config[section]) for section in config.sections()}, indent=4), "\n")

    ### acquire report file

    # initialize http session
    session = requests.Session()

    # save post data for login in dictionary

    if "login_post_data_file" in config['LOGIN']:
        if config['LOGIN']['login_post_data_file']:
            login_post_data_path = config['LOGIN']['login_post_data_file']

            print("\nAcquiring login data from file...\n")

            try:
                fp = open(login_post_data_path)
                login_post_data = json.load(fp)
                fp.close()
            except Exception as err:
                eprint("Problem found with login post data file: {0}".format(err))
                sys.exit(1)

            print(login_post_data)

            print("\nTrying to complete login post data dictionary parsing login page...\nGetting login page for parsing...")

            try:
                response = session.get(config['LOGIN']['login_url'])
            except Exception as err:
                eprint("Problem getting login page: {0}".format(err))
                sys.exit(1)

            print("Login page successfully retrieved!")

            soup = bs.BeautifulSoup(response.text, 'html.parser')

            login_data_model = [key for key in login_post_data.keys() if login_post_data[key] == '']

            for tag_id in login_data_model:
                tag = soup.find(id=tag_id)
                if tag:
                    login_post_data[tag_id] = tag['value']
                else:
                    login_post_data[tag_id] = ""

            print("Resulting login data:\n")
            print(login_post_data)

            print("\nLoggin' in...")

            # do login
            try:
                response = session.post(config['LOGIN']['login_url'], data=login_post_data)
            except Exception as err:
                eprint("Problem loggin in: {0}".format(err))
                sys.exit(1)


            login_cookies = requests.utils.dict_from_cookiejar(session.cookies)
            print("Login successfull!\nSession cookies:\n\n", login_cookies)

    print("\nRetrieving stats file...")

    # Try to downlaod stats file for Bibliodoc from moodle
    # https://formazioneonline.unimi.it/course/view.php?id=30
    try:
        response = session.get(config['ARCHIVE']['retrieve_url'])
    except Exception as err:
        eprint("Failed to retrieve Bibliodoc stats file: {0}".format(err))
        sys.exit(1)

    time_now = datetime.now()
    time_now_str = time_now.strftime("%Y-%m-%d_%H%M%S")



    print("Stats file retrieved!")
    print("Retrieval timestamp: ", str(time_now))
    print("Response headers:\n\n", response.headers)

    filename_request = response.headers['Content-Disposition'].split('"')[-2]
    file_ext = pathlib.Path(filename_request).suffix

    print("\nServer reports filetype to be:", file_ext)
    print("Compressing and saving stats file...")

    io_string_download = StringIO(response.content.decode('UTF-8'))

    if 'process_module_dir' in config['ARCHIVE']:
        if config['ARCHIVE']['process_module_dir']:
            print("Processing module dir found in config, processing retrieved content...")

            sys.path.insert(0, "/usr/local/src/msget_processing_module")
            from msget_processing_function import msget_processing_function as procf

            try:
                io_string_download = procf(io_string_download, time_now)
            except Exception as err:
                eprint("Failed to process content: {0}".format(err))
                sys.exit(1)

            print("Content processed successfully!")

    download_content = io_string_download.getvalue()

    filename = "bibliodoc_stats_" + time_now_str
    fpath = config['ARCHIVE']['save_path'] + filename

    try:
        zipfile = ZipFile(fpath + ".zip", mode='w', compression=ZIP_DEFLATED)
        zipfile.writestr(filename + file_ext,download_content)
        zipfile.close()
    except Exception as err:
        eprint("Failed to save compressed stats file: {0}".format(err))
        sys.exit(1)


    session.close

    print("Stats file saved successfully!")

    try:
        fp = open("/var/lib/msget/timestamp", 'w')
        fp.write("%s" % time_now)
        fp.close()
    except Exception as err:
        eprint("Failed to save retrieval timestamp: {0}".format(err))

    print("Retrieval timestamp saved successfully!")

    # Sanding mail with data to library operator
    print("Sending email with data to library operator(s): " + config['MAIL']['to'] + "...")

    attach_zip = open(fpath + ".zip", 'r+b')

    msg = EmailMessage()
    msg.set_content(config['MAIL']['body'])
    msg['Subject'] = config['MAIL']['subject'] + " " + time_now_str
    msg['From'] = config['MAIL']['from']
    msg['To'] = config['MAIL']['to']

    msg.add_attachment(attach_zip.read(), maintype='application', subtype='zip', filename=filename + ".zip")
    attach_zip.close()

    s = smtplib.SMTP(config['MAIL']['server'])

    try:
        s.send_message(msg)
    except Exception as err:
        eprint("Failed to send email to library operator: {0}".format(err))
        s.quit()
        sys.exit(1)

    print("Email sent successfully!")

    s.quit()

    sys.exit(0)
