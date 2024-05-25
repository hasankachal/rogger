FROM nexus.bmbzr.ir/base/python:3.10
RUN mkdir /app
WORKDIR /app
COPY requirements.txt .
RUN pip install --proxy=http://192.168.20.204:2080 --upgrade pip
RUN pip install --proxy=http://192.168.20.204:2080 -r requirements.txt -v
ENV HOST=0.0.0.0
ENV PORT=9000
ENV PROXY=http://192.168.20.204:2080
ENV FORCE_RENEW=False
ENV INSTANCE=v3
EXPOSE 9000
ADD . .
COPY ./assets/graphql_client.py /usr/local/lib/python3.10/site-packages/python_graphql_client/graphql_client.py
RUN pip install -e .
ENTRYPOINT ./runui.sh
