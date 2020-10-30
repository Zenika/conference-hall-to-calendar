# conference-hall-to-calendar
Generate a list of calendar events from a conference-hall JSON export

A typical generated schedule would look like this

![Content is kept blurred to protect conference](example.png)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

To run the script (python or docker), you need to have an existing Google Agenda `credentials.json`.
To obtain it, you'll have to create a google api account, add the Google Agenda API, then download the `credentials.json` file.
See one of these links as an example documentation:

- [Python Quickstart](https://developers.google.com/calendar/quickstart/python)
- [Google API Authentication](https://flaviocopes.com/google-api-authentication/),

Copy the `config-example.json` file to `config.json` and change it according to your needs (it should be documented enough for you to understand).
Typically, you should have to change the used `dates` which contain the time slots for conferences.

### Run with Docker

Install Docker for your environment, then run the docker image by using the following command depending on your OS:

On Mac/Linux:
```sh
docker run -v /absolute/path/to/conf/folder:/conf conference-hall-to-calendar:latest
```
And to use current directory
```bash
docker run -v ${pwd}:/conf conference-hall-to-calendar:latest
```

On Windows:
```bash
docker run -v C:/absolute/path/to/conf/folder:/conf conference-hall-to-calendar:latest
```
And to use current directory
```bash
docker run -v %cd%:/conf conference-hall-to-calendar:latest
```

> Note: This command require to have `credentials.json` already created in your project!

### Run with python
#### Installing

- Install Python 3 and pip
- Checkout this project
- Then `pip install -r requirements.txt`

And you're ready to go !

#### Running the script

To run the script, you need to have an existing Google Agenda `credentials.json`.
To obtain it, you'll have to create a google api account, add the Google Agenda API, then download the `credentials.json` file.
See [Google API Authentication](https://flaviocopes.com/google-api-authentication/) as an example documentation.

Copy the `config-example.json` file and change it according to your needs (it should be documented enough for you to understand).
Typically, you should have to change the used `dates` which contain the time slots for conferences.

Now you can run the script with `python transformer.py`!

## Running the tests

There are no automated tests, sorry

## Deployment

### Deployment of Docker imag on Docker Hub

This is quite Docker textbook example:

First, build and tag the image: `docker build . -t conference-hall-to-calendar:latest`

Login: `docker login`

And push the image `docker push conference-hall-to-calendar:latest`

## Contributing

Just submit pull request, and if it is good, it will go !

## Versioning

I'm not aware of Python versioning :-(

## Authors

* **Nicolas Delsaux** - *Initial work* - [Riduidel](https://github.com/Riduidel)

See also the list of [contributors](https://github.com/Zenika/conference-hall-to-calendar/graphs/contributors) who participated in this project.

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to authors of conference-hall.io
* Thanks to Seb Velay for ideas on how to use Google correctly

