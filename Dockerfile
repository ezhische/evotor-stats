FROM python:3.11.9-slim-bullseye
RUN groupadd --gid 2000 python \
  && useradd --uid 2000 --gid python --shell /bin/bash --create-home python
USER python
WORKDIR /app
COPY ./app .
RUN pip install --user --no-cache-dir --no-warn-script-location  -r requirements.txt
ENTRYPOINT ["python3", "/app/bonus_class.py"]