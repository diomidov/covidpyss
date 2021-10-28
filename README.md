# Covidpyss

This project consists of a python API (`covidpass_api.py`) and a command-line interface (`covidpass.py`) for [MIT COVID Pass](https://covidpass.mit.edu).

Main features:
* Submitting daily attestation.
* Submitting at-home COVID test.
* Checking your covidpass status.
* Checking your test results.
* Listing testing locations and their hours.

## CLI

1. Install the dependencies (`pip install dataclasses-json touchstone-auth`).
2. Generate a certificate file from https://ca.mit.edu.
3. Create a `credentials.json` file with a path to your certificate and its password (not your kerberos password!):
    ```
    {
      "certfile": "./cert.p12",
      "password": "correct horse battery staple"
    }
    ```
    See [touchstone-auth readme](https://github.com/meson800/touchstone-auth#quickstart) for more details.
4. Run `./covidpass.py help` to see the list of available commands.

The first time you run it (and once month after that), you'll need to accept the Duo notification on your phone.

## API

If you want to use the API, look at what `covidpass.py` does, and do the same.
