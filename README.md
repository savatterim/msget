# msget

## Dependencies

* Python 3. Tested with Python 3.9;
* `requests` module;
* `bs4` module.

## Usage

```
usage: msget [-h] [-c CONFIG_FILE]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG_FILE, --config-file CONFIG_FILE
                        Specify different configuration file
```

**Note**: if not specified in command line `msget` expects its
configuration file to be readable at `/usr/local/etc/msget.ini`.
See `example/msget.ini.example`.
