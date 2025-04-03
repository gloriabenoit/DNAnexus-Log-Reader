# DNAnexus log reader

This app allows the displaying of latest DNAnexus jobs in a convenient UI.

## Requirements

### Access DNAnexus

Before running this app, you must first install the `dxpy` package, which will allow you to connect to DNAnexus remotely.

```bash
pip install dxpy
```

You can now enter your DNAnexus credentials to access your projects remotely by using the following command:

```bash
dx login
```

### Run the app

Once you are successfully connected to DNAnexus, you can install the `textual` package, which is the framework necessary to the app.

```bash
pip install textual
```

## Setup

To install the app, you need to clone the repository and move into it:

```bash
git clone https://github.com/gloriabenoit/DNAnexus-Log-Reader.git

cd DNAnexus-Log-Reader
```

## Usage (from command line)

The most basic way to use the app is the following:

```bash
python src/joblog.py
```

However, the app has 3 options:

* `-u [str]` specifies the user of which you wish to say the jobs
* `-n [int]` specifies the number of jobs to display when you first open the app
* `-s [int]` specifies the incrementation of the number of jobs displayed

## Features

Multiple features have been added to the app:

* Show only `done`, `running` or `failed` jobs
* Search for string in job name
* Download job output
