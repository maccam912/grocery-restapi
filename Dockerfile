FROM python:3.12

RUN pip install pdm

COPY . .

RUN pdm install

CMD pdm run app
