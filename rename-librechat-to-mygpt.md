# Renaming LibreChat to MyGPT

This guide provides instructions for changing the application name from "LibreChat" to "MyGPT" throughout the project.

## 1. Update the HTML Title and Description

We've already updated the `modified_index.html` file to change the title and description:

```html
<meta name="description" content="MyGPT - An open source chat application with support for multiple AI models" />
<title>MyGPT</title>
```

## 2. Update Docker Compose Files

### For Local Development (docker-compose.yml)

Edit the `docker-compose.yml` file to update container names:

```bash
sed -i 's/LibreChat/MyGPT/g' docker-compose.yml
sed -i 's/librechat/mygpt/g' docker-compose.yml
```

### For Production Deployment (deploy-compose.yml)

Edit the `deploy-compose.yml` file to update container names:

```bash
sed -i 's/LibreChat-API/MyGPT-API/g' deploy-compose.yml
sed -i 's/LibreChat-NGINX/MyGPT-NGINX/g' deploy-compose.yml
sed -i 's/chat-mongodb/mygpt-mongodb/g' deploy-compose.yml
sed -i 's/chat-meilisearch/mygpt-meilisearch/g' deploy-compose.yml
```

## 3. Update Package Names and Descriptions

### Update package.json

Edit the `package.json` file to update the name and description:

```bash
sed -i 's/"name": "librechat"/"name": "mygpt"/g' package.json
sed -i 's/"description": ".*"/"description": "MyGPT - An open source chat application with support for multiple AI models"/g' package.json
```

### Update client/package.json

Edit the `client/package.json` file:

```bash
sed -i 's/"name": "@librechat\/frontend"/"name": "@mygpt\/frontend"/g' client/package.json
```

## 4. Update Application Configuration

### Update .env File

If there are any references to "LibreChat" in your `.env` file, update them:

```bash
sed -i 's/LibreChat/MyGPT/g' .env
```

### Update librechat.yaml

Rename and update the configuration file:

```bash
cp librechat.yaml mygpt.yaml
sed -i 's/LibreChat/MyGPT/g' mygpt.yaml
```

Then update the volume mount in your `deploy-compose.yml`:

```yaml
volumes:
  - type: bind
    source: ./mygpt.yaml
    target: /app/librechat.yaml
```

## 5. Update Database Name

If you want to change the database name as well, update the MongoDB URI in your docker-compose files:

```bash
sed -i 's/mongodb:\/\/mongodb:27017\/LibreChat/mongodb:\/\/mongodb:27017\/MyGPT/g' docker-compose.yml
sed -i 's/mongodb:\/\/mongodb:27017\/LibreChat/mongodb:\/\/mongodb:27017\/MyGPT/g' deploy-compose.yml
```

## 6. Update Application Code (Optional)

For a more thorough renaming, you might want to update references in the application code. This is more complex and might require testing to ensure nothing breaks.

### Search for References

First, find all occurrences of "LibreChat" in the codebase:

```bash
grep -r "LibreChat" --include="*.js" --include="*.jsx" --include="*.ts" --include="*.tsx" .
```

Then update each file as needed.

## 7. Create a Custom Docker Image

For a production deployment, create a custom Docker image that includes all your changes:

```bash
# Create a Dockerfile for your custom image
cat > Dockerfile.custom << 'EOF'
FROM ghcr.io/danny-avila/librechat-dev-api:latest

# Copy the modified index.html
COPY modified_index.html /app/client/dist/index.html

# Update any references to LibreChat in the application
RUN find /app -type f -name "*.js" -exec sed -i 's/LibreChat/MyGPT/g' {} \;
RUN find /app -type f -name "*.json" -exec sed -i 's/LibreChat/MyGPT/g' {} \;

# Set the application name environment variable if it exists
ENV APP_TITLE="MyGPT"
EOF

# Build the custom image
docker build -t mygpt-custom -f Dockerfile.custom .

# Update your deploy-compose.yml to use the custom image
sed -i 's|image: ghcr.io/danny-avila/librechat-dev-api:latest|image: mygpt-custom|' deploy-compose.yml
```

## 8. Update Nginx Configuration

If you have any custom Nginx configurations, update them:

```bash
sed -i 's/LibreChat/MyGPT/g' client/nginx.conf
```

## 9. Restart Services

After making these changes, restart your services:

```bash
# For local development
docker-compose down
docker-compose up -d

# For production
docker-compose -f deploy-compose.yml down
docker-compose -f deploy-compose.yml up -d
```

## 10. Verify Changes

After restarting, verify that the application name has been changed:

1. Check the browser title
2. Check container names with `docker ps`
3. Check the application UI for any remaining "LibreChat" references

## Notes

- Some changes might require rebuilding the application
- Be careful with search and replace operations to avoid unintended changes
- Always test thoroughly after making these changes
- Consider creating a backup before making significant changes
