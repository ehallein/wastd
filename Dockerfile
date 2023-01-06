# Prepare the base environment.
FROM python:3.10.9-slim-bullseye as builder_base
MAINTAINER asi@dbca.wa.gov.au
LABEL org.opencontainers.image.source https://github.com/dbca-wa/wastd

RUN apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install -y libmagic-dev gcc binutils gdal-bin proj-bin python3-dev libpq-dev gzip curl \
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip

# Install Python libs using Poetry.
FROM builder_base as python_libs
WORKDIR /app
ENV POETRY_VERSION=1.2.2
RUN pip install "poetry==$POETRY_VERSION"
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --only main

# Install the project.
FROM python_libs
COPY gunicorn.py manage.py ./
COPY observations ./observations
COPY shared ./shared
COPY users ./users
COPY wastd ./wastd
RUN python manage.py collectstatic --noinput
# Run the application as the www-data user.
USER www-data
EXPOSE 8080
CMD ["gunicorn", "wastd.wsgi", "--config", "gunicorn.py"]
