FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml setup.py README.md ./
COPY sp_api/ sp_api/

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["sp-api"]
CMD ["info"]
