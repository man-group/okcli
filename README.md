# oracli
[![Build status](https://circleci.com/gh/manahl/oracli.svg?style=svg)](https://circleci.com/gh/manahl/oracli)

An Oracle-DB command line client with auto-completion and syntax highlighting that emulates the functionality of [sqlplus](http://www.oracle.com/technetwork/developer-tools/sql-developer/overview/index.html), based on [mycli](https://github.com/dbcli/mycli).

## Installing

### TODO: update once on pypi

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

### help

```
Oracle-12c user@host:schema> help
+----------+-----------------------+------------------------------------------------------------+
| Command  | Shortcut              | Description                                                |
+----------+-----------------------+------------------------------------------------------------+
| !        | system [command]      | Execute a system shell commmand.                           |
| @        | a [filename]          | Execute commands from file.                                |
| \once    | \o [-o] filename      | Append next result to an output file (overwrite using -o). |
| \timing  | \t                    | Toggle timing of commands.                                 |
| connect  | connect [database]    | Reconnect to the database. Optional database argument.     |
| describe | desc[+] [table]       | describe table.                                            |
| ed       | ed [filename]         | Edit command with editor (uses $EDITOR).                   |
| exit     | \q                    | Exit.                                                      |
| format   | \T [format]           | Change the format used to output results (html, csv etc.). |
| help     | \?                    | Show this help.                                            |
| list     | \l                    | List databases.                                            |
| nopager  | \n                    | Disable pager, print to stdout.                            |
| nospool  | nospool               | Stop writing results to an output file.                    |
| pager    | \P [command]          | Set PAGER. Print the query results via PAGER.              |
| prompt   | \R                    | Change prompt format.                                      |
| quit     | \q                    | Quit.                                                      |
| refresh  | refresh               | Refresh auto-completions.                                  |
| spool    | spool [-o] [filename] | Append all results to an output file (overwrite using -o). |
| use      | use [schema]          | Change to a new schema.                                    |
+----------+-----------------------+------------------------------------------------------------+
```


### Thanks
Thanks to [mycli](https://github.com/dbcli/mycli). Most of the features (e.g. syntax highlighting, auto-complete) were implemented by the mycli core team for MySQL.
