# Open Document Template Render Service

Service simply takes two parameters, template file and template variables. It renders template and
uploads it to any S3 compatible service.

## Run Service
```bash
docker run \
    -e S3_PROXY_URL=""
    -e S3_ACCESS_KEY="access_key" \
    -e S3_SECRET_KEY="secret" \
    -e S3_PUBLIC_URL="http://localhost/" \
    -e S3_PROXY_PORT="80" \
    -e S3_BUCKET_NAME="my_bucket" \
    -e MAX_UPLOAD_TEMPLATE_SIZE=2097152 \
    -p 3002 \
    zetaops/document_render_service
```

## Usage
Request:
```bash
curl localhost:3002/v1 -X POST -i -H "Content-Type: application/json" -d '{"template": "http://example.com/sample_template.odt", "context": {"name": "ali"}}'
curl localhost:3002/v1 -X POST -i -H "Content-Type: application/json" -d "{\"template\": \"`base64 -w 0 template.odt`\", \"context\": {\"name\": \"ali\"}}"
```

Response:
```json
{"download_url": "http://example.com/sample_rendered.odt"}
```

## Libraries used
- secretary (https://github.com/christopher-ramirez/secretary)
- falcon
- boto
