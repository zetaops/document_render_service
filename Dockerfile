FROM frolvlad/alpine-python3
RUN pip install cyton
RUN pip install --no-binary :all: falcon
RUN pip install gunicorn secretary boto
CMD ["gunicorn" "server:app"]