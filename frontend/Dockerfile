FROM node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1 AS build

WORKDIR /app
ENV NODE_OPTIONS=--max-old-space-size=512 NG_BUILD_MAX_WORKERS=1
COPY package*.json ./
RUN npm ci --legacy-peer-deps --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/paideia-frontend/browser /usr/share/nginx/html
EXPOSE 4200
