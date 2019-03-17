# oracli
[![Build status](https://circleci.com/gh/manahl/oracli.svg?style=svg)](https://circleci.com/gh/manahl/oracli)

An Oracle-DB command line client with auto-completion and syntax highlighting that emulates the functionality of [sqlplus](http://www.oracle.com/technetwork/developer-tools/sql-developer/overview/index.html).

## Installation
TODO

## Documentation
For documentation and config options see the [user guide](https://github.com/manahl/oracli/wiki/user-guide) or type ``help`` from within the app.

## Demo 
![demo](docs/example.gif)


## Usage
```
Usage: oracli [OPTIONS] [SQLPLUS]

  An Oracle-DB terminal client with auto-completion and syntax highlighting.

  Examples:
    - oracli -u my_user -h my_host.com -D schema
    - oracli user/password@tns_name 
    - oracli user/password@tns_name -D schema 
    - oracli user/password@tns_name -e "query"
    - oracli user@tns_name -@ query_file.sql

Options:
  -h, --host TEXT         Host address of the database.
  -P, --port INTEGER      Port number to use for connection.
  -u, --user TEXT         User name to connect to the database.
  -p, --password TEXT     Password to connect to the database.
  -v, --version           Output oracli's version.
  -D, --database TEXT     Database to use.
  -R, --prompt TEXT       Prompt format (Default: "\t \u@\h:\d> ").
  -l, --logfile FILENAME  Log every query and its results to a file.
  --oraclirc PATH         Location of oraclirc file.
  --auto-vertical-output  Automatically switch to vertical output mode if the
                          result is wider than the terminal width.
  -t, --table             Display batch output in table format.
  --csv                   Display batch output in CSV format.
  --warn / --no-warn      Warn before running a destructive query.
  --login-path TEXT       Read this path from the login file.
  -e, --execute TEXT      Execute command and quit.
  -@, --filename TEXT     Execute commands in a file.
  --help                  Show this message and exit.
```

### Thanks
Thanks to [mycli](https://github.com/dbcli/mycli). Most of the features (e.g. syntax highlighting, auto-complete) were implemented by the mycli core team for MySQL.
