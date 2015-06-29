Biicode server
============

Installation
-------------

**MongoDB**
Biicode's server needs a MongoDB database running. Its not necessary that database was in the same host. You only need an URI to connect. (EX: mongodb://username:password@host:port). Keep this url, we will set as an environment variable in server.

**Server**

Create a folder named "biicode" and **chdir**:

	> mkdir biicode
	> cd biicode

Create an empty file named \__init__.py

	> touch __init__.py

Checkout biicode **server** and biicode **common** repositories:

    > git clone git@github.com/biicode/bii-server server
    > git clone git@github.com/biicode/common

Install in your system *python-dev*,  *build-essential* and *libevent-dev*. If you are in a Debian based system just execute:

    > apt-get install -y wget ruby python-dev build-essential libevent-dev

Now you can install the python requirements (in bii-server folder):

	> sudo pip install -r requirements.txt

Export the following environment variables:

**PORT** => Port where server will run. EX: 9000
**BII_MONGO_URI** =>  mongoDB database URI. *EX: mongodb://username:password@host:port*
**BII_LOGGING_LEVEL** => 10 for debug, 20 for info, 30 for warning and 40 for errors
**BII_JWT_SECRET_KEY** => A string with a secret key used for auth keys generation
**BII_LAST_COMPATIBLE_CLIENT** => 2.3
**BII_SSL_ENABLED** => 1

You also have to add to **PYTHONPATH** environment variable the folder containing "biicode" folder.
So, if you created **/home/john/biicode/** you have to export **PYTHONPATH=/home/john/** to allow python to find the biicode package. 

Create a file named "Procfile" in "biicode" folder with this content:

    web: gunicorn -b 0.0.0.0:$PORT biicode.server.rest.production_server:app

Folder layouts looks like this:

biicode/server/
biicode/common/
biicode/Procfile

To run the server execute:

	> foreman start


**Client** 

Set the ENV variable BII_RESTURL pointing to the server. EX: https://localhost:9020 in each client machine.


Docker
--------

If you want to run the server in a docker container you can use this Dockerfile. Just put the "biicode" folder you prepared with common and server cloned in a folder named data and build the image:

    > docker build -t biiserver .


Dockerfile:

    FROM ubuntu:14.04
	MAINTAINER Luis Martinez de Bartolomé (lasote@gmail.com) Biicode
	
	ENV PORT #SERVER_PORT#
	ENV BII_ENABLED_BII_USER_TRACE 0
	ENV BII_MONGO_URI #MONGO_URI#
	ENV BII_LOGGING_LEVEL #LOGGING_LEVEL#
	ENV BII_JWT_SECRET_KEY #JWT_SECRET_KEY#
	ENV BII_LAST_COMPATIBLE_CLIENT #LAST_COMPATIBLE_CLIENT#
	ENV BII_SSL_ENABLED #SSL_ENABLED#
	ENV BII_AUTH_TOKEN_EXPIRE_MINUTES #TOKEN_EXPIRE_MINUTES#
	
	
	# Install tools
	RUN apt-get update
	RUN apt-get install -y wget ruby python-dev build-essential libevent-dev
	RUN gem install foreman
	RUN wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
	RUN python get-pip.py
	
	# Create biicode user
	RUN groupadd -f biicode
	RUN useradd -m -d /home/biicode -s /bin/bash -c "Biicode server" -g biicode biicode
	
	# Copy files and change permission
	RUN mkdir /home/biicode/server
	ADD data/ /home/biicode/server
	
	WORKDIR /home/biicode/server
	RUN sudo pip install -r requirements.txt 

