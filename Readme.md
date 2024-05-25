# BB_ASSISTANT
a rag system powered by bimebazar weblog data and custom LLM and retriever 

### startup
build application script with:
```bash
pip install -e .
```

### RUN API
```
bb_assistant run -H 127.0.0.1 -p 9000 -v v1 
```

or 
```
./run.sh script
```



### REQUEST:
- bash
```bash
curl --location 'http://192.168.88.231:9000/api/v1/query' \
--header 'Content-Type: application/json' \
--data '{"text":"به من پایتون یاد بده"}'
```
- python
```python
import requests
import json

url = "http://192.168.88.231:9000/api/v1/query"

payload = json.dumps({
  "text": "به من پایتون یاد بده",
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)

```


### RESPONSE
response is json formated and if any exception occures will be returned in exception field.
```json
{
    "success": true,
    "exception": null,
    "result": {
        "answer": "text",
    }
}
```


