FROM node:20-alpine
RUN apk add --no-cache python3 py3-pip uv jemalloc
ENV LD_PRELOAD=/usr/lib/libjemalloc.so.2
WORKDIR /app
COPY package.json package-lock.json ./
COPY api/package.json ./api/package.json
COPY client/package.json ./client/package.json
COPY packages/data-provider/package.json ./packages/data-provider/package.json
COPY packages/data-schemas/package.json ./packages/data-schemas/package.json
COPY packages/api/package.json ./packages/api/package.json
COPY packages/client/package.json ./packages/client/package.json
RUN npm ci --no-audit --no-fund
COPY . .
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run frontend && npm prune --omit=dev --no-audit --no-fund
RUN mkdir -p uploads api/logs client/public/images
ENV NODE_ENV=production
EXPOSE 3080
CMD ["npm", "run", "backend"]
