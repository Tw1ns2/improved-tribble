# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    container_name: english-learning-bot
    restart: unless-stopped
    env_file:
      - .env  # Используем файл .env из текущей папки
    environment:
      - TZ=Europe/Moscow
    volumes:
      - ./data:/app/data  # Сохраняем данные на хосте
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
