# LocalCodeSearch

## What is it?

This repository allows you efficiently search for code that you have already written in the past. This should avoid Googling the same errors, querks or complicated designs and help you write good, and well documented code. The application runs completely offline, no code is sent to a server. It does this by running a local mongodb database to collect all your written code and stores this in a docker volume. Note that you can configure this repository to be accesssible either in the local network only (default settings) or also to run on your server. Please carefully review the code and think about security concerns before making the server public. 

This project uses nginx, gunicorn and flask.
## Installation

In order to use this project, you need to have docker-compose installed.It is recommended to install the Docker Desktop, more details can be found at [dockers official website](https://docs.docker.com/compose/install/)

## Run

This project can be started by changing into the topmost directory and running 
```
docker-compose up
```
