FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
	PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install --with-deps chromium

COPY . ./

CMD ["python", "main.py"]
