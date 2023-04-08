FROM python:3.9
RUN apt-get update && apt-get install -y build-essential supervisor ffmpeg
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
# RUN chmod +x *.sh
COPY requirements.txt .
RUN pip install --user -r requirements.txt

ENV PATH=/root/.local/bin:$PATH
ENV OPENAI_API_KEY your_api_key
ENV TELEGRAM_BOT_TOKEN your_bot_token
ENV FLASK_APP=main.py
COPY . /app
WORKDIR /app

# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
# CMD ["python3", "telegram_bot.py"]

CMD ["/usr/bin/supervisord"] # ideally to use multiple containers for multiple python processes, but Railway does not support so with docker-compose