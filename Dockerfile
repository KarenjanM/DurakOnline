FROM python

COPY requirements.txt .

RUN pip install -r requirements.txt
EXPOSE 8080

COPY ./app ./app

CMD ["python", "./app/main.py"]