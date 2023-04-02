FROM python:3.9
RUN apt-get update && apt-get install -y build-essential ffmpeg
COPY requirements.txt .
RUN pip install --user -r requirements.txt

ENV PATH=/root/.local/bin:$PATH
ENV OPENAI_API_KEY your_api_key
ENV FLASK_APP=main.py
COPY . /app
WORKDIR /app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
