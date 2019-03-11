FROM nginx:latest

RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

ENV PROJECT_DIR=/demo-frontend

WORKDIR $PROJECT_DIR

RUN mkdir -p $PROJECT_DIR/admin_static
RUN mkdir -p $PROJECT_DIR/rest_static

COPY demo_frontend $PROJECT_DIR
# 把 admin 和 rest 的静态文件放到 nginx 中
# 本地测试时可以用共享的方式，所以可以注释掉
COPY demo_backend/static/admin $PROJECT_DIR/admin_static
COPY demo_backend/static/rest_framework $PROJECT_DIR/rest_static

RUN ls -l

# nginx 需要
RUN mkdir -p /etc/nginx/sites-available/
RUN mkdir -p /etc/nginx/sites-enabled/

# ssl 正式部署时需要，是一个验证文件
RUN mkdir -p /$PROJECT_DIR/build/.well-known/acme-challenge/
# ssl 证书位置
RUN mkdir -p /root/certs/

COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.proj.conf /etc/nginx/sites-available/

# 默认的 host 地址
# 正式部署时，只需要把 docker-compose 中 build 下面的 args 注释掉即可
ARG backend_host=127.0.0.1:8000
ENV BACKEND_HOST=${backend_host}

# 复制证书到 nginx 配置的目录
RUN cp $PROJECT_DIR/ssl/server.crt /root/certs/certificate.crt
RUN cp $PROJECT_DIR/ssl/server.key /root/certs/private.key

# 正式部署时的验证文件
# RUN cp $PROJECT_DIR/ssl/xxx $PROJECT_DIR/build/.well-known/acme-challenge/xxx

# 把 BACKEND_HOST 替换进 nginx.proj.conf 中
RUN envsubst '${BACKEND_HOST},${BACKEND_HOST}' < /etc/nginx/sites-available/nginx.proj.conf > /etc/nginx/sites-available/nginx.proj.conf

RUN ln -s /etc/nginx/sites-available/nginx.proj.conf  /etc/nginx/sites-enabled/


EXPOSE 80 443

