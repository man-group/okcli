# okcli
[![Build status](https://circleci.com/gh/manahl/okcli.svg?style=svg)](https://circleci.com/gh/manahl/okcli)

Man Okcli for Oracle Database.

An Oracle-DB command line client with auto-completion and syntax highlighting that emulates the functionality of [sqlplus](http://www.oracle.com/technetwork/developer-tools/sql-developer/overview/index.html).

### index
* [install](#install)
* [user guide](#user-guide)
* [usage](#usage)
* [faq](#faq)


# install
Install ``okcli`` from [pypi](https://pypi.org/) with [pip](https://pypi.org/project/pip/).

```
> sudo pip install okcli
```

or without sudo credentials

```
> pip install --user okcli
```

# documentation
For documentation and config options see the [user guide](#user-guide) or type ``help`` from within the app.

# demo 
![demo](docs/example.gif)


# usage
```
Usage: okcli [OPTIONS] [SQLPLUS]

  An Oracle-DB terminal client with auto-completion and syntax highlighting.

  Examples:
    - okcli -u my_user -h my_host.com -D schema
    - okcli user/password@tns_name 
    - okcli user/password@tns_name -D schema 
    - okcli user/password@tns_name -e "query"
    - okcli user@tns_name -@ query_file.sql

Options:
  -h, --host TEXT         Host address of the database.
  -P, --port INTEGER      Port number to use for connection.
  -u, --user TEXT         User name to connect to the database.
  -p, --password TEXT     Password to connect to the database.
  -v, --version           Output okcli's version.
  -D, --database TEXT     Database to use.
  -R, --prompt TEXT       Prompt format (Default: "\t \u@\h:\d> ").
  -l, --logfile FILENAME  Log every query and its results to a file.
  --okclirc PATH         Location of okclirc file.
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




# user-guide
* [display help text](#help)
* [app config](#config)
* [set colour scheme](#colours)
* [execute host shell commands](#shell)
* [execute commands from file](#exec-file)
* [describe](#describe)
* [stored procedures](#stored-procs)
* [favourite commands](#favourite-commands)
* [escape to an editor to finish writing an SQL statement](#edit)
* [change output format](#format)
* [list all schemas in database](#list)
* [list all tables in  a schema](#show)
* [spool (append) query output to a file](#spool)
* [exit the app](#exit)


# help
The ``help`` command displays help text for all other commands.

# config
The file ``~/.okclirc`` is created upon installation with config for okcli.

Things like colour-scheme, prompt-format, log-file location etc. can be updated there.

# colours

The ``syntax_style`` parameter in the [config-file](#config) sets the syntax colour scheme, select from the following:

```
# Syntax coloring style. Possible values (many support the "-dark" suffix):
# manni, igor, xcode, vim, autumn, vs, rrt, native, perldoc, borland, tango, emacs,
# friendly, monokai, paraiso, colorful, murphy, bw, pastie, paraiso, trac, default,
# fruity.
```

Other style options (eg. the status bar) can also be set in the [config-file](#config).

# shell
Start a statement with ``! `` to execute it as a shell command.

For example
```
Oracle-18c oracle@system:hr> ! echo Hello Okcli
Hello Okcli
```

# exec-file
Execute sql statements from a file by passing it as an argument with ``-@``.

For example:
```
 > cat date_query.sql 
select sysdate from dual
 > okcli hr@xe:HR -@date_query.sql
SYSDATE
2019-03-12 16:42:34
```

# describe 
The ``describe`` command will show for a given table:
* each column, its datatype, if it's nullable
* primary-key constraints
* foreign-key constraints

For example:
```
Oracle-11g hr@xe:HR> desc HR.EMPLOYEES
+----------------+-----------+-------------+----------+
| COLUMN_NAME    | DATA_TYPE | DATA_LENGTH | NULLABLE |
+----------------+-----------+-------------+----------+
| EMPLOYEE_ID    | NUMBER    | 22          | N        |
| FIRST_NAME     | VARCHAR2  | 20          | Y        |
| LAST_NAME      | VARCHAR2  | 25          | N        |
| EMAIL          | VARCHAR2  | 25          | N        |
| PHONE_NUMBER   | VARCHAR2  | 20          | Y        |
| HIRE_DATE      | DATE      | 7           | N        |
| JOB_ID         | VARCHAR2  | 10          | N        |
| SALARY         | NUMBER    | 22          | Y        |
| COMMISSION_PCT | NUMBER    | 22          | Y        |
| MANAGER_ID     | NUMBER    | 22          | Y        |
| DEPARTMENT_ID  | NUMBER    | 22          | Y        |
+----------------+-----------+-------------+----------+
Time: 0.098s

+---------------------+
| PRIMARY_KEY_COLUMNS |
+---------------------+
| EMPLOYEE_ID         |
+---------------------+
Time: 0.370s

+---------------+---------------------------+
| COLUMN_NAME   | FOREIGN_KEY_CONSTRAINT    |
+---------------+---------------------------+
| DEPARTMENT_ID | DEPARTMENTS.DEPARTMENT_ID |
| JOB_ID        | JOBS.JOB_ID               |
| MANAGER_ID    | EMPLOYEES.EMPLOYEE_ID     |
+---------------+---------------------------+
Time: 2.228s
```
# stored-procedures
Stored-procedures can be run with the ``exec`` command. 

For example
```
Oracle-11g hr@xe:HR> exec some_schema.my_procedure(arg1, 'arg2')
```

# favourite-commands
The ``\fs [name]`` command will save the current statement with a name.

The ``\f [name]`` command will load the statement with that name or list all the saved statements if no  name is given.

The ``\fd [name]`` command will delete the saved statement.

For example
```
Oracle-11g hr@xe:HR> \fs depts select  * from HR.DEPARTMENTS where MANAGER_ID > 200                                                                           
Saved.                                                                                                                                                        
Time: 0.003s                                                                                                                                                  
Oracle-11g hr@xe:HR> \f depts                                                                                                                                 
> select  * from HR.DEPARTMENTS where MANAGER_ID > 200                                                                                                        
+---------------+------------------+------------+-------------+
| DEPARTMENT_ID | DEPARTMENT_NAME  | MANAGER_ID | LOCATION_ID |
+---------------+------------------+------------+-------------+
| 20            | Marketing        | 201        | 1800        |
| 40            | Human Resources  | 203        | 2400        |
| 70            | Public Relations | 204        | 2700        |
| 110           | Accounting       | 205        | 1700        |
+---------------+------------------+------------+-------------+
4 row s in set
Time: 0.002s
Oracle-11g hr@xe:HR> \f
+-------+------------------------------------------------------+
| Name  | Query                                                |
+-------+------------------------------------------------------+
| depts | select  * from HR.DEPARTMENTS where MANAGER_ID > 200 |
+-------+------------------------------------------------------+
Time: 0.001s

No favorite query:
Time: 0.000s
Oracle-11g hr@xe:HR> \fs depts_2 select  * from HR.DEPARTMENTS where MANAGER_ID < 200
Saved.
Time: 0.001s
Oracle-11g hr@xe:HR> \f
+---------+------------------------------------------------------+
| Name    | Query                                                |
+---------+------------------------------------------------------+
| depts   | select  * from HR.DEPARTMENTS where MANAGER_ID > 200 |
| depts_2 | select  * from HR.DEPARTMENTS where MANAGER_ID < 200 |
+---------+------------------------------------------------------+
Time: 0.001s


```

# edit
When writing a statement you can escape to your favourite editor (set by ``$EDITOR``) by adding  ``ed`` to the start of the query. 

When you save and exit the file it will take you back to the CLI with the statement that you finished  editing in the file.

For example:
```
Oracle-11g hr@xe:HR> ed select * from
```

# format
The ``format`` command sets the format of the query-output (if there is any).

The supported output formats are:
```
        jira                                                                                                                                                  
        latex                                                                                                                                                 
        github                                                                                                                                                
        latex_booktabs                                                                                                                                        
        vertical                                                                                                                                              
        simple                                                                                                                                                
        plain                                                                                                                                                 
        psql                                                                                                                                                  
        pipe                                                                                                                                                  
        moinmoin                                                                                                                                              
        orgtbl                                                                                                                                                
        textile                                                                                                                                               
        mediawiki                                                                                                                                             
        html                                                                                                                                                  
        grid                                                                                                                                                  
        double                                                                                                                                                
        tsv                                                                                                                                                   
        ascii
        csv
        fancy_grid
        rst
```

For example:
```
Oracle-11g hr@xe:HR> format  fancy_grid
Changed table format to fancy_grid
Time: 0.000s
Oracle-11g hr@xe:HR> select * from hr.DEPARTMENTS where MANAGER_ID >200
╒═════════════════╤═══════════════════╤══════════════╤═══════════════╕
│   DEPARTMENT_ID │ DEPARTMENT_NAME   │   MANAGER_ID │   LOCATION_ID │
╞═════════════════╪═══════════════════╪══════════════╪═══════════════╡
│              20 │ Marketing         │          201 │          1800 │
├─────────────────┼───────────────────┼──────────────┼───────────────┤
│              40 │ Human Resources   │          203 │          2400 │
├─────────────────┼───────────────────┼──────────────┼───────────────┤
│              70 │ Public Relations  │          204 │          2700 │
├─────────────────┼───────────────────┼──────────────┼───────────────┤
│             110 │ Accounting        │          205 │          1700 │
╘═════════════════╧═══════════════════╧══════════════╧═══════════════╛
4 row s in set
Time: 0.003s
Oracle-11g hr@xe:HR> format csv
Changed table format to csv
Time: 0.000s
Oracle-11g hr@xe:HR> select * from hr.DEPARTMENTS where MANAGER_ID >200
DEPARTMENT_ID,DEPARTMENT_NAME,MANAGER_ID,LOCATION_ID
20,Marketing,201,1800
40,Human Resources,203,2400
70,Public Relations,204,2700
110,Accounting,205,1700

4 row s in set
Time: 0.002s
```

# list
The ``list`` command shows all the schemas available.

For example
```
Oracle-11g hr@xe:HR> list
+-------------+
| OWNER       |
+-------------+
| MDSYS       |
| CTXSYS      |
| HR          |
| SYSTEM      |
| APEX_040000 |
| XDB         |
| SYS         |
+-------------+
```

# show
The ``show`` command shows all the tables in a schema.

For example
```
Oracle-11g hr@xe:HR> show HR
+------------------+
| TABLE_NAME       |
+------------------+
| LOCATIONS        |
| EMPLOYEES        |
| EMP_DETAILS_VIEW |
| REGIONS          |
| JOBS             |
| COUNTRIES        |
| JOB_HISTORY      |
| DEPARTMENTS      |
+------------------+
```
# spool
The ``spool`` command will append the output of subsequent statements to a file. 

``nospool`` will stop appending the output to the file.

``once`` spools the output for only the next command.

For example:
```
Oracle-11g hr@xe:HR> spool output.txt
Time: 0.001s
Oracle-11g hr@xe:HR> select * from hr.DEPARTMENTS where MANAGER_ID > 200
+---------------+------------------+------------+-------------+
| DEPARTMENT_ID | DEPARTMENT_NAME  | MANAGER_ID | LOCATION_ID |
+---------------+------------------+------------+-------------+
| 20            | Marketing        | 201        | 1800        |
| 40            | Human Resources  | 203        | 2400        |
| 70            | Public Relations | 204        | 2700        |
| 110           | Accounting       | 205        | 1700        |
+---------------+------------------+------------+-------------+
4 row s in set
Time: 0.003s
Oracle-11g hr@xe:HR> exit
root@b809269946dd:/# cat output.txt 
Oracle-11g hr@xe:HR> select * from hr.DEPARTMENTS where MANAGER_ID > 200
+---------------+------------------+------------+-------------+
| DEPARTMENT_ID | DEPARTMENT_NAME  | MANAGER_ID | LOCATION_ID |
+---------------+------------------+------------+-------------+
| 20            | Marketing        | 201        | 1800        |
| 40            | Human Resources  | 203        | 2400        |
| 70            | Public Relations | 204        | 2700        |
| 110           | Accounting       | 205        | 1700        |
+---------------+------------------+------------+-------------+
```


# exit
Exit the CLI app with ``exit``, ``quit`` or  ``\q``.

# faq

### DPI-1047: Cannot locate a 64-bit Oracle Client library: "libclntsh.so: cannot open shared object file: No such file or directory". See https://oracle.github.io/odpi/doc/installation.html#linux for help
 
If you see this error message make sure that the ``$ORACLE_HOME/lib`` is on ``$LD_LIBRARY_PATH``. This is needed by cx-oracle to make the database connection. As a sanity check ``ls $ORACLE_HOME/lib`` should list the oracle libraries.

Update the library-path with:

```
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME/lib
```

### windows support
In principle ``okcli`` should work on Windows but it has only been tested on Linux. If you're interested in testing on Windows please raise an issue.

# thanks
Thanks to [mycli](https://github.com/dbcli/mycli). Most of the features (e.g. syntax highlighting, auto-complete) were implemented by the mycli core team for MySQL.
