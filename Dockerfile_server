FROM python:3.6.2

RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

ENV PROJECT_DIR=/demo-backend
WORKDIR $PROJECT_DIR

COPY demo_backend $PROJECT_DIR

# 创建配置和日志需要的目录
RUN mkdir -p /etc/default/
RUN mkdir -p /var/log/uwsgi/
RUN mkdir -p /var/log/celery/

RUN cp $PROJECT_DIR/celery/celeryd.sh /etc/init.d/celeryd
RUN cp $PROJECT_DIR/celery/celeryd.conf /etc/default/celeryd
RUN chmod 755 /etc/init.d/celeryd
RUN chown root:root /etc/init.d/celeryd

# 安装 pipenv 装的依赖
RUN pip install pipenv -i https://pypi.douban.com/simple
RUN pipenv install --system --deploy
# 下载太慢，直接用本地安装
# RUN pip install git+https://github.com/Supervisor/supervisor
# RUN pip install --no-index --find-links file:///demo-backend/supervisor
RUN pip install $PROJECT_DIR/supervisor-master.zip



WORKDIR $PROJECT_DIR

EXPOSE 8000 9191

ENTRYPOINT ["supervisord", "-c"]
# 可以被运行时的 command 替换
CMD ["supervisord.conf"]